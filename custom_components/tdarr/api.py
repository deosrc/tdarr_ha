import asyncio
import logging
import aiohttp

from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class TdarrApiClient(object):
    """API Client for interacting with a Tdarr server"""

    def __init__(self, id: str, session: aiohttp.ClientSession):
        self._id = id
        self._session = session
        
    async def get_nodes(self):
        _LOGGER.debug("Retrieving nodes from %s", self._id)
        r = await self._session.get('get-nodes')
        if r.status == 200:
            data = await r.json()

            # Node IDs can change when node is restarted, so replace with node name instead.
            # Fallback to ID if node name is unavailable for some reason.
            data = { value.get("nodeName", key): value for key, value in data.items()}

            return data
        else:
            return "ERROR"

    async def get_status(self):
        _LOGGER.debug("Retrieving status from %s", self._id)
        r = await self._session.get('status')
        if r.status == 200:
            result = await r.json()
            return result
        else:
            return "ERROR"
    
    async def get_libraries(self):
        _LOGGER.debug("Retrieving libraries from %s", self._id)
        library_settings = await self.get_library_settings()
        libraries = {l["_id"]: { "name": l["name"] } for l in library_settings}
        libraries.update({ 
            "": { 
                "name": "All" 
            } 
        }) 
        _LOGGER.debug("Libraries: %s", libraries) 
 
        async def update_library_details(library_id, data: dict):
            data.update(await self.get_pies(library_id))

        async with asyncio.TaskGroup() as tg:
            for library_id, data in libraries.items():
                tg.create_task(update_library_details(library_id, data))
        
        return libraries

    async def get_stats(self):
        _LOGGER.debug("Retrieving stats from %s", self._id)
        post = {
            "data": {
                "collection":"StatisticsJSONDB",
                "mode":"getById",
                "docID":"statistics",
                "obj":{}
                },
            "timeout":1000
        }
        r = await self._session.post('cruddb', json = post)
        if r.status == 200:
            return await r.json()
        else:
            return "ERROR"
    
    async def get_library_settings(self):
        _LOGGER.debug("Retrieving library settings from %s", self._id)
        post = {
            "data": {
                "collection":"LibrarySettingsJSONDB",
                "mode":"getAll",
                },
            "timeout":20000
        }
        r = await self._session.post('cruddb', json = post)
        if r.status == 200:
            return await r.json()
        else:
            return
        
    async def get_pies(self, library_id=""):
        _LOGGER.debug("Retrieving pies for library ID '%s' from %s", library_id, self._id)
        post = {
            "data": {
                "libraryId": library_id
            },
        }
        r = await self._session.post('stats/get-pies', json = post)
        if r.status == 200:
            data = await r.json()
            return data["pieStats"]
        else:
            return "ERROR"
        
    async def get_staged(self):
        _LOGGER.debug("Retrieving staged files from %s", self._id)
        post = {
            "data": {
                "filters":[],
                "start":0,
                "pageSize":10,
                "sorts":[],
                "opts":{}
                },
            "timeout":1000
        }
        r = await self._session.post('client/staged', json = post)
        if r.status == 200:
            return await r.json()
        else:
            return "ERROR"
        
    async def get_global_settings(self):  
        _LOGGER.debug("Retrieving global settings from %s", self._id)
        post = {
            "data": {
                "collection":"SettingsGlobalJSONDB",
                "mode":"getById",
                "docID":"globalsettings",
                "obj":{}
                },
            "timeout":1000
        }
        r = await self._session.post('cruddb', json = post)
        if r.status == 200:
            return await r.json()
        else:
            return {"message": r.text, "status_code": r.status, "status": "ERROR"}
        
    async def set_global_setting(self, setting_key, value):
        _LOGGER.debug("Setting global setting '%s' for %s", setting_key, self._id)
        data = {
            "data":{
                "collection":"SettingsGlobalJSONDB",
                "mode":"update",
                "docID":"globalsettings",
                "obj":{
                    setting_key: value
                }
            },
            "timeout":20000
        }

        try:
            response = await self._session.post('cruddb', json=data)            
        except aiohttp.ClientError as e:
            raise HomeAssistantError(f"Error writing Tdarr global setting {setting_key}: {e}")
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response received writing Tdarr global setting {setting_key}: {response.status} {response.reason}")
        
        return response
        
    async def set_node_paused_state(self, node_id, status):
        _LOGGER.debug("Setting node '%s' paused state to '%s' for %s", node_id, status, self._id)
        data = {
            "data": {
                "nodeID": node_id,
                "nodeUpdates": {
                    "nodePaused": status
                }
            }
        }

        try:
            response = await self._session.post('update-node', json=data)            
        except aiohttp.ClientError as e:
            raise HomeAssistantError(f"Error writing node '{node_id}' setting 'nodePaused': {e}")
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response received writing node '{node_id}' setting 'nodePaused': {response.status} {response.reason}")
        
        return response

    async def refresh_library(self, library_name, mode, folder_path):
        _LOGGER.debug("Refreshing library '%s' using mode '%s' for %s", library_name, mode, self._id)
        stats = await self.get_library_settings()
        libid = None

        if mode == "":
            mode = "scanFindNew"
        for lib in stats:
            if library_name in lib["name"]:
                libid = lib["_id"]

        if libid is None:
            return {"ERROR": "Library Name not found"}


        data = {
            "data": {
                "scanConfig": {
                    "dbID" : libid,
                    "arrayOrPath": folder_path,
                    "mode": mode
                }
            }
        }

        try:
            response = await self._session.post('scan-files', json=data)            
        except aiohttp.ClientError as e:
            raise HomeAssistantError(f"Error starting library scan for '{library_name}': {e}")
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response received starting library scan for '{library_name}': {response.status} {response.reason}")
        
        _LOGGER.debug(await response.text())
        return "SUCCESS"



            
    


    

    
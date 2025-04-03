import asyncio
import logging
from typing import Any
import aiohttp

from homeassistant.exceptions import HomeAssistantError

from .const import WORKER_TYPES

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
        
    async def get_node_id(self, node_name: str) -> str:
        all_node_data = await self.get_nodes()
        node_data = all_node_data.get(node_name)
        if node_data:
            return node_data["_id"]
        else:
            raise HomeAssistantError(f"Could not determine ID for node '{node_name}'.")
        
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
            raise HomeAssistantError(f"Error writing Tdarr global setting {setting_key}: {e}") from e
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response received writing Tdarr global setting {setting_key}: {response.status} {response.reason}")
        
        return response
        
    async def set_node_setting(self, node_id: str, setting_key: str, value: Any):
        """Set the paused state of a node.
        
        args:
            node_id: The Tdarr node ID. NOTE: This may be different from the node key used internally by the integration.
            setting_key: The setting to update for the node.
            state: The paused state to set
        """
        _LOGGER.debug("Setting node '%s' %s state to '%s' for %s", node_id, setting_key, value, self._id)
        data = {
            "data": {
                "nodeID": node_id,
                "nodeUpdates": {
                    setting_key: value
                }
            }
        }

        try:
            response = await self._session.post('update-node', json=data)            
        except aiohttp.ClientError as e:
            raise HomeAssistantError(f"Error writing node '{node_id}' setting '{setting_key}': {e}") from e
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response received writing node '{node_id}' setting '{setting_key}': {response.status} {response.reason}")
        
        return response
    
    async def set_node_worker_limit(self, node_key: str,  worker_type: str, value: int):
        """Set the paused state of a node.
        
        args:
            node_key: The internal ID of the node for the integration. This is usually the node name.
            worker_type: The type of worker to set.
            value: The number to set the worker limit to.
        """
        if value < 0:
            raise HomeAssistantError("Worker limit cannot be negative.")

        if worker_type not in WORKER_TYPES:
            raise HomeAssistantError(f"Worker type must be one of {', '.join(WORKER_TYPES)}")

        _LOGGER.info("Setting %s worker limit for '%s' to %d", worker_type, node_key, value)
        
        current_node_data = (await self.get_nodes()).get(node_key, {})
        if not current_node_data:
            raise HomeAssistantError("Could not determine current worker limit. Node looks to be offline.")
        
        current_worker_limit = current_node_data.get('workerLimits', {}).get(worker_type)
        if current_worker_limit is None:
            raise HomeAssistantError("Could not determine current worker limit.")

        process = ''
        if current_worker_limit < value:
            process = 'increase'
        elif current_worker_limit > value:
            process = 'decrease'
        else:
            _LOGGER.warning("Worker %s limit for '%s' is already at %s", worker_type, node_key, value)
            return

        difference = abs(current_worker_limit - value)
        _LOGGER.debug("Stepping %s worker limit for %s by %d %s", worker_type, node_key, difference, process)

        data = {
            'data': {
                'nodeID': current_node_data['_id'],
                'process': process,
                'workerType': worker_type
            }
        }
        try:
            for i in range(difference):
                _LOGGER.debug("Step %d...", (i + 1))
                await self._session.post('alter-worker-limit', json=data)
            _LOGGER.info("Worker limit updated.")
        except Exception as e:
            raise HomeAssistantError("Error while updating worker limit. Potentially only partially updated.") from e

    async def async_scan_library(self, library_name, mode):
        _LOGGER.debug("Scanning library '%s' using mode '%s' for %s", library_name, mode, self._id)
        all_library_settings = await self.get_library_settings()
        matching_library_settings = [x for x in all_library_settings if x.get("name") == library_name]

        if not matching_library_settings:
            raise HomeAssistantError(f"Library '{library_name}' not found.")
        elif len(matching_library_settings) > 1:
            raise HomeAssistantError(f"Multiple libraries found matching name '{library_name}'.")

        data = {
            "data": {
                "scanConfig": {
                    "dbID" : matching_library_settings[0]["_id"],
                    "arrayOrPath": matching_library_settings[0]["folder"],
                    "mode": mode or "scanFindNew"
                }
            }
        }

        try:
            response = await self._session.post('scan-files', json=data)            
        except aiohttp.ClientError as e:
            raise HomeAssistantError(f"Error starting library scan for '{library_name}': {e}") from e
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response received starting library scan for '{library_name}': {response.status} {response.reason}")
        
        response_text = await response.text()
        if response_text.casefold() != "OK".casefold():
            raise HomeAssistantError(f"Unexpected response starting library scan: {response_text}")
    
    async def async_cancel_worker_item(self, node_name: str, worker_id: str, reason: str) -> None:
        node_id = await self.get_node_id(node_name)
        data = {
            "data": {
                "nodeID": node_id,
                "workerID": worker_id,
                "cause": reason or "user"
            }
        }

        try:
            response = await self._session.post("cancel-worker-item", json=data)        
        except aiohttp.ClientError as e:
            raise HomeAssistantError(f"Error cancelling worker item: {e}") from e
        
        if response.status >= 400:
            raise HomeAssistantError(f"Error response recieved cancelling worker item: {response.status} {response.reason}")
        
        response_text = await response.text()
        if response_text.casefold() != "OK".casefold():
            raise HomeAssistantError(f"Unexpected response cancelling worker item: {response_text}")


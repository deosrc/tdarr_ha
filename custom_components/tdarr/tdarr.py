import logging
from urllib.parse import urljoin
import requests

_LOGGER = logging.getLogger(__name__)

class TdarrServerSession(requests.Session):
    """Requests session with the base URL and headers configured."""

    def __init__(self, url, port, api_key=""):
        super().__init__()
        self.headers.update({
            'Content-Type': 'application/json',
            'x-api-key': api_key
        })
        self._base_url = 'http://' + url + ':' + port + '/api/v2/'

    def request(self, method, url, *args, **kwargs):
        full_url = urljoin(self._base_url, url)
        return super().request(method, full_url, *args, **kwargs)

class TdarrApiClient(object):
    """API Client for interacting with a Tdarr server"""

    def __init__(self, url, port, api_key=""):
        self._session = TdarrServerSession(url, port, api_key)
        
    def get_nodes(self):
        r = self._session.get('get-nodes')
        if r.status_code == 200:
            result = r.json()
            return result
        else:
            return "ERROR"

    def get_status(self):
        r = self._session.get('status')
        if r.status_code == 200:
            result = r.json()
            return result
        else:
            return "ERROR"
    
    def get_libraries(self):
        libraries = {l["_id"]: { "name": l["name"] } for l in self.get_library_settings()} 
        libraries.update({ 
            "": { 
                "name": "All" 
            } 
        }) 
        _LOGGER.debug("Libraries: %s", libraries) 
 
        for key, value in libraries.items():
            value.update(self.get_pies(key))
        
        return libraries

    def get_stats(self):
        post = {
            "data": {
                "collection":"StatisticsJSONDB",
                "mode":"getById",
                "docID":"statistics",
                "obj":{}
                },
            "timeout":1000
        }
        r = self._session.post('cruddb', json = post)
        if r.status_code == 200:
            return r.json()
        else:
            return "ERROR"
    
    def get_library_settings(self):
        post = {
            "data": {
                "collection":"LibrarySettingsJSONDB",
                "mode":"getAll",
                },
            "timeout":20000
        }
        r = self._session.post('cruddb', json = post)
        if r.status_code == 200:
            return r.json()
        else:
            return
    def get_pies(self, libraryID=""):
        post = {
            "data": {
                "libraryId": libraryID
            },
        }
        r = self._session.post('stats/get-pies', json = post)
        if r.status_code == 200:
            return r.json()["pieStats"]
        else:
            return "ERROR"
        
    def get_staged(self):
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
        r = self._session.post('client/staged', json = post)
        if r.status_code == 200:
            return r.json()
        else:
            return "ERROR"
        
    def get_global_settings(self):  
        post = {
            "data": {
                "collection":"SettingsGlobalJSONDB",
                "mode":"getById",
                "docID":"globalsettings",
                "obj":{}
                },
            "timeout":1000
        }
        r = self._session.post('cruddb', json = post)
        if r.status_code == 200:
            return r.json()
        else:
            return {"message": r.text, "status_code": r.status_code, "status": "ERROR"}
        
    def set_global_setting(self, setting_key, value) -> requests.Response:
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
        return self._session.post('cruddb', json=data)
        
    def set_node_paused_state(self, nodeID, status) -> requests.Response:
        data = {
            "data": {
                "nodeID": nodeID,
                "nodeUpdates": {
                    "nodePaused": status
                }
            }
        }
        return self._session.post('update-node', json=data)

    def refresh_library(self, libraryname, mode, folderpath):
        stats = self.get_library_settings()
        libid = None
        _LOGGER.debug(mode)

        if mode == "":
            mode = "scanFindNew"
        for lib in stats:
            if libraryname in lib["name"]:
                libid = lib["_id"]

        if libid is None:
            return {"ERROR": "Library Name not found"}


        data = {
            "data": {
                "scanConfig": {
                    "dbID" : libid,
                    "arrayOrPath": folderpath,
                    "mode": mode
                }
            }
        }

        r = self._session.post("scan-files", json=data)

        if r.status_code == 200:
            _LOGGER.debug(r.text)
            return {"SUCCESS"}
        else:
            return {"ERROR": r.text}



            
    


    

    
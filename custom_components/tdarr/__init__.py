"""The Tdarr integration."""
import asyncio
import logging
from datetime import timedelta

import async_timeout
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_NAME,
    ATTR_MANUFACTURER,
    ATTR_SW_VERSION,
    ATTR_VIA_DEVICE,
)
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    MANUFACTURER,
    SERVERIP,
    SERVERPORT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_DEFAULT,
    COORDINATOR,
    APIKEY
)

from .tdarr import TdarrApiClient

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor", "switch"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Tdarr component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tdarr Server from a config entry."""
    serverip = entry.data[SERVERIP]
    serverport= entry.data[SERVERPORT]
    if APIKEY in entry.data:
        apikey = entry.data[APIKEY]
    else:
        apikey = ""

    if UPDATE_INTERVAL in entry.options:
        update_interval = entry.options[UPDATE_INTERVAL]
    else:
        update_interval = UPDATE_INTERVAL_DEFAULT

    #for ar in entry.data:
        #_LOGGER.debug(ar)

    coordinator = TdarrDataUpdateCoordinator(hass, serverip, serverport, update_interval, apikey)

    await coordinator.async_refresh()  # Get initial data
       # Registers update listener to update config entry when options are updated.
    #_LOGGER.debug(coordinator.data)
    tdarr_options_listener = entry.add_update_listener(options_update_listener) 

   

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR : coordinator,
        "tdarr_options_listener": tdarr_options_listener
    }
        


    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_refresh_library_service(service_call):
        await hass.async_add_executor_job(
            refresh_library, hass, service_call, coordinator
        )

    hass.services.async_register(
        DOMAIN,
        "refresh_library", 
        async_refresh_library_service
    )


    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    #_LOGGER.debug(hass.data[DOMAIN][entry.entry_id])
    hass.data[DOMAIN][entry.entry_id]["tdarr_options_listener"]()
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

def refresh_library(hass, service, coordinator):
    libraryid = service.data.get("library", "")
    mode = service.data.get("mode", "scanFindNew")
    folderpath = service.data.get("folderpath", "")
    status = coordinator.tdarr.refreshLibrary(libraryid, mode, folderpath)
    if "ERROR" in status:
        _LOGGER.debug(status)
        raise HomeAssistantError(status["ERROR"])

async def options_update_listener(
    hass: HomeAssistant,  entry: ConfigEntry 
    ):
        _LOGGER.debug("OPTIONS CHANGE")
        await hass.config_entries.async_reload(entry.entry_id)

class TdarrDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to handle fetching new data about the Tdarr Controller."""

    def __init__(self, hass, serverip, serverport, update_interval, apikey):
        """Initialize the coordinator and set up the Controller object."""
        self._hass = hass
        self.serverip = serverip
        self.serverport = serverport
        self.tdarr = TdarrApiClient(serverip, serverport, apikey)
        self._available = True

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from Tdarr Server."""
        try:
            async with async_timeout.timeout(30):
                data = {}
                data["server"] = await self._hass.async_add_executor_job(
                    self.tdarr.getStatus  # Fetch new status
                )

                data["nodes"] = await self._hass.async_add_executor_job(
                    self.tdarr.getNodes
                )          

                data["stats"] = await self._hass.async_add_executor_job(
                    self.tdarr.getStats
                )

                data["staged"] = await self._hass.async_add_executor_job(
                    self.tdarr.getStaged
                )

                data["libraries"] = await self._hass.async_add_executor_job(
                    self.tdarr.getLibraries
                )

                data["globalsettings"] = await self._hass.async_add_executor_job(
                    self.tdarr.getSettings
                )
                #_LOGGER.debug(self.data)
                if self.data is not None:
                    #_LOGGER.debug(self.data)
                    oldnodes = len(self.data["nodes"])
                    #_LOGGER.debug(len(self.data["nodes"]))
                else:
                    oldnodes = len(data["nodes"])
                #_LOGGER.debug(len(self.data["nodes"])
                if oldnodes != len(data["nodes"]):
                    _LOGGER.debug("Node Change Detected config reload required")
                    # Reload integration to pick up new/changed nodes
                    current_entries = self._hass.config_entries.async_entries(DOMAIN)

                
                    if len(current_entries) > 0:
                        for entry in current_entries:
                            _LOGGER.debug("SHOWING ENTRY")
                            self._hass.config_entries.async_schedule_reload(entry.entry_id)


        

                return data
        except Exception as ex:
            self._available = False  # Mark as unavailable
            _LOGGER.warning(str(ex))
            _LOGGER.warning("Error communicating with Tdarr for %s", self.serverip)
            raise UpdateFailed(
                f"Error communicating with Tdarr for {self.serverip}"
            ) from ex

    async def reloadentities(self):
        _LOGGER.debug("Reloading?")
        current_entries = self._hass.config_entries.async_entries(DOMAIN)
        

        reload_tasks = [
            self._hass.config_entries.async_reload(entry.entry_id)
            for entry in current_entries
        ]

        await asyncio.gather(*reload_tasks)

class TdarrEntity(CoordinatorEntity):

    _attr_has_entity_name = True # Required for reading translation_key from EntityDescription

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, entity_description: EntityDescription):
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        
        # Required for HA 2022.7
        self.coordinator_context = object()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()    

    @property
    def data(self) -> dict:
        return self.coordinator.data

    @property
    def device_info(self):
        """Return device information about this device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.coordinator.serverip)},
            ATTR_NAME: f"Tdarr Server ({self.coordinator.serverip})",
            ATTR_SW_VERSION: self.coordinator.data.get("server", {}).get("version", "Unknown"),
            ATTR_MANUFACTURER: MANUFACTURER
        }


class TdarrServerEntity(TdarrEntity):

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return f"{self.coordinator.serverip}-server-{self.entity_description.key}"


class TdarrLibraryEntity(TdarrEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, library_id: str, entity_description: EntityDescription):
        """Initialize the entity."""
        super().__init__(coordinator, entity_description)
        self.library_id = library_id

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return f"{self.coordinator.serverip}-library-{self.library_id}-{self.entity_description.key}"
    
    @property
    def data(self):
        return self.coordinator.data.get("libraries", {}).get(self.library_id)


class TdarrNodeEntity(TdarrEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, node_id: str, entity_description: EntityDescription):
        """Initialize the entity."""
        super().__init__(coordinator, entity_description)
        self.node_id = node_id

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return f"{self.coordinator.serverip}-node-{self.node_id}-{self.entity_description.key}"
    
    @property
    def data(self):
        return self.coordinator.data.get("nodes", {}).get(self.node_id)

    @property
    def device_info(self):
        """Return device information about this device."""
        device_info = super().device_info
        server_identifier = next(iter(device_info[ATTR_IDENTIFIERS]))

        # Override the identifier and name to produce a new device
        device_info.update({
            ATTR_IDENTIFIERS: {(DOMAIN, self.coordinator.serverip, "node", self.node_id)},
            ATTR_NAME: f"Tdarr Node ({self.data.get("nodeName")})",
            ATTR_VIA_DEVICE: server_identifier,
        })
        return device_info

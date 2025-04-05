"""The Tdarr integration."""
import asyncio
import logging
from typing import (
    Any,
    Dict,
)

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    HomeAssistantError,
    ServiceCall,
    SupportsResponse,
)
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_NAME,
    ATTR_MANUFACTURER,
    ATTR_SW_VERSION,
    ATTR_VIA_DEVICE,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .coordinator import TdarrDataUpdateCoordinator
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

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [
    "binary_sensor",
    "number",
    "sensor",
    "switch",
]

SCAN_LIBRARY_MODE = {
    "find_new": "scanFindNew",
    "fresh": "scanFresh",
}

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

    async def async_scan_library(service_call: ServiceCall):
        library_name = service_call.data["library"]

        mode = SCAN_LIBRARY_MODE.get(service_call.data["mode"])
        if not mode:
            raise HomeAssistantError(f"Invalid scan mode '{service_call.data["mode"]}'")

        await coordinator.tdarr.async_scan_library(library_name, mode)

    hass.services.async_register(
        DOMAIN,
        "scan_library", 
        async_scan_library
    )

    async def async_get_workers(service_call: ServiceCall):
        node_data = await coordinator.tdarr.get_nodes()
        return { k: v.get("workers", []) for k, v in node_data.items() }

    hass.services.async_register(
        DOMAIN,
        "get_workers", 
        async_get_workers,
        supports_response=SupportsResponse.ONLY
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

async def options_update_listener(
    hass: HomeAssistant,  entry: ConfigEntry 
    ):
        _LOGGER.debug("OPTIONS CHANGE")
        await hass.config_entries.async_reload(entry.entry_id)

class TdarrEntity(CoordinatorEntity[TdarrDataUpdateCoordinator]):

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
    
    @property
    def base_attributes(self) -> Dict[str, Any] | None:
        return {
            "server_ip": self.coordinator.serverip,
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
    def data(self) -> dict:
        return self.coordinator.data.get("libraries", {}).get(self.library_id)
    
    @property
    def base_attributes(self) -> Dict[str, Any] | None:
        video_info = self.data.get("video", {})
        return {
            **super().base_attributes,
            "Total Files": self.data.get("totalFiles"),
            "Number of Transcodes": self.data.get("totalTranscodeCount"),
            "Space Saved (GB)": round(self.data.get("sizeDiff"), 0),
            "Number of Health Checks": self.data.get("totalHealthCheckCount"),
            "Codecs": {x["name"]: x["value"] for x in video_info.get("codecs", {})},
            "Containers": {x["name"]: x["value"] for x in video_info.get("containers", {})},
            "Resolutions": {x["name"]: x["value"] for x in video_info.get("resolutions", {})},
        }


class TdarrNodeEntity(TdarrEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, node_key: str, entity_description: EntityDescription):
        """Initialize the entity."""
        super().__init__(coordinator, entity_description)
        self.node_key = node_key

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return f"{self.coordinator.serverip}-node-{self.node_key}-{self.entity_description.key}"
    
    @property
    def tdarr_node_id(self) -> str | None:
        return self.data.get("_id")
    
    @property
    def data(self) -> dict:
        return self.coordinator.data.get("nodes", {}).get(self.node_key, {})

    @property
    def device_info(self):
        """Return device information about this device."""
        device_info = super().device_info
        server_identifier = next(iter(device_info[ATTR_IDENTIFIERS]))

        # Override the identifier and name to produce a new device
        device_info.update({
            ATTR_IDENTIFIERS: {(DOMAIN, self.coordinator.serverip, "node", self.node_key)},
            ATTR_NAME: f"Tdarr Node ({self.data.get("nodeName")})",
            ATTR_VIA_DEVICE: server_identifier,
        })
        return device_info

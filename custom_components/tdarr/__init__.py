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
    ATTR_MODEL,
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
    update_interval = entry.options.get(UPDATE_INTERVAL, UPDATE_INTERVAL_DEFAULT)
    coordinator = TdarrDataUpdateCoordinator(hass, update_interval, entry.data)

    # Get initial data so that correct sensors can be created
    await coordinator.async_refresh()

    # Registers update listener to update config entry when options are updated.
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

    async def async_cancel_worker_item(service_call: ServiceCall):
        await coordinator.tdarr.async_cancel_worker_item(
            service_call.data["node_name"],
            service_call.data["worker_id"],
            service_call.data.get("reason"))

    hass.services.async_register(
        DOMAIN,
        "cancel_worker_item", 
        async_cancel_worker_item
    )

    async def async_get_workers(service_call: ServiceCall):
        node_data = await coordinator.tdarr.async_get_nodes()
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

async def options_update_listener(hass: HomeAssistant,  entry: ConfigEntry):
    _LOGGER.info("Options updated")
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
    
    @property
    def device_info(self):
        return {
            **super().device_info,
            ATTR_MODEL: "Server",
        }


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
            "codecs": {x["name"]: x["value"] for x in video_info.get("codecs", {})},
            "containers": {x["name"]: x["value"] for x in video_info.get("containers", {})},
            "library_id": self.library_id,
            "library_name": self.data.get("name"),
            "resolutions": {x["name"]: x["value"] for x in video_info.get("resolutions", {})},
            "space_saved_gb": round(self.data.get("sizeDiff"), 0),
            "total_files": self.data.get("totalFiles"),
            "total_health_checks": self.data.get("totalHealthCheckCount"),
            "total_transcodes": self.data.get("totalTranscodeCount"),
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
            ATTR_MODEL: "Node",
            ATTR_VIA_DEVICE: server_identifier,
        })
        return device_info
    
    @property
    def base_attributes(self) -> Dict[str, Any] | None:
        return {
            **super().base_attributes,
            "integration_node_key": self.node_key,
            "node_id": self.tdarr_node_id,
            "node_name": self.data.get("nodeName"),
            "remote_address": self.data.get("remoteAddress"),
        }

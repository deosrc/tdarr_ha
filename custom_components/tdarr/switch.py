from dataclasses import replace
import logging

from homeassistant.core import callback
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription
)

from . import TdarrEntity
from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)

SERVER_ENTITY_DESCRIPTIONS = {
    SwitchEntityDescription(
        key="pauseAll",
        translation_key="pause_all",
        icon="mdi:pause-circle"
    ),
    SwitchEntityDescription(
        key="ignoreSchedules",
        translation_key="ignore_schedules",
        icon="mdi:calendar-remove"
    ),
}

NODE_PAUSE_ENTITY_DESCRIPTION = SwitchEntityDescription(
    key="node_pause",
    translation_key="node_pause"
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Switch from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    switches = []

    # Server Switches
    for description in SERVER_ENTITY_DESCRIPTIONS:
        switches.append(TdarrSwitch(entry, entry.data["globalsettings"], description.key, config_entry.options, description))

    # Node Switches
    for _, value in entry.data["nodes"].items():
        description = replace(
            NODE_PAUSE_ENTITY_DESCRIPTION,
            translation_placeholders={
                "node_name": value["nodeName"]
            }
        )
        sw = TdarrSwitch(entry, value, value["_id"], config_entry.options, description)
        switches.append(sw)

    async_add_entities(switches, False)

class TdarrSwitch(TdarrEntity, SwitchEntity):
    """Define the Switch for turning ignition off/on"""

    _attr_has_entity_name = True # Required for reading translation_key from EntityDescription

    def __init__(self, coordinator, switch, name, options, entity_description: SwitchEntityDescription):
        _LOGGER.debug(name)
        if "nodeName" in switch:
            self._device_id = "tdarr_node_" + switch["nodeName"] + "_paused"
        elif name == "pauseAll":
            self._device_id = "tdarr_pause_all"
        elif name == "ignoreSchedules":
            self._device_id = "tdarr_ignore_schedules"
        else:
            self._device_id = "tdarr_node_" + switch["_id"] + "_paused"
        self.switch = switch
        self.coordinator = coordinator
        self.entity_description = entity_description
        self.object_name = name
        # Required for HA 2022.7
        self.coordinator_context = object()

    async def async_turn_on(self, **kwargs):
        return await self.async_set_paused(True)

    async def async_turn_off(self, **kwargs):
        return await self.async_set_paused(False)

    async def async_set_paused(self, paused: bool):
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.object_name,
            paused
        )

        if update == "OK":
            self._attr_is_on = paused 
            self.async_write_ha_state() 
            await self.coordinator.async_request_refresh() 
 
    @callback 
    def _handle_coordinator_update(self) -> None: 
        """Handle updated data from the coordinator.""" 
        if  self.object_name == "pauseAll":
            self._attr_is_on = self.coordinator.data["globalsettings"]["pauseAllNodes"]
        elif self.object_name == "ignoreSchedules":
            self._attr_is_on = self.coordinator.data["globalsettings"]["ignoreSchedules"]
        else:
            for _, value in self.coordinator.data["nodes"].items():
                if value["_id"] == self.switch["_id"]:
                    self._attr_is_on = value["nodePaused"]
        self.async_write_ha_state()


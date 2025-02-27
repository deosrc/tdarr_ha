import logging

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
        translation_key="pauseAll",
        icon="mdi:pause-circle"
    ),
    SwitchEntityDescription(
        key="ignoreSchedules",
        translation_key="ignoreSchedules",
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
        sw = TdarrSwitch(entry, value, value["_id"], config_entry.options, NODE_PAUSE_ENTITY_DESCRIPTION)
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
        self._state = None
        self.object_name = name
        # Required for HA 2022.7
        self.coordinator_context = object()

    async def async_turn_on(self, **kwargs):
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.object_name,
            True
        )

        if update == "OK":
            self._state = True
            self.switch["nodePaused"] = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.object_name,
            False
        )

        if update == "OK":
            self._state = False
            self.switch["nodePaused"] = False
            self.async_write_ha_state()

    @property
    def device_id(self):
        return self.device_id

    @property
    def is_on(self):
        if self._state == True:
            self._state = None
            return True
        elif self._state == False:
            self._state = None
            return False
        if  self.object_name == "pauseAll":
            return self.coordinator.data["globalsettings"]["pauseAllNodes"]
        elif self.object_name == "ignoreSchedules":
            return self.coordinator.data["globalsettings"]["ignoreSchedules"]
        for key, value in self.coordinator.data["nodes"].items():
            if value["_id"] == self.switch["_id"]:
                return value["nodePaused"]

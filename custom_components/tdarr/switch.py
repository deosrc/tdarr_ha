from dataclasses import replace
import logging

from homeassistant.core import callback
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription
)

from . import (
    TdarrServerEntity,
    TdarrNodeEntity,
)
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

NODE_ENTITY_DESCRIPTIONS = {
    SwitchEntityDescription(
        key="paused",
        translation_key="node_paused"
    )
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Switch from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    switches = []

    # Server Switches
    for description in SERVER_ENTITY_DESCRIPTIONS:
        switches.append(TdarrServerSwitch(entry, config_entry.options, description))

    # Node Switches
    for key in entry.data["nodes"]:
        for description in NODE_ENTITY_DESCRIPTIONS:
            sw = TdarrNodeSwitch(entry, key, config_entry.options, description)
            switches.append(sw)

    async_add_entities(switches, False)

class TdarrServerSwitch(TdarrServerEntity, SwitchEntity):
    """A Tdarr server level switch"""

    def __init__(self, coordinator, options, entity_description: SwitchEntityDescription):
        _LOGGER.info("Creating server level switch %s", entity_description.key)
        super().__init__(coordinator, entity_description)

        if entity_description.key == "pauseAll":
            self._device_id = "tdarr_pause_all"
        elif entity_description.key == "ignoreSchedules":
            self._device_id = "tdarr_ignore_schedules"
        else:
            raise NotImplementedError(f"Unknown server switch key {entity_description.key}")
        
        # Required for HA 2022.7
        self.coordinator_context = object()

    async def async_turn_on(self, **kwargs):
        return await self.async_set_state(True)

    async def async_turn_off(self, **kwargs):
        return await self.async_set_state(False)

    async def async_set_state(self, paused: bool):
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.entity_description.key,
            paused
        )

        if update == "OK":
            self._attr_is_on = paused 
            self.async_write_ha_state() 
            await self.coordinator.async_request_refresh() 
 
    @callback 
    def _handle_coordinator_update(self) -> None: 
        """Handle updated data from the coordinator.""" 
        if  self.entity_description.key == "pauseAll":
            self._attr_is_on = self.coordinator.data["globalsettings"]["pauseAllNodes"]
        elif self.entity_description.key == "ignoreSchedules":
            self._attr_is_on = self.coordinator.data["globalsettings"]["ignoreSchedules"]
        else:
            raise NotImplementedError(f"Unknown server switch key {self.entity_description.key}")
            
        self.async_write_ha_state()

class TdarrNodeSwitch(TdarrNodeEntity, SwitchEntity):
    """A Tdarr node level switch"""

    def __init__(self, coordinator, node_id, options, entity_description: SwitchEntityDescription):
        _LOGGER.info("Creating node %s level switch %s", node_id, entity_description.key)
        super().__init__(coordinator, node_id, entity_description)
        # Required for HA 2022.7
        self.coordinator_context = object()

    async def async_turn_on(self, **kwargs):
        return await self.async_set_state(True)

    async def async_turn_off(self, **kwargs):
        return await self.async_set_state(False)

    async def async_set_state(self, paused: bool):
        if self.entity_description.key != 'paused':
            raise NotImplementedError(f"Unknown node switch type {self.entity_description.key}")
        
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.node_id,
            paused
        )

        if update == "OK":
            self._attr_is_on = paused 
            self.async_write_ha_state() 
            await self.coordinator.async_request_refresh() 
 
    @callback 
    def _handle_coordinator_update(self) -> None: 
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.node_data["nodePaused"]
        self.async_write_ha_state()


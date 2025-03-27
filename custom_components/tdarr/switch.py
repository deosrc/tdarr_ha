from dataclasses import dataclass, replace
import logging
from typing import Awaitable, Callable

import aiohttp
from homeassistant.core import callback
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription
)
from homeassistant.exceptions import HomeAssistantError

from . import (
    TdarrServerEntity,
    TdarrNodeEntity,
)
from .coordinator import TdarrDataUpdateCoordinator
from .const import DOMAIN, COORDINATOR
from .api import TdarrApiClient

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True) 
class TdarrSwitchEntityDescription(SwitchEntityDescription): 
    """Details of a Tdarr switch entity""" 
 
    value_fn: Callable[[dict], bool | None]

@dataclass(frozen=True, kw_only=True) 
class TdarrServerSwitchEntityDescription(TdarrSwitchEntityDescription): 
    """Details of a Tdarr server switch entity""" 
 
    update_fn: Callable[[TdarrApiClient, bool], Awaitable]

@dataclass(frozen=True, kw_only=True) 
class TdarrNodeSwitchEntityDescription(TdarrSwitchEntityDescription): 
    """Details of a Tdarr node switch entity""" 
 
    update_fn: Callable[[TdarrApiClient, str, bool], Awaitable]

SERVER_ENTITY_DESCRIPTIONS = {
    TdarrServerSwitchEntityDescription(
        key="pause_all",
        translation_key="pause_all",
        icon="mdi:pause-circle",
        value_fn=lambda data: data.get("globalsettings", {}).get("pauseAllNodes"),
        update_fn=lambda server, state: server.set_global_setting("pauseAll", state),
    ),
    TdarrServerSwitchEntityDescription(
        key="ignore_schedules",
        translation_key="ignore_schedules",
        icon="mdi:calendar-remove",
        value_fn=lambda data: data.get("globalsettings", {}).get("ignoreSchedules"),
        update_fn=lambda server, state: server.set_global_setting("ignoreSchedules", state),
    ),
}

NODE_ENTITY_DESCRIPTIONS = {
    TdarrNodeSwitchEntityDescription(
        key="paused",
        translation_key="node_paused",
        icon="mdi:pause-circle",
        value_fn=lambda data: data.get("nodePaused"),
        update_fn=lambda server, node_id, state: server.set_node_setting(node_id, "nodePaused", state),
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

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, options, entity_description: TdarrServerSwitchEntityDescription):
        _LOGGER.info("Creating server level switch %s", entity_description.key)
        super().__init__(coordinator, entity_description)

    @property
    def description(self) -> TdarrServerSwitchEntityDescription:
        return self.entity_description

    async def async_turn_on(self, **kwargs):
        return await self.async_set_state(True)

    async def async_turn_off(self, **kwargs):
        return await self.async_set_state(False)

    async def async_set_state(self, state: bool):
        await self.description.update_fn(self.coordinator.tdarr, state)
        self._attr_is_on = state
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
 
    @callback 
    def _handle_coordinator_update(self) -> None: 
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.description.value_fn(self.data)
        self.async_write_ha_state()

class TdarrNodeSwitch(TdarrNodeEntity, SwitchEntity):
    """A Tdarr node level switch"""

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, node_id: str, options, entity_description: TdarrNodeSwitchEntityDescription):
        _LOGGER.info("Creating node %s level switch %s", node_id, entity_description.key)
        super().__init__(coordinator, node_id, entity_description)

    @property
    def description(self) -> TdarrNodeSwitchEntityDescription:
        return self.entity_description

    async def async_turn_on(self, **kwargs):
        return await self.async_set_state(True)

    async def async_turn_off(self, **kwargs):
        return await self.async_set_state(False)

    async def async_set_state(self, state: bool):
        await self.description.update_fn(self.coordinator.tdarr, self.node_id, state)
        self._attr_is_on = state 
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh() 
 
    @callback 
    def _handle_coordinator_update(self) -> None: 
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.description.value_fn(self.data)
        self.async_write_ha_state()


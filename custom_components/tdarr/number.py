from dataclasses import dataclass
import logging
from typing import Callable

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)

from . import (
    TdarrServerEntity,
    TdarrNodeEntity,
)
from .coordinator import TdarrDataUpdateCoordinator
from .const import (
    DOMAIN,
    COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True) 
class TdarrNumberEntityDescription(NumberEntityDescription): 
    """Details of a Tdarr sensor entity""" 
 
    value_fn: Callable[[dict], int | None]
    attributes_fn: Callable[[dict], dict | None] = None

SERVER_ENTITY_DESCRIPTIONS = {
}

NODE_ENTITY_DESCRIPTIONS = {
    TdarrNumberEntityDescription(
        key="worker_limit_healthcheck_cpu",
        translation_key="worker_limit_healthcheck_cpu",
        icon="mdi:heart-pulse",
        min_value=0,
        step=1,
        mode=NumberMode.BOX,
        value_fn=lambda data: data.get("workerLimits", {}).get("healthcheckcpu")
    ),
    TdarrNumberEntityDescription(
        key="worker_limit_healthcheck_gpu",
        translation_key="worker_limit_healthcheck_gpu",
        icon="mdi:heart-pulse",
        min_value=0,
        step=1,
        mode=NumberMode.BOX,
        value_fn=lambda data: data.get("workerLimits", {}).get("healthcheckgpu")
    ),
    TdarrNumberEntityDescription(
        key="worker_limit_transcode_cpu",
        translation_key="worker_limit_transcode_cpu",
        icon="mdi:video",
        min_value=0,
        step=1,
        mode=NumberMode.BOX,
        value_fn=lambda data: data.get("workerLimits", {}).get("transcodecpu")
    ),
    TdarrNumberEntityDescription(
        key="worker_limit_transcode_gpu",
        translation_key="worker_limit_transcode_gpu",
        icon="mdi:video",
        min_value=0,
        step=1,
        mode=NumberMode.BOX,
        value_fn=lambda data: data.get("workerLimits", {}).get("transcodegpu")
    ),
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    sensors = []
    
    # Server Number Entities
    for description in SERVER_ENTITY_DESCRIPTIONS:
        sensors.append(TdarrServerNumberEntity(entry, config_entry.options, description))

    # Node Number Entities
    for node_id in entry.data["nodes"]:
        for description in NODE_ENTITY_DESCRIPTIONS:
            sensors.append(TdarrNodeNumberEntity(entry, node_id, config_entry.options, description))

    async_add_entities(sensors, True)


class TdarrServerNumberEntity(TdarrServerEntity, NumberEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, options, entity_description: TdarrNumberEntityDescription):
        _LOGGER.info("Creating server level number entity %s", entity_description.key)
        super().__init__(coordinator, entity_description)

    @property
    def description(self) -> TdarrNumberEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        return self.description.value_fn(self.data)

    @property
    def extra_state_attributes(self):
        if self.description.attributes_fn:
            return self.description.attributes_fn(self.data)
        

class TdarrNodeNumberEntity(TdarrNodeEntity, NumberEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, node_key: str, options, entity_description: TdarrNumberEntityDescription):
        _LOGGER.info("Creating node %s level number entity %s", node_key, entity_description.key)
        super().__init__(coordinator, node_key, entity_description)

    @property
    def description(self) -> TdarrNumberEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        return self.description.value_fn(self.data)

    @property
    def extra_state_attributes(self):
        if self.description.attributes_fn:
            return self.description.attributes_fn(self.data)
        else:
            return self.data
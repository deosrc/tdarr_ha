from dataclasses import dataclass
import logging
from typing import (
    Any,
    Callable,
    Dict,
)

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
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
class TdarrBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Details of a Tdarr sensor entity"""

    value_fn: Callable[[dict], bool | None]
    attributes_fn: Callable[[dict], dict | None] = None

SERVER_ENTITY_DESCRIPTIONS = {
}

NODE_ENTITY_DESCRIPTIONS = {
    TdarrBinarySensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:server-network-outline",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: bool(data),
    ),
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    sensors = []

    # Server Binary Sensors
    for description in SERVER_ENTITY_DESCRIPTIONS:
        sensors.append(TdarrServerBinarySensor(entry, config_entry.options, description))

    # Node Binary Sensors
    for node_id in entry.data["nodes"]:
        for description in NODE_ENTITY_DESCRIPTIONS:
            sensors.append(TdarrNodeBinarySensor(entry, node_id, config_entry.options, description))

    async_add_entities(sensors, True)


class TdarrServerBinarySensor(TdarrServerEntity, BinarySensorEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, options, entity_description: TdarrBinarySensorEntityDescription):
        _LOGGER.info("Creating server level %s binary sensor entity", entity_description.key)
        super().__init__(coordinator, entity_description)

    @property
    def description(self) -> TdarrBinarySensorEntityDescription:
        return self.entity_description

    @property
    def is_on(self):
        try:
            return self.description.value_fn(self.data)
        except Exception as e:
            raise ValueError(f"Unable to get value for {self.entity_description.key} binary sensor entity") from e

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        try:
            attributes = self.base_attributes
            if self.description.attributes_fn:
                attributes = {**attributes, **self.description.attributes_fn(self.data)}
            return attributes
        except Exception as e:
            raise ValueError(f"Unable to get attributes for {self.entity_description.key} binary sensor entity") from e


class TdarrNodeBinarySensor(TdarrNodeEntity, BinarySensorEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, node_key: str, options, entity_description: TdarrBinarySensorEntityDescription):
        _LOGGER.info("Creating node %s level %s binary sensor entity", node_key, entity_description.key)
        super().__init__(coordinator, node_key, entity_description)

    @property
    def description(self) -> TdarrBinarySensorEntityDescription:
        return self.entity_description

    @property
    def is_on(self):
        try:
            return self.description.value_fn(self.data)
        except Exception as e:
            raise ValueError(f"Unable to get value for node '{self.node_key}' {self.entity_description.key} binary sensor entity") from e

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        try:
            attributes = self.base_attributes
            if self.description.attributes_fn:
                attributes = {**attributes, **self.description.attributes_fn(self.data)}
            return attributes
        except Exception as e:
            raise ValueError(f"Unable to get attributes for node '{self.node_key}' {self.entity_description.key} binary sensor entity") from e

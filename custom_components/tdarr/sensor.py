from dataclasses import dataclass, replace
import logging
from typing import (
    Any,
    Callable,
    Dict,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)

from . import (
    TdarrServerEntity,
    TdarrLibraryEntity,
    TdarrNodeEntity,
)
from .coordinator import TdarrDataUpdateCoordinator
from .const import (
    DOMAIN,
    COORDINATOR,
    WORKER_TYPE_HEALTHCHECK,
    WORKER_TYPE_TRANSCODE,
)

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True) 
class TdarrSensorEntityDescription(SensorEntityDescription): 
    """Details of a Tdarr sensor entity""" 
 
    value_fn: Callable[[dict], str | int | float | None]
    attributes_fn: Callable[[dict], dict | None] = None

def get_node_fps(node_data: dict, worker_type: str = "") -> int:
    return sum([worker_data.get("fps", 0) for _, worker_data in node_data.get("workers", {}).items() if worker_data.get("workerType", "").startswith(worker_type)])

def get_node_memory_percent(node_data: dict) -> float:
    os_resource_stats: Dict[str, str] = node_data.get("resStats", {}).get("os", {})
    used_gb_raw = os_resource_stats.get("memUsedGB")
    total_gb_raw = os_resource_stats.get("memTotalGB")
    if used_gb_raw is None or total_gb_raw is None:
        return None
    
    return (float(used_gb_raw) / float(total_gb_raw)) * 100

SERVER_ENTITY_DESCRIPTIONS = {
    TdarrSensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:server",
        value_fn=lambda data: data.get("server", {}).get("status"),
        attributes_fn=lambda data: data.get("server", {})
    ),
    TdarrSensorEntityDescription(
        key="space_saved",
        translation_key="space_saved",
        icon="mdi:harddisk",
        native_unit_of_measurement="GB",
        suggested_display_precision=2,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("sizeDiff"),
        attributes_fn=lambda data: data.get("stats" ,{})
    ),
    TdarrSensorEntityDescription(
        key="staged",
        translation_key="staged",
        icon="mdi:file-sync",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("staged", {}).get("totalCount"),
    ),
    TdarrSensorEntityDescription(
        key="transcode_queued",
        translation_key="transcode_queued",
        icon="mdi:file-arrow-up-down",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table1Count"),
    ),
    TdarrSensorEntityDescription(
        key="transcode_success",
        translation_key="transcode_success",
        icon="mdi:file-check",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table2Count"),
    ),
    TdarrSensorEntityDescription(
        key="transcode_error",
        translation_key="transcode_error",
        icon="mdi:file-alert",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table3Count"),
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_queued",
        translation_key="healthcheck_queued",
        icon="mdi:heart-pulse",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table4Count"),
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_success",
        translation_key="healthcheck_success",
        icon="mdi:heart",
        native_unit_of_measurement="files",
        value_fn=lambda data: data.get("stats", {}).get("table5Count"),
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_error",
        translation_key="healthcheck_error",
        icon="mdi:heart-broken",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table6Count"),
    ),
    TdarrSensorEntityDescription(
        key="total_frame_rate",
        translation_key="total_frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sum([get_node_fps(node_data) for _, node_data in data.get("nodes", {}).items()]),
    ),
    TdarrSensorEntityDescription(
        key="total_healthcheck_frame_rate",
        translation_key="total_healthcheck_frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sum([get_node_fps(node_data, worker_type=WORKER_TYPE_HEALTHCHECK) for _, node_data in data.get("nodes", {}).items()]),
    ),
    TdarrSensorEntityDescription(
        key="total_transcode_frame_rate",
        translation_key="total_transcode_frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sum([get_node_fps(node_data, worker_type=WORKER_TYPE_TRANSCODE) for _, node_data in data.get("nodes", {}).items()]),
    ),
}

LIBRARY_ENTITY_DESCRIPTIONS = {
    TdarrSensorEntityDescription(
        key="library",
        translation_key="library",
        icon="mdi:folder-multiple",
        native_unit_of_measurement="files",
        value_fn=lambda data: data.get("totalFiles"),
    )
}

NODE_ENTITY_DESCRIPTIONS = {
    TdarrSensorEntityDescription(
        key="frame_rate",
        translation_key="frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: get_node_fps(data)
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_frame_rate",
        translation_key="healthcheck_frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: get_node_fps(data, worker_type=WORKER_TYPE_HEALTHCHECK)
    ),
    TdarrSensorEntityDescription(
        key="transcode_frame_rate",
        translation_key="transcode_frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: get_node_fps(data, worker_type=WORKER_TYPE_TRANSCODE)
    ),
    TdarrSensorEntityDescription(
        key="os_cpu_usage",
        translation_key="os_cpu_usage",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("resStats", {}).get("os", {}).get("cpuPerc")
    ),
    TdarrSensorEntityDescription(
        key="os_memory_usage",
        translation_key="os_memory_usage",
        icon="mdi:memory",
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: get_node_memory_percent(data),
        attributes_fn=lambda data: {
            "Used GB": data.get("resStats", {}).get("os", {}).get("memUsedGB"),
            "Total GB": data.get("resStats", {}).get("os", {}).get("memTotalGB"),
        }
    )
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    sensors = []
    
    # Server Sensors
    for description in SERVER_ENTITY_DESCRIPTIONS:
        sensors.append(TdarrServerSensor(entry, config_entry.options, description))

    # Library Sensors
    for library_id, data in entry.data["libraries"].items():
        for description in LIBRARY_ENTITY_DESCRIPTIONS:
            description = replace(
                description,
                translation_placeholders={
                    "library_name": data["name"]
                }
            )
            sensors.append(TdarrLibrarySensor(entry, library_id, config_entry.options, description))

    # Node Sensors
    for node_id in entry.data["nodes"]:
        for description in NODE_ENTITY_DESCRIPTIONS:
            sensors.append(TdarrNodeSensor(entry, node_id, config_entry.options, description))

    async_add_entities(sensors, True)


class TdarrServerSensor(TdarrServerEntity, SensorEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, options, entity_description: TdarrSensorEntityDescription):
        _LOGGER.info("Creating server level %s sensor entity", entity_description.key)
        super().__init__(coordinator, entity_description)

    @property
    def description(self) -> TdarrSensorEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        try:
            return self.description.value_fn(self.data)
        except Exception as e:
            raise ValueError(f"Unable to get value for {self.entity_description.key} sensor entity") from e

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        try:
            attributes = self.base_attributes
            if self.description.attributes_fn:
                attributes = {**attributes, **self.description.attributes_fn(self.data)}
            return attributes
        except Exception as e:
            raise ValueError(f"Unable to get attributes for {self.entity_description.key} sensor entity") from e


class TdarrLibrarySensor(TdarrLibraryEntity, SensorEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, library_id: str, options, entity_description: TdarrSensorEntityDescription):
        _LOGGER.info("Creating library %s level %s sensor entity", library_id, entity_description.key)
        super().__init__(coordinator, library_id, entity_description)

    @property
    def description(self) -> TdarrSensorEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        try:
            return self.description.value_fn(self.data)
        except Exception as e:
            raise ValueError(f"Unable to get value for library '{self.library_id}' {self.entity_description.key} sensor entity") from e

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        try:
            attributes = self.base_attributes
            if self.description.attributes_fn:
                attributes = {**attributes, **self.description.attributes_fn(self.data)}
            return attributes
        except Exception as e:
            raise ValueError(f"Unable to get attributes for library '{self.library_id}' {self.entity_description.key} sensor entity") from e
        

class TdarrNodeSensor(TdarrNodeEntity, SensorEntity):

    def __init__(self, coordinator: TdarrDataUpdateCoordinator, node_key: str, options, entity_description: TdarrSensorEntityDescription):
        _LOGGER.info("Creating node %s level %s sensor entity", node_key, entity_description.key)
        super().__init__(coordinator, node_key, entity_description)

    @property
    def description(self) -> TdarrSensorEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        try:
            return self.description.value_fn(self.data)
        except Exception as e:
            raise ValueError(f"Unable to get value for node '{self.node_key}' {self.entity_description.key} sensor entity") from e

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        try:
            attributes = self.base_attributes
            if self.description.attributes_fn:
                attributes = {**attributes, **self.description.attributes_fn(self.data)}
            return attributes
        except Exception as e:
            raise ValueError(f"Unable to get attributes for node '{self.node_key}' {self.entity_description.key} sensor entity") from e
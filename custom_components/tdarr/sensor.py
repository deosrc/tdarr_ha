from dataclasses import dataclass, replace
import logging
from typing import Callable

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
from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True) 
class TdarrSensorEntityDescription(SensorEntityDescription): 
    """Details of a Tdarr sensor entity""" 
 
    value_fn: Callable[[dict], str | int | float | None]

def get_node_fps(node_data: dict) -> int:
    return sum([worker_data.get("fps", 0) for _, worker_data in node_data.get("workers", {}).items()])

SERVER_ENTITY_DESCRIPTIONS = {
    TdarrSensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:server",
        value_fn=lambda data: data.get("server", {}).get("status"),
    ),
    TdarrSensorEntityDescription(
        key="space_saved",
        translation_key="space_saved",
        icon="mdi:harddisk",
        native_unit_of_measurement="GB",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("sizeDiff"),
    ),
    TdarrSensorEntityDescription(
        key="staged",
        translation_key="staged",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("staged", {}).get("totalCount"),
    ),
    TdarrSensorEntityDescription(
        key="transcode_queued",
        translation_key="transcode_queued",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table1Count"),
    ),
    TdarrSensorEntityDescription(
        key="transcode_success",
        translation_key="transcode_success",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table2Count"),
    ),
    TdarrSensorEntityDescription(
        key="transcode_error",
        translation_key="transcode_error",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table3Count"),
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_queued",
        translation_key="healthcheck_queued",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("table4Count"),
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_success",
        translation_key="healthcheck_success",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files",
        value_fn=lambda data: data.get("stats", {}).get("table5Count"),
    ),
    TdarrSensorEntityDescription(
        key="healthcheck_error",
        translation_key="healthcheck_error",
        icon="mdi:medication-outline",
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
        key="status",
        translation_key="status",
        icon="mdi:server-network-outline",
        value_fn=lambda _: "Online",
    ),
    TdarrSensorEntityDescription(
        key="frame_rate",
        translation_key="frame_rate",
        icon="mdi:video",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: get_node_fps(data)
    )
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    sensors = []
    
    # Server Status Sensors
    for description in SERVER_ENTITY_DESCRIPTIONS:
        sensors.append(TdarrServerSensor(entry, config_entry.options, description))

    # Server Library Sensors
    for library_id, data in entry.data["libraries"].items():
        for description in LIBRARY_ENTITY_DESCRIPTIONS:
            description = replace(
                description,
                translation_placeholders={
                    "library_name": data["name"]
                }
            )
            sensors.append(TdarrLibrarySensor(entry, library_id, config_entry.options, description))

    # Server Node Sensors
    for node_id in entry.data["nodes"]:
        for description in NODE_ENTITY_DESCRIPTIONS:
            sensors.append(TdarrNodeSensor(entry, node_id, config_entry.options, description))

    async_add_entities(sensors, True)


class TdarrServerSensor(TdarrServerEntity, SensorEntity):

    def __init__(self, coordinator, options, entity_description: TdarrSensorEntityDescription):
        _LOGGER.info("Creating server level sensor %s", entity_description.key)
        super().__init__(coordinator, entity_description)

    @property
    def description(self) -> TdarrSensorEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        return self.description.value_fn(self.data)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "server":
            return self.data.get("server", {})
        elif self.entity_description.key == "space_saved":
            return self.data.get("stats", {})


class TdarrLibrarySensor(TdarrLibraryEntity, SensorEntity):

    def __init__(self, coordinator, library_id, options, entity_description: TdarrSensorEntityDescription):
        _LOGGER.info("Creating library %s level sensor %s", library_id, entity_description.key)
        super().__init__(coordinator, library_id, entity_description)

    @property
    def description(self) -> TdarrSensorEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        return self.description.value_fn(self.data)

    @property
    def extra_state_attributes(self):
        video_info = self.data.get("video", {})
        return {
            "Total Files": self.data.get("totalFiles"),
            "Number of Transcodes": self.data.get("totalTranscodeCount"),
            "Space Saved (GB)": round(self.data.get("sizeDiff"), 0),
            "Number of Health Checks": self.data.get("totalHealthCheckCount"),
            "Codecs": {x["name"]: x["value"] for x in video_info.get("codecs", {})},
            "Containers": {x["name"]: x["value"] for x in video_info.get("containers", {})},
            "Resolutions": {x["name"]: x["value"] for x in video_info.get("resolutions", {})},
        }
        

class TdarrNodeSensor(TdarrNodeEntity, SensorEntity):

    def __init__(self, coordinator, node_id, options, entity_description: TdarrSensorEntityDescription):
        _LOGGER.info("Creating node %s level sensor %s", node_id, entity_description.key)
        super().__init__(coordinator, node_id, entity_description)

    @property
    def description(self) -> TdarrSensorEntityDescription:
        return self.entity_description

    @property 
    def native_value(self):
        return self.description.value_fn(self.data)

    @property
    def extra_state_attributes(self):
        return self.data
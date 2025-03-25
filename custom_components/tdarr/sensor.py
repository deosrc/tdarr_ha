from dataclasses import dataclass, replace
import logging
from typing import Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass
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
 
    value_fn: Callable[[dict], str | int | float | None] | None = None 

SERVER_ENTITY_DESCRIPTIONS = {
    TdarrSensorEntityDescription(
        key="server",
        translation_key="server",
        icon="mdi:server"
    ),
    TdarrSensorEntityDescription(
        key="stats_spacesaved",
        translation_key="stats_spacesaved",
        icon="mdi:harddisk",
        native_unit_of_measurement="GB",
        device_class=SensorDeviceClass.DATA_SIZE
    ),
    TdarrSensorEntityDescription(
        key="stats_transcodefilesremaining",
        translation_key="stats_transcodefilesremaining",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    TdarrSensorEntityDescription(
        key="stats_transcodedcount",
        translation_key="stats_transcodedcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    TdarrSensorEntityDescription(
        key="stats_stagedcount",
        translation_key="stats_stagedcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    TdarrSensorEntityDescription(
        key="stats_healthcount",
        translation_key="stats_healthcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    TdarrSensorEntityDescription(
        key="stats_transcodeerrorcount",
        translation_key="stats_transcodeerrorcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    TdarrSensorEntityDescription(
        key="stats_healtherrorcount",
        translation_key="stats_healtherrorcount",
        icon="mdi:medication-outline",
        native_unit_of_measurement="files"
    ),
    TdarrSensorEntityDescription(
        key="stats_totalfps",
        translation_key="stats_totalfps",
        icon="mdi:video",
        native_unit_of_measurement="fps"
    ),
}

LIBRARY_ENTITY_DESCRIPTION = TdarrSensorEntityDescription(
    key="library",
    translation_key="library",
    icon="mdi:folder-multiple",
    native_unit_of_measurement="files"
)

NODE_ENTITY_DESCRIPTIONS = {
    TdarrSensorEntityDescription(
        key="node",
        translation_key="node",
        icon="mdi:server-network-outline",
    ),
    TdarrSensorEntityDescription(
        key="nodefps",
        translation_key="nodefps",
        icon="mdi:video",
        native_unit_of_measurement="fps"
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
        description = replace(
            LIBRARY_ENTITY_DESCRIPTION,
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
        if self.description.value_fn:
            return self.description.value_fn(self.data)

        if self.entity_description.key == "server":
            return self.data.get("server", {}).get("status")
        elif self.entity_description.key == "stats_spacesaved":
            return round(self.data.get("stats",{}).get("sizeDiff", 0), 2)
        elif self.entity_description.key == "stats_transcodefilesremaining":
            return self.data.get("stats",{}).get("table1Count", 0)
        elif self.entity_description.key == "stats_transcodedcount":
            return self.data.get("stats",{}).get("table2Count", 0)
        elif self.entity_description.key == "stats_stagedcount":
            return self.data.get("staged",{}).get("totalCount", 0)
        elif self.entity_description.key == "stats_healthcount":
            return self.data.get("stats",{}).get("table4Count", 0)
        elif self.entity_description.key == "stats_transcodeerrorcount":
            return self.data.get("stats",{}).get("table3Count", 0)
        elif self.entity_description.key == "stats_healtherrorcount":
            return self.data.get("stats",{}).get("table6Count", 0)
        elif self.entity_description.key == "stats_totalfps":
            fps = 0
            for _, node_values in self.data["nodes"].items():
                for _, worker_values in node_values.get("workers", {}).items():
                    fps += worker_values.get("fps", 0)
            return fps

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "server":
            return self.data.get("server", {})
        elif self.entity_description.key == "stats_spacesaved":
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
        if self.description.value_fn:
            return self.description.value_fn(self.data)

        if self.entity_description.key == "library":
            return self.data.get("totalFiles")

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
        if self.description.value_fn:
            return self.description.value_fn(self.data)

        if self.entity_description.key == "node":
            return "Online"
        elif self.entity_description.key == "nodefps":
            fps = 0
            for _, worker_values in self.data.get("workers", {}).items():
                fps += worker_values.get("fps", 0)
            return fps

    @property
    def extra_state_attributes(self):
        return self.data
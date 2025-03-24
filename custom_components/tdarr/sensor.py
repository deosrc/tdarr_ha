import logging
import re

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass
)

from . import TdarrEntity
from .const import DOMAIN, COORDINATOR, SENSORS

_LOGGER = logging.getLogger(__name__)

SERVER_ENTITY_DESCRIPTIONS = {
    SensorEntityDescription(
        key="server",
        icon="mdi:server"
    ),
    SensorEntityDescription(
        key="stats_spacesaved",
        icon="mdi:harddisk",
        native_unit_of_measurement="GB",
        device_class=SensorDeviceClass.DATA_SIZE
    ),
    SensorEntityDescription(
        key="stats_transcodefilesremaining",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_transcodedcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_stagedcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_healthcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_transcodeerrorcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_healtherrorcount",
        icon="mdi:medication-outline",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_totalfps",
        icon="mdi:video",
        native_unit_of_measurement="fps"
    ),
}

LIBRARY_ENTITY_DESCRIPTION = SensorEntityDescription(
    key="library",
    icon="mdi:folder-multiple",
    native_unit_of_measurement="files"
)

NODE_ENTITY_DESCRIPTIONS = {
    SensorEntityDescription(
        key="node",
        icon="mdi:server-network-outline",
    ),
    SensorEntityDescription(
        key="nodefps",
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
        legacy_sensor_dict_value = SENSORS[description.key]
        sensors.append(TdarrSensor(entry, entry.data[legacy_sensor_dict_value["entry"]], config_entry.options, description))

    # Server Library Sensors
    for value in entry.data["libraries"]:
        sensors.append(TdarrSensor(entry, value, config_entry.options, LIBRARY_ENTITY_DESCRIPTION))

    # Server Node Sensors
    for _, value in entry.data["nodes"].items():
        for description in NODE_ENTITY_DESCRIPTIONS:
            sensors.append(TdarrSensor(entry, value, config_entry.options, description))

    async_add_entities(sensors, True)


class TdarrSensor(
    TdarrEntity,
    SensorEntity,
):
    def __init__(self, coordinator, sensor, options, entity_description: SensorEntityDescription):
        self.sensor = sensor
        self.tdarroptions = options
        self.entity_description = entity_description
        self._attr = {}
        self.coordinator = coordinator
        if self.entity_description.key == "server":
            self._device_id = "tdarr_server"
        elif self.entity_description.key == "node":
            if "nodeName" in self.sensor:
                self._device_id = "tdarr_node_" + self.sensor.get("nodeName", "")
            else:
                self._device_id = "tdarr_node_" + self.sensor.get("_id", "")
        elif self.entity_description.key == "nodefps":
            if "nodeName" in self.sensor:
                self._device_id = "tdarr_node_" + self.sensor.get("nodeName","") + "_fps"
            else:
                self._device_id = "tdarr_node_" + self.sensor.get("_id", "") + "_fps"
        elif self.entity_description.key == "library":
            self._device_id = "tdarr_library_" + self.sensor["name"]
        else:
            self._device_id = "tdarr_" + self.entity_description.key
        # Required for HA 2022.7
        self.coordinator_context = object()

    @property 
    def native_value(self):
        if self.entity_description.key == "server":
            return self.coordinator.data.get("server", {}).get("status")
        elif self.entity_description.key == "node":
            return "Online"
        elif self.entity_description.key == "nodefps":
            fps = 0
            for key1, value in self.coordinator.data.get("nodes", {}).get(self.sensor["_id"], {}).get("workers", {}).items():
                fps += value.get("fps", 0)
            return fps
        elif self.entity_description.key == "stats_spacesaved":
            return round(self.coordinator.data.get("stats",{}).get("sizeDiff", 0), 2)
        elif self.entity_description.key == "stats_transcodefilesremaining":
            return self.coordinator.data.get("stats",{}).get("table1Count", 0)
        elif self.entity_description.key == "stats_transcodedcount":
            return self.coordinator.data.get("stats",{}).get("table2Count", 0)
        elif self.entity_description.key == "stats_stagedcount":
            return self.coordinator.data.get("staged",{}).get("totalCount", 0)
        elif self.entity_description.key == "stats_healthcount":
            return self.coordinator.data.get("stats",{}).get("table4Count", 0)
        elif self.entity_description.key == "stats_transcodeerrorcount":
            return self.coordinator.data.get("stats",{}).get("table3Count", 0)
        elif self.entity_description.key == "stats_healtherrorcount":
            return self.coordinator.data.get("stats",{}).get("table6Count", 0)
        elif self.entity_description.key == "library":
            libraries = self.coordinator.data.get("libraries",{})
            for library in libraries:
                if library["name"] == self.sensor["name"]:
                    _LOGGER.debug(library)
                    return library["totalFiles"]

        elif self.entity_description.key == "stats_totalfps":
            fps = 0
            for _, node_values in self.coordinator.data["nodes"].items():
                for _, worker_values in node_values.get("workers", {}).items():
                    fps += worker_values.get("fps", 0)
            return fps

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "server":
            return self.coordinator.data.get("server", {})
        elif self.entity_description.key == "node":
            return self.coordinator.data.get("nodes",{}).get(self.sensor["_id"], {})
        elif self.entity_description.key == "stats_spacesaved":
            return self.coordinator.data.get("stats", {})
        elif self.entity_description.key == "library":
            libraries = self.coordinator.data.get("libraries",{})
            for library in libraries:
                if library["name"] == self.sensor["name"]:
                    data = {}
                    data["Total Files"] = library["totalFiles"]
                    data["Number of Transcodes"] = library["totalTranscodeCount"]
                    data["Space Saved (GB)"] = round(library["sizeDiff"], 0)
                    data["Number of Health Checks"] = library["totalHealthCheckCount"]
                    codecs = {}
                    for codec in library.get("video", {}).get("codecs", {}):
                        codecs[codec["name"]] = codec["value"]
                    data["Codecs"] = codecs
                    containers = {}
                    for container in library.get("video", {}).get("containers", {}):
                        containers[container["name"]] = container["value"]
                    data["Containers"] = containers
                    qualities = {}
                    for quality in library.get("video", {}).get("resolutions", {}):
                        qualities[quality["name"]] = quality["value"]
                    data["Resolutions"] = qualities
                    return data

    @property
    def device_id(self):
        return self.device_id

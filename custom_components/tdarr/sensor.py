import logging
import re

from homeassistant.components.sensor import (
    SensorEntity,
)

from . import TdarrEntity
from .const import DOMAIN, COORDINATOR, SENSORS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    sensors = []
    # Server Status Sensor
    #_LOGGER.debug(entry.data)
    for key, value in SENSORS.items():
        if value.get("type", "") == "single":
            sensors.append(TdarrSensor(entry, entry.data[value["entry"]], config_entry.options, key))
    # Server Library Sensors
    id = 0
    for value in entry.data["libraries"]:
        #value.insert(0, id)
        sensors.append(TdarrSensor(entry, value, config_entry.options, "library"))
        id += 1
    # Server Node Sensors
    fps_count = 0
    for key, value in entry.data["nodes"].items():
        sensors.append(TdarrSensor(entry, value, config_entry.options, "node"))
        sensors.append(TdarrSensor(entry, value, config_entry.options, "nodefps"))
    

    async_add_entities(sensors, True)


class TdarrSensor(
    TdarrEntity,
    SensorEntity,
):
    def __init__(self, coordinator, sensor, options, type):

        self.sensor = sensor
        self.tdarroptions = options
        self.type = type
        self._attr = {}
        self.coordinator = coordinator
        if self.type == "server":
            self._device_id = "tdarr_server"
        elif self.type == "node":
            if "nodeName" in self.sensor:
                self._device_id = "tdarr_node_" + self.sensor.get("nodeName", "")
            else:
                self._device_id = "tdarr_node_" + self.sensor.get("_id", "")
        elif self.type == "nodefps":
            if "nodeName" in self.sensor:
                self._device_id = "tdarr_node_" + self.sensor.get("nodeName","") + "_fps"
            else:
                self._device_id = "tdarr_node_" + self.sensor.get("_id", "") + "_fps"
        elif self.type == "library":
            self._device_id = "tdarr_library_" + self.sensor["name"]
        else:
            self._device_id = "tdarr_" + self.type
        # Required for HA 2022.7
        self.coordinator_context = object()

    @property 
    def native_value(self):
        if self.type == "server":
            return self.coordinator.data.get("server", {}).get("status")
        elif self.type == "node":
            return "Online"
        elif self.type == "nodefps":
            fps = 0
            for key1, value in self.coordinator.data.get("nodes", {}).get(self.sensor["_id"], {}).get("workers", {}).items():
                fps += value.get("fps", 0)
            return fps
        elif self.type == "stats_spacesaved":
            return round(self.coordinator.data.get("stats",{}).get("sizeDiff", 0), 2)
        elif self.type == "stats_transcodefilesremaining":
            return self.coordinator.data.get("stats",{}).get("table1Count", 0)
        elif self.type == "stats_transcodedcount":
            return self.coordinator.data.get("stats",{}).get("table2Count", 0)
        elif self.type == "stats_stagedcount":
            return self.coordinator.data.get("staged",{}).get("totalCount", 0)
        elif self.type == "stats_healthcount":
            return self.coordinator.data.get("stats",{}).get("table4Count", 0)
        elif self.type == "stats_transcodeerrorcount":
            return self.coordinator.data.get("stats",{}).get("table3Count", 0)
        elif self.type == "stats_healtherrorcount":
            return self.coordinator.data.get("stats",{}).get("table6Count", 0)
        elif self.type == "library":
            libraries = self.coordinator.data.get("libraries",{})
            for library in libraries:
                if library["name"] == self.sensor["name"]:
                    _LOGGER.debug(library)
                    return library["totalFiles"]

        elif self.type == "stats_totalfps":
            fps = 0
            for key1, value1 in self.coordinator.data["nodes"].items():
                for key2, value2 in value1.get("workers", {}).items():
                    fps += value2.get("fps", 0)
            return fps

    @property
    def extra_state_attributes(self):
        if self.type == "server":
            return self.coordinator.data.get("server", {})
        elif self.type == "node":
            return self.coordinator.data.get("nodes",{}).get(self.sensor["_id"], {})
        elif self.type == "stats_spacesaved":
            return self.coordinator.data.get("stats", {})
        elif self.type == "library":
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
    def name(self):
        if self.type == "server":
            return "tdarr_server"
        elif self.type == "node":
            if "nodeName" in self.sensor:
                return "tdarr_node_" + self.sensor.get("nodeName", "Unknown")
            else:
                return "tdarr_node_" + self.sensor.get("_id", "Unknown")
        elif self.type == "nodefps":
            if "nodeName" in self.sensor:
                return "tdarr_node_" + self.sensor.get("nodeName", "Unknown") + "_fps"
            else:
                return "tdarr_node_" + self.sensor.get("_id", "Unknown") + "_fps"
        elif self.type == "library":
            return "tdarr_library_" + self.sensor["name"]
        else:
            return "tdarr_" + self.type


    @property
    def device_id(self):
        return self.device_id

    @property
    def native_unit_of_measurement(self):
        return SENSORS.get(self.type, {}).get("unit_of_measurement", None)

    @property
    def device_class(self):
        return SENSORS.get(self.type, {}).get("device_class", None)

    @property
    def icon(self):
        return SENSORS.get(self.type, {}).get("icon", None)
    
    @property
    def state_class(self):
        return None
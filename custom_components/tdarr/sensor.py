from dataclasses import replace
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass
)

from . import (
    TdarrEntity,
    TdarrServerEntity,
    TdarrNodeEntity,
)
from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)

SERVER_ENTITY_DESCRIPTIONS = {
    SensorEntityDescription(
        key="server",
        translation_key="server",
        icon="mdi:server"
    ),
    SensorEntityDescription(
        key="stats_spacesaved",
        translation_key="stats_spacesaved",
        icon="mdi:harddisk",
        native_unit_of_measurement="GB",
        device_class=SensorDeviceClass.DATA_SIZE
    ),
    SensorEntityDescription(
        key="stats_transcodefilesremaining",
        translation_key="stats_transcodefilesremaining",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_transcodedcount",
        translation_key="stats_transcodedcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_stagedcount",
        translation_key="stats_stagedcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_healthcount",
        translation_key="stats_healthcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_transcodeerrorcount",
        translation_key="stats_transcodeerrorcount",
        icon="mdi:file-multiple",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_healtherrorcount",
        translation_key="stats_healtherrorcount",
        icon="mdi:medication-outline",
        native_unit_of_measurement="files"
    ),
    SensorEntityDescription(
        key="stats_totalfps",
        translation_key="stats_totalfps",
        icon="mdi:video",
        native_unit_of_measurement="fps"
    ),
}

LIBRARY_ENTITY_DESCRIPTION = SensorEntityDescription(
    key="library",
    translation_key="library",
    icon="mdi:folder-multiple",
    native_unit_of_measurement="files"
)

NODE_ENTITY_DESCRIPTIONS = {
    SensorEntityDescription(
        key="node",
        translation_key="node",
        icon="mdi:server-network-outline",
    ),
    SensorEntityDescription(
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
        sensors.append(TdarrLibrarySensor(entry, library_id, data, config_entry.options, description))

    # Server Node Sensors
    for node_id, data in entry.data["nodes"].items():
        for description in NODE_ENTITY_DESCRIPTIONS:
            description = replace(
                description,
                translation_placeholders={
                    "node_name": data["nodeName"]
                }
            )
            sensors.append(TdarrNodeSensor(entry, node_id, config_entry.options, description))

    async_add_entities(sensors, True)


class TdarrServerSensor(TdarrServerEntity, SensorEntity):
    
    _attr_has_entity_name = True # Required for reading translation_key from EntityDescription

    def __init__(self, coordinator, options, entity_description: SensorEntityDescription):
        _LOGGER.info("Creating server level sensor %s", entity_description.key)
        super().__init__(coordinator, entity_description)
        self._attr = {}
        # Required for HA 2022.7
        self.coordinator_context = object()

    @property 
    def native_value(self):
        if self.entity_description.key == "server":
            return self.coordinator.data.get("server", {}).get("status")
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
        elif self.entity_description.key == "stats_spacesaved":
            return self.coordinator.data.get("stats", {})


class TdarrLibrarySensor(TdarrEntity, SensorEntity):
    
    _attr_has_entity_name = True # Required for reading translation_key from EntityDescription

    def __init__(self, coordinator, library_id, sensor, options, entity_description: SensorEntityDescription):
        self.library_id = library_id
        self.sensor = sensor
        self.tdarroptions = options
        self.entity_description = entity_description
        self._attr = {}
        self.coordinator = coordinator
        if self.entity_description.key == "library":
            self._device_id = "tdarr_library_" + self.sensor["name"]
        else:
            raise NotImplementedError(f"Unrecognised sensor type {self.entity_description.key}")
        # Required for HA 2022.7
        self.coordinator_context = object()
    
    @property
    def library_data(self):
        return self.coordinator.data.get("libraries",{}).get(self.library_id)

    @property 
    def native_value(self):
        if self.entity_description.key == "library":
            return self.library_data.get("totalFiles")

    @property
    def extra_state_attributes(self):
        library = self.library_data
        if library:
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
        

class TdarrNodeSensor(TdarrNodeEntity, SensorEntity):
    
    _attr_has_entity_name = True # Required for reading translation_key from EntityDescription

    def __init__(self, coordinator, node_id, options, entity_description: SensorEntityDescription):
        _LOGGER.info("Creating node %s level sensor %s", node_id, entity_description.key)
        super().__init__(coordinator, node_id, entity_description)
        self._attr = {}
        # Required for HA 2022.7
        self.coordinator_context = object()

    @property 
    def native_value(self):
        if self.entity_description.key == "node":
            return "Online"
        elif self.entity_description.key == "nodefps":
            fps = 0
            for _, worker_values in self.node_data.get("workers", {}).items():
                fps += worker_values.get("fps", 0)
            return fps

    @property
    def extra_state_attributes(self):
        return self.node_data
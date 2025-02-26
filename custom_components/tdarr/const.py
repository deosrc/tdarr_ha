DOMAIN = "tdarr"
SERVERIP = "serverip"
MANUFACTURER = "Tdarr"
SERVERPORT = "serverport"
UPDATE_INTERVAL = "update_interval"
UPDATE_INTERVAL_DEFAULT = 60
COORDINATOR = "coordinator"
APIKEY = "apikey"

SENSORS = {
    "server": {"entry": "server"},
    "stats_spacesaved": {"entry": "stats"},
    "stats_transcodefilesremaining": {"entry": "stats"},
    "stats_transcodedcount": {"entry": "stats"},
    "stats_stagedcount": {"entry": "staged"},
    "stats_healthcount": {"entry": "stats"},
    "stats_transcodeerrorcount": {"entry": "stats"},
    "stats_healtherrorcount": {"entry": "stats"},
    "stats_totalfps": {"entry": "nodes"},
}

SWITCHES = {
    "pauseAll": {"icon": "mdi:pause-circle", "name": "pauseAll", "data": "globalsettings"},
    "ignoreSchedules": {"icon": "mdi:calendar-remove", "name": "ignoreSchedules", "data": "globalsettings"},
}
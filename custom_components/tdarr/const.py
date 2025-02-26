DOMAIN = "tdarr"
SERVERIP = "serverip"
MANUFACTURER = "Tdarr"
SERVERPORT = "serverport"
UPDATE_INTERVAL = "update_interval"
UPDATE_INTERVAL_DEFAULT = 60
COORDINATOR = "coordinator"
APIKEY = "apikey"

SENSORS = {
    "server": {"type": "single", "entry": "server"},
    "stats_spacesaved": {"entry": "stats"},
    "stats_transcodefilesremaining": {"type": "single", "entry": "stats"},
    "stats_transcodedcount": {"type": "single", "entry": "stats"},
    "stats_stagedcount": {"type": "single", "entry": "staged"},
    "stats_healthcount": {"type": "single", "entry": "stats"},
    "stats_transcodeerrorcount": {"type": "single", "entry": "stats"},
    "stats_healtherrorcount": {"type": "single", "entry": "stats"},
    "node": {},
    "nodefps": {},
    "stats_totalfps": {"type": "single", "entry": "nodes"},
    "library": {},
}

SWITCHES = {
    "pauseAll": {"icon": "mdi:pause-circle", "name": "pauseAll", "data": "globalsettings"},
    "ignoreSchedules": {"icon": "mdi:calendar-remove", "name": "ignoreSchedules", "data": "globalsettings"},
}
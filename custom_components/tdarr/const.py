DOMAIN = "tdarr"
SERVERIP = "serverip"
MANUFACTURER = "Tdarr"
SERVERPORT = "serverport"
UPDATE_INTERVAL = "update_interval"
UPDATE_INTERVAL_DEFAULT = 60
COORDINATOR = "coordinator"
APIKEY = "apikey"

WORKER_TYPE_HEALTHCHECK="healthcheck"
WORKER_TYPE_TRANSCODE="transcode"
WORKER_TYPES=[
    f'{WORKER_TYPE_HEALTHCHECK}cpu',
    f'{WORKER_TYPE_HEALTHCHECK}gpu',
    f'{WORKER_TYPE_TRANSCODE}cpu',
    f'{WORKER_TYPE_TRANSCODE}gpu'
]
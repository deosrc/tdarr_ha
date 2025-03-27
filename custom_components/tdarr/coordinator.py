"""The Tdarr integration coordinator components."""
import asyncio
import logging
from datetime import timedelta

import async_timeout
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
)

from .api import TdarrApiClient

_LOGGER = logging.getLogger(__name__)


class TdarrDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """DataUpdateCoordinator to handle fetching new data about the Tdarr Controller."""

    def __init__(self, hass, serverip, serverport, update_interval, api_key):
        """Initialize the coordinator and set up the Controller object."""
        self._hass = hass
        self.serverip = serverip

        self._session = async_create_clientsession(
            hass,
            base_url=f"http://{serverip}:{serverport}/api/v2/",
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key
            })
        self.tdarr = TdarrApiClient(f"{serverip}:{serverport}", self._session)
        self._available = True

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from Tdarr Server."""
        try:
            async with async_timeout.timeout(30):
                async with asyncio.TaskGroup() as tg:
                    status = tg.create_task(self.tdarr.get_status())
                    nodes = tg.create_task(self.tdarr.get_nodes())
                    stats = tg.create_task(self.tdarr.get_stats())
                    staged = tg.create_task(self.tdarr.get_staged())
                    libraries = tg.create_task(self.tdarr.get_libraries())
                    global_settings = tg.create_task(self.tdarr.get_global_settings())

                data = {
                    "server": status.result(),
                    "nodes": nodes.result(),
                    "stats": stats.result(),
                    "staged": staged.result(),
                    "libraries": libraries.result(),
                    "globalsettings": global_settings.result(),
                }

                #_LOGGER.debug(self.data)
                if self.data is not None:
                    #_LOGGER.debug(self.data)
                    oldnodes = len(self.data["nodes"])
                    #_LOGGER.debug(len(self.data["nodes"]))
                else:
                    oldnodes = len(data["nodes"])
                #_LOGGER.debug(len(self.data["nodes"])
                if oldnodes != len(data["nodes"]):
                    _LOGGER.debug("Node Change Detected config reload required")
                    # Reload integration to pick up new/changed nodes
                    current_entries = self._hass.config_entries.async_entries(DOMAIN)
                
                    if len(current_entries) > 0:
                        for entry in current_entries:
                            _LOGGER.debug("SHOWING ENTRY")
                            self._hass.config_entries.async_schedule_reload(entry.entry_id)

                return data
            
        except Exception as ex:
            self._available = False  # Mark as unavailable
            _LOGGER.warning(str(ex))
            _LOGGER.warning("Error communicating with Tdarr for %s", self.serverip)
            raise UpdateFailed(
                f"Error communicating with Tdarr for {self.serverip}"
            ) from ex

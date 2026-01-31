"""Config flow for Tdarr integration."""
import logging

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
    CONN_CLASS_CLOUD_POLL,
)
from homeassistant.core import (
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from requests.exceptions import ConnectionError

from .const import (
    DOMAIN,
    SERVERIP,
    SERVERPORT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_DEFAULT,
    APIKEY
)
from .api import TdarrApiClient

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(SERVERIP): str,
        vol.Required(SERVERPORT, default="8265"): str,
        vol.Optional(APIKEY, default=""): str
    }
)

async def validate_input(hass: HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    api_client: TdarrApiClient = TdarrApiClient.from_config(hass, data)

    result = await api_client.async_get_global_settings()
    if result.get("status", "") == "ERROR":
        if "Invalid API key" in result["message"]:
            raise InvalidAPIKEY
        if "No auth token provided" in result["message"]:
            raise AuthRequired
        raise ConnectionError
    if not result:
        _LOGGER.error("Failed to connect to Tdarr Server")
        raise ConnectionError

    # Return info that you want to store in the config entry.
    return {"title": f"Tdarr Server ({data[SERVERIP]})"}

class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tdarr Controller."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except InvalidAPIKEY:
                errors["base"] = "invalid_apikey"
            except AuthRequired:
                errors["base"] = "auth_required"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception(ex)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

class OptionsFlowHandler(OptionsFlow):

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            if SERVERIP in self.config_entry.data:
                user_input[SERVERIP] = self.config_entry.data[SERVERIP]
            if SERVERPORT in self.config_entry.data:
                user_input[SERVERPORT] = self.config_entry.data[SERVERPORT]
            if APIKEY in user_input:
                user_input[APIKEY] = user_input[APIKEY].strip()
            _LOGGER.debug(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
            )
            return self.async_create_entry(title="", data={})
        options = {
            vol.Optional(
                UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    UPDATE_INTERVAL, UPDATE_INTERVAL_DEFAULT
                ),
            ): int,
            vol.Optional(
                APIKEY,
                default=self.config_entry.data.get(APIKEY, "")
            ): str,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))

class InvalidAPIKEY(HomeAssistantError):
    """Error to indicate the wrong API key was entered"""

class AuthRequired(HomeAssistantError):
    """Error to indicate Auth is required"""




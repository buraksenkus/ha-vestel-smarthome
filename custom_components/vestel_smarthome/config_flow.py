"""Config flow for the Vestel Smart Home integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VestelApi, VestelAuthError, VestelError
from .const import (
    CONF_HOME_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


class VestelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._email: str = ""
        self._password: str = ""
        self._refresh_token: str | None = None
        self._homes: list[dict[str, Any]] = []

    async def _async_authenticate(self) -> str | None:
        """Log in and load the homes. Return an error key on failure."""
        api = VestelApi(async_get_clientsession(self.hass), self._email, self._password)
        try:
            await api.async_login()
            self._homes = await api.async_get_homes()
        except VestelAuthError:
            return "invalid_auth"
        except VestelError as err:
            _LOGGER.debug("Connection to the Vestel cloud failed: %s", err)
            return "cannot_connect"
        self._refresh_token = api.refresh_token
        if not self._homes:
            return "no_homes"
        return None

    def _entry_data(self, home_id: str) -> dict[str, Any]:
        return {
            CONF_EMAIL: self._email,
            CONF_PASSWORD: self._password,
            CONF_REFRESH_TOKEN: self._refresh_token,
            CONF_HOME_ID: home_id,
        }

    def _home_name(self, home_id: str) -> str:
        for home in self._homes:
            if home.get("homeId") == home_id:
                return home.get("homeName") or home_id
        return home_id

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the account credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip()
            self._password = user_input[CONF_PASSWORD]
            error = await self._async_authenticate()
            if error:
                errors["base"] = error
            elif len(self._homes) == 1:
                return await self._async_create(self._homes[0]["homeId"])
            else:
                return await self.async_step_home()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_home(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick which home to add."""
        if user_input is not None:
            return await self._async_create(user_input[CONF_HOME_ID])

        choices = {
            home["homeId"]: home.get("homeName") or home["homeId"]
            for home in self._homes
            if home.get("homeId")
        }
        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema({vol.Required(CONF_HOME_ID): vol.In(choices)}),
        )

    async def _async_create(self, home_id: str) -> ConfigFlowResult:
        await self.async_set_unique_id(home_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=self._home_name(home_id), data=self._entry_data(home_id)
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle expired credentials."""
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the password again."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            error = await self._async_authenticate()
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        **entry.data,
                        CONF_PASSWORD: self._password,
                        CONF_REFRESH_TOKEN: self._refresh_token,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_EMAIL: self._email},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return VestelOptionsFlow()


class VestelOptionsFlow(OptionsFlow):
    """Handle the integration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the polling interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_SECONDS, int(DEFAULT_SCAN_INTERVAL.total_seconds())
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL_SECONDS, default=current
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            max=MAX_SCAN_INTERVAL_SECONDS,
                        ),
                    )
                }
            ),
        )

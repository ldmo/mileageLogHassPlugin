"""Config flow for Traxmiles."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .client import TraxmilesAuthError, TraxmilesClient, TraxmilesError
from .const import (
    CONF_AUTO_SUBMIT_ENABLED,
    CONF_EMAIL,
    CONF_UPDATE_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    MAX_UPDATE_INTERVAL_SECONDS,
    MIN_UPDATE_INTERVAL_SECONDS,
    DEFAULT_AUTO_SUBMIT_ENABLED,
)

_LOGGER = logging.getLogger(__name__)


class TraxmilesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Traxmiles."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            password = user_input[CONF_PASSWORD]
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()

            try:
                session = async_create_clientsession(self.hass)
                client = TraxmilesClient(session=session, email=email, password=password)
                await client.validate_credentials()
                await session.close()
            except TraxmilesAuthError:
                errors["base"] = "invalid_auth"
            except TraxmilesError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during auth probe")
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title=email,
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> "TraxmilesOptionsFlow":
        return TraxmilesOptionsFlow(entry)


class TraxmilesOptionsFlow(config_entries.OptionsFlow):
    """Handle Traxmiles options."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=dict(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL_SECONDS,
                        default=self._entry.options.get(
                            CONF_UPDATE_INTERVAL_SECONDS, DEFAULT_UPDATE_INTERVAL_SECONDS
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_UPDATE_INTERVAL_SECONDS,
                            max=MAX_UPDATE_INTERVAL_SECONDS,
                        ),
                    ),
                    vol.Optional(
                        CONF_AUTO_SUBMIT_ENABLED,
                        default=self._entry.options.get(
                            CONF_AUTO_SUBMIT_ENABLED,
                            DEFAULT_AUTO_SUBMIT_ENABLED,
                        ),
                    ): bool,
                }
            ),
        )

"""Traxmiles integration setup."""

from __future__ import annotations

from aiohttp import CookieJar
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.typing import ConfigType

from .client import TraxmilesAuthError, TraxmilesClient, TraxmilesError, TraxmilesValidationError
from .const import (
    ATTR_CLOSING_ODOMETER,
    ATTR_ENTRY_ID,
    ATTR_SOURCE,
    CONF_AUTO_SUBMIT_ENABLED,
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
    SERVICE_LOCK_AND_SUBMIT,
    SOURCE_AUTOMATION,
    SOURCE_MANUAL,
)
from .coordinator import TraxmilesDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration domain."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Traxmiles from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_create_clientsession(
        hass, cookie_jar=CookieJar(unsafe=True), auto_cleanup=False
    )
    client = TraxmilesClient(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = TraxmilesDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "session": session,
        "entry": entry,
        "closing_odometer": 0.0,
        "auto_submit_allowed": bool(
            entry.options.get(CONF_AUTO_SUBMIT_ENABLED, False)
        ),
    }

    if not hass.services.has_service(DOMAIN, SERVICE_LOCK_AND_SUBMIT):
        _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        session = entry_data.get("session")
        if session:
            await session.close()
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_LOCK_AND_SUBMIT):
            hass.services.async_remove(DOMAIN, SERVICE_LOCK_AND_SUBMIT)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    service_schema = vol.Schema(
        {
            vol.Required(ATTR_CLOSING_ODOMETER): vol.Coerce(float),
            vol.Optional(ATTR_SOURCE, default=SOURCE_AUTOMATION): vol.In(
                [SOURCE_MANUAL, SOURCE_AUTOMATION]
            ),
            vol.Optional(ATTR_ENTRY_ID): str,
        }
    )

    async def _handle_lock_and_submit(call) -> None:
        entry_id: str | None = call.data.get(ATTR_ENTRY_ID)
        source: str = call.data[ATTR_SOURCE]
        closing_odometer: float = call.data[ATTR_CLOSING_ODOMETER]

        if entry_id is None:
            entries = list(hass.data[DOMAIN].keys())
            if len(entries) != 1:
                raise HomeAssistantError(
                    "Multiple Traxmiles entries configured; provide entry_id"
                )
            entry_id = entries[0]

        entry_runtime = hass.data[DOMAIN].get(entry_id)
        if not entry_runtime:
            raise HomeAssistantError(f"Traxmiles entry '{entry_id}' not found")

        auto_submit_allowed = bool(entry_runtime.get("auto_submit_allowed", False))
        if source == SOURCE_AUTOMATION and not auto_submit_allowed:
            raise HomeAssistantError(
                "auto-submit is not allowed; enable the switch first"
            )

        if closing_odometer <= 0:
            raise HomeAssistantError("closing_odometer must be a positive number")

        client: TraxmilesClient = entry_runtime["client"]
        coordinator: TraxmilesDataUpdateCoordinator = entry_runtime["coordinator"]

        try:
            result = await client.lock_and_submit(closing_odometer=closing_odometer)
        except (TraxmilesValidationError, TraxmilesAuthError, TraxmilesError) as err:
            raise HomeAssistantError(str(err)) from err

        await coordinator.async_request_refresh()
        snapshot = result["snapshot"]
        hass.bus.async_fire(
            "traxmiles_locked",
            {
                "entry_id": entry_id,
                "record_id": result["record_id"],
                "closing_odometer": closing_odometer,
                "month": snapshot.open_record_month,
            },
        )

    hass.services.async_register(
        DOMAIN, SERVICE_LOCK_AND_SUBMIT, _handle_lock_and_submit, schema=service_schema
    )

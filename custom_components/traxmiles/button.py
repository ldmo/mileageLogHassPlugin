"""Button platform for Traxmiles."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_CLOSING_ODOMETER,
    ATTR_ENTRY_ID,
    ATTR_SOURCE,
    CONF_EMAIL,
    DOMAIN,
    SERVICE_LOCK_AND_SUBMIT,
    SOURCE_MANUAL,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lock-and-submit button."""
    async_add_entities([TraxmilesLockAndSubmitButton(hass, entry)])


class TraxmilesLockAndSubmitButton(ButtonEntity):
    """Manual lock and submit trigger."""

    _attr_name = "Lock and submit"
    _attr_translation_key = "lock_and_submit"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_lock_and_submit"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Traxmiles {entry.data[CONF_EMAIL]}",
            "manufacturer": "Traxmiles",
            "model": "Web Dashboard",
        }

    async def async_press(self) -> None:
        runtime = self.hass.data[DOMAIN][self._entry.entry_id]
        closing_odometer = runtime.get("closing_odometer")
        if closing_odometer is None or float(closing_odometer) <= 0:
            raise HomeAssistantError(
                "Set a valid closing odometer value before submitting"
            )

        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_LOCK_AND_SUBMIT,
            {
                ATTR_ENTRY_ID: self._entry.entry_id,
                ATTR_CLOSING_ODOMETER: float(closing_odometer),
                ATTR_SOURCE: SOURCE_MANUAL,
            },
            blocking=True,
        )

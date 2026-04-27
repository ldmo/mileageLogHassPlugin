"""Number platform for Traxmiles."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_EMAIL, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up closing odometer number entity."""
    async_add_entities([TraxmilesClosingOdometerNumber(hass, entry)])


class TraxmilesClosingOdometerNumber(NumberEntity, RestoreEntity):
    """Writable closing odometer value."""

    _attr_name = "Closing odometer"
    _attr_translation_key = "closing_odometer"
    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 9_999_999
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_mode = NumberMode.BOX

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_closing_odometer"
        self._attr_native_value = 0
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Traxmiles {entry.data[CONF_EMAIL]}",
            "manufacturer": "Traxmiles",
            "model": "Web Dashboard",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                self._attr_native_value = 0
        self.hass.data[DOMAIN][self._entry.entry_id]["closing_odometer"] = float(
            self._attr_native_value
        )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = float(value)
        self.hass.data[DOMAIN][self._entry.entry_id]["closing_odometer"] = float(value)
        self.async_write_ha_state()

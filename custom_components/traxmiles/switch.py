"""Switch platform for Traxmiles."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_EMAIL, DEFAULT_AUTO_SUBMIT_ENABLED, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up auto-submit switch."""
    async_add_entities([TraxmilesAutoSubmitSwitch(hass, entry)])


class TraxmilesAutoSubmitSwitch(SwitchEntity, RestoreEntity):
    """Gate automation-driven submit calls."""

    _attr_name = "Auto submit allowed"
    _attr_translation_key = "auto_submit_allowed"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._is_on = DEFAULT_AUTO_SUBMIT_ENABLED
        self._attr_unique_id = f"{entry.entry_id}_auto_submit_allowed"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Traxmiles {entry.data[CONF_EMAIL]}",
            "manufacturer": "Traxmiles",
            "model": "Web Dashboard",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._is_on = last_state.state == "on"
        self.hass.data[DOMAIN][self._entry.entry_id]["auto_submit_allowed"] = self._is_on

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        self._is_on = True
        self.hass.data[DOMAIN][self._entry.entry_id]["auto_submit_allowed"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        self.hass.data[DOMAIN][self._entry.entry_id]["auto_submit_allowed"] = False
        self.async_write_ha_state()

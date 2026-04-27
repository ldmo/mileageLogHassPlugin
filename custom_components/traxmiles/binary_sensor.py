"""Binary sensor platform for Traxmiles."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_EMAIL, DOMAIN
from .coordinator import TraxmilesDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Traxmiles binary sensors from a config entry."""
    coordinator: TraxmilesDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    async_add_entities([TraxmilesRecordLockedBinarySensor(coordinator, entry)])


class TraxmilesRecordLockedBinarySensor(
    CoordinatorEntity[TraxmilesDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Binary sensor for lock state."""

    _attr_name = "Record locked"
    _attr_translation_key = "record_locked"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TraxmilesDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_record_locked"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Traxmiles {entry.data[CONF_EMAIL]}",
            "manufacturer": "Traxmiles",
            "model": "Web Dashboard",
        }

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_locked

"""Sensor platform for Traxmiles."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_EMAIL, DOMAIN
from .coordinator import TraxmilesDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class TraxmilesSensorDescription(SensorEntityDescription):
    """Description for a Traxmiles sensor."""

    value_key: str


SENSOR_DESCRIPTIONS: tuple[TraxmilesSensorDescription, ...] = (
    TraxmilesSensorDescription(
        key="business_miles_this_month",
        translation_key="business_miles_this_month",
        name="Business miles this month",
        native_unit_of_measurement=UnitOfLength.MILES,
        value_key="business_miles_this_month",
    ),
    TraxmilesSensorDescription(
        key="total_business_miles_tax_year",
        translation_key="total_business_miles_tax_year",
        name="Business miles tax year",
        native_unit_of_measurement=UnitOfLength.MILES,
        value_key="total_business_miles_tax_year",
    ),
    TraxmilesSensorDescription(
        key="opening_odometer",
        translation_key="opening_odometer",
        name="Opening odometer",
        native_unit_of_measurement=UnitOfLength.MILES,
        value_key="opening_odometer",
    ),
    TraxmilesSensorDescription(
        key="vehicle_registration",
        translation_key="vehicle_registration",
        name="Current vehicle",
        value_key="vehicle_registration",
    ),
    TraxmilesSensorDescription(
        key="open_record_month",
        translation_key="open_record_month",
        name="Open record month",
        value_key="open_record_month",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Traxmiles sensors from a config entry."""
    coordinator: TraxmilesDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    async_add_entities(
        TraxmilesSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class TraxmilesSensor(
    CoordinatorEntity[TraxmilesDataUpdateCoordinator],
    SensorEntity,
):
    """Representation of a Traxmiles sensor."""

    entity_description: TraxmilesSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TraxmilesDataUpdateCoordinator,
        entry: ConfigEntry,
        description: TraxmilesSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Traxmiles {entry.data[CONF_EMAIL]}",
            "manufacturer": "Traxmiles",
            "model": "Web Dashboard",
        }

    @property
    def native_value(self) -> str | float | None:
        data = self.coordinator.data
        return getattr(data, self.entity_description.value_key)

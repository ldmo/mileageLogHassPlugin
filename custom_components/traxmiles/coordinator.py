"""Data coordinator for Traxmiles."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import HomeSnapshot, TraxmilesAuthError, TraxmilesClient, TraxmilesError
from .const import (
    CONF_UPDATE_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    MIN_UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class TraxmilesDataUpdateCoordinator(DataUpdateCoordinator[HomeSnapshot]):
    """Coordinator fetching latest /home snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TraxmilesClient,
    ) -> None:
        update_seconds = int(
            entry.options.get(CONF_UPDATE_INTERVAL_SECONDS, DEFAULT_UPDATE_INTERVAL_SECONDS)
        )
        interval = max(update_seconds, MIN_UPDATE_INTERVAL_SECONDS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> HomeSnapshot:
        try:
            return await self.client.fetch_home()
        except TraxmilesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TraxmilesError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected update error: {err}") from err

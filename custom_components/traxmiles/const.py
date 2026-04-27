"""Constants for the Traxmiles integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "traxmiles"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL_SECONDS = "update_interval_seconds"
CONF_AUTO_SUBMIT_ENABLED = "auto_submit_enabled"

DEFAULT_UPDATE_INTERVAL_SECONDS = 3600
MIN_UPDATE_INTERVAL_SECONDS = 3600
MAX_UPDATE_INTERVAL_SECONDS = 3600
DEFAULT_AUTO_SUBMIT_ENABLED = False

SERVICE_LOCK_AND_SUBMIT = "lock_and_submit"
ATTR_CLOSING_ODOMETER = "closing_odometer"
ATTR_SOURCE = "source"
ATTR_ENTRY_ID = "entry_id"
SOURCE_MANUAL = "manual"
SOURCE_AUTOMATION = "automation"

SESSION_STALE_SECONDS = 300
SCAN_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS)

BASE_URL = "https://traxmiles.co.uk"
LOGIN_URL = f"{BASE_URL}/login"
HOME_URL = f"{BASE_URL}/home"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)

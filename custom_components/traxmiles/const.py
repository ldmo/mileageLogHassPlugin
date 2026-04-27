"""Constants for the Traxmiles integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "traxmiles"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL_SECONDS = "update_interval_seconds"

DEFAULT_UPDATE_INTERVAL_SECONDS = 60
MIN_UPDATE_INTERVAL_SECONDS = 3600
MAX_UPDATE_INTERVAL_SECONDS = 3600

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

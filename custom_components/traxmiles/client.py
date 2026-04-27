"""Traxmiles HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import asyncio
import logging
import re
from urllib.parse import urlencode
from typing import Any

from aiohttp import ClientResponse, ClientSession
from bs4 import BeautifulSoup

from .const import HOME_URL, LOGIN_URL, SESSION_STALE_SECONDS, USER_AGENT

_LOGGER = logging.getLogger(__name__)

_OPEN_LOCKED_MONTH_RE = re.compile(
    r"(Open|Locked)\s+Record\s*[-–]\s*([A-Za-z]+\s+\d{4})", re.IGNORECASE
)
_CLAIMS_MONTH_RE = re.compile(r"Claims\s+For\s+([A-Za-z]+\s+\d{4})", re.IGNORECASE)
_THIS_MONTH_BUSINESS_MILES_RE = re.compile(
    r"This\s+Month[^\d]{0,80}Business\s+Mileage[^\d]{0,40}([\d.,]+)",
    re.IGNORECASE,
)
_THIS_MONTH_BUSINESS_MILES_FALLBACK_RE = re.compile(
    r"Business\s+Mileage\s+This\s+Month[^\d]{0,40}([\d.,]+)",
    re.IGNORECASE,
)
_THIS_MONTH_BUSINESS_MILES_ALT_RE = re.compile(
    r"Business\s+Miles?\s+This\s+Month[^\d]{0,40}([\d.,]+)",
    re.IGNORECASE,
)
_TAX_YEAR_BUSINESS_MILES_RE = re.compile(
    r"Total\s+Business\s+Mileage\s+This\s+Tax\s+Year[^\d]{0,40}([\d.,]+)",
    re.IGNORECASE,
)
_TAX_YEAR_BUSINESS_MILES_ALT_RE = re.compile(
    r"Business\s+Miles?\s+Tax\s+Year[^\d]{0,40}([\d.,]+)",
    re.IGNORECASE,
)
_TAX_YEAR_CUMULATIVE_BUSINESS_MILES_RE = re.compile(
    r"Cumulative\s+Business\s+Mileage[:\s]+([\d.,]+)",
    re.IGNORECASE,
)
_CAR_REG_RE = re.compile(r"Car:\s*([A-Z0-9]{1,8})", re.IGNORECASE)
_CURRENT_VEHICLE_RE = re.compile(
    r"Current\s+Vehicle[^\w]{0,20}([A-Z0-9]{1,8})",
    re.IGNORECASE,
)
_VEHICLE_REG_RE = re.compile(
    r"(?:Vehicle|Registration|Reg)[:\s]+([A-Z0-9]{1,8})",
    re.IGNORECASE,
)
_REGISTRATION_NUMBER_RE = re.compile(
    r"Registration\s+Number[:\s]+([A-Z0-9]{1,8})",
    re.IGNORECASE,
)
_OPENING_ODOMETER_RE = re.compile(
    r"Opening\s+odometer[:\s]+([\d.,]+)\s*mi",
    re.IGNORECASE,
)
_RECORD_ID_RE = re.compile(r"/log/(\d+)(?:[/?#]|$)", re.IGNORECASE)


class TraxmilesError(Exception):
    """Base Traxmiles client exception."""


class TraxmilesAuthError(TraxmilesError):
    """Raised when authentication fails."""


class TraxmilesValidationError(TraxmilesError):
    """Raised when Traxmiles rejects form validation."""


@dataclass(slots=True)
class HomeSnapshot:
    """Parsed `/home` payload."""

    csrf_token: str
    record_id: str | None
    open_record_month: str | None
    is_locked: bool
    business_miles_this_month: float | None
    total_business_miles_tax_year: float | None
    opening_odometer: float | None
    vehicle_registration: str | None
    raw_html: str
    fetched_at: datetime


def extract_csrf_token(html: str) -> str | None:
    """Extract a CSRF token from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    meta_tag = soup.find("meta", attrs={"name": "csrf-token"})
    if meta_tag and meta_tag.get("content"):
        return str(meta_tag["content"])

    token_input = soup.find("input", attrs={"name": "_token"})
    if token_input and token_input.get("value"):
        return str(token_input["value"])

    return None


def extract_edit_lock_url(html: str) -> str | None:
    """Extract the current edit/lock URL from /home HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a"):
        text = anchor.get_text(" ", strip=True)
        if re.match(r"^edit\s*/\s*lock\s+record$", text, re.IGNORECASE):
            href = anchor.get("href")
            return str(href) if href else None
    return None


def parse_record_id(edit_lock_url: str | None) -> str | None:
    """Extract record id from `/log/<id>` URL."""
    if not edit_lock_url:
        return None
    match = _RECORD_ID_RE.search(edit_lock_url)
    return match.group(1) if match else None


def parse_home_snapshot(html: str) -> HomeSnapshot:
    """Parse the authenticated `/home` page."""
    csrf_token = extract_csrf_token(html)
    if not csrf_token:
        raise TraxmilesError("CSRF token missing from /home HTML")

    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    record_state_match = _OPEN_LOCKED_MONTH_RE.search(text)
    if record_state_match:
        is_locked = record_state_match.group(1).lower() == "locked"
        open_record_month = record_state_match.group(2)
    else:
        is_locked = False
        fallback_month = _CLAIMS_MONTH_RE.search(text)
        open_record_month = fallback_month.group(1) if fallback_month else None

    edit_lock_url = extract_edit_lock_url(html)
    record_id = parse_record_id(edit_lock_url)

    business_miles_this_month = _extract_business_miles_this_month(text)

    tax_year_match = (
        _TAX_YEAR_BUSINESS_MILES_RE.search(text)
        or _TAX_YEAR_BUSINESS_MILES_ALT_RE.search(text)
        or _TAX_YEAR_CUMULATIVE_BUSINESS_MILES_RE.search(text)
    )
    total_business_miles_tax_year = _parse_number(
        tax_year_match.group(1) if tax_year_match else None
    )

    car_match = (
        _CAR_REG_RE.search(text)
        or _REGISTRATION_NUMBER_RE.search(text)
        or _CURRENT_VEHICLE_RE.search(text)
        or _VEHICLE_REG_RE.search(text)
    )
    vehicle_registration = car_match.group(1).upper() if car_match else None

    opening_odometer_match = _OPENING_ODOMETER_RE.search(text)
    opening_odometer = _parse_number(
        opening_odometer_match.group(1) if opening_odometer_match else None
    )

    if (
        business_miles_this_month is None
        or total_business_miles_tax_year is None
        or vehicle_registration is None
    ):
        _LOGGER.debug(
            "Partial /home parse: month_miles=%s tax_year_miles=%s vehicle=%s text_preview=%s",
            business_miles_this_month,
            total_business_miles_tax_year,
            vehicle_registration,
            text[:300],
        )

    return HomeSnapshot(
        csrf_token=csrf_token,
        record_id=record_id,
        open_record_month=open_record_month,
        is_locked=is_locked,
        business_miles_this_month=business_miles_this_month,
        total_business_miles_tax_year=total_business_miles_tax_year,
        opening_odometer=opening_odometer,
        vehicle_registration=vehicle_registration,
        raw_html=html,
        fetched_at=datetime.now(UTC),
    )


def _extract_business_miles_this_month(text: str) -> float | None:
    business_miles_match = (
        _THIS_MONTH_BUSINESS_MILES_RE.search(text)
        or _THIS_MONTH_BUSINESS_MILES_FALLBACK_RE.search(text)
        or _THIS_MONTH_BUSINESS_MILES_ALT_RE.search(text)
    )
    return _parse_number(business_miles_match.group(1) if business_miles_match else None)


def _parse_number(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


class TraxmilesClient:
    """Client for Traxmiles web endpoints."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._csrf_token: str | None = None
        self._last_validated: datetime | None = None
        self._request_lock = asyncio.Lock()

    async def login(self) -> None:
        """Perform the full §3.3 login flow from a clean cookie state.

        Always starts by clearing this session's cookie jar so the GET /login
        step actually returns the anonymous login page (with a fresh
        ``_token``) rather than a 302 to /home from a still-valid cached
        cookie. The Node reference does the equivalent by starting each
        ``loginSession()`` with an empty cookie object.
        """
        self._clear_session_cookies()
        self._csrf_token = None
        self._last_validated = None

        login_page = await self._request("GET", LOGIN_URL, allow_login_redirect_check=True)
        if login_page.status != 200:
            raise TraxmilesAuthError(
                f"GET /login returned HTTP {login_page.status} (expected 200 with login form)"
            )
        login_html = await login_page.text()
        csrf_token = extract_csrf_token(login_html)
        if not csrf_token:
            raise TraxmilesAuthError("Unable to extract CSRF token from /login page")

        payload = {
            "_token": csrf_token,
            "email": self._email,
            "password": self._password,
        }
        await self._request(
            "POST",
            LOGIN_URL,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://traxmiles.co.uk",
                "Referer": LOGIN_URL,
            },
            allow_login_redirect_check=True,
        )

        home_response = await self._request(
            "GET",
            HOME_URL,
            headers={"Referer": LOGIN_URL},
            allow_login_redirect_check=True,
        )
        if self._is_login_redirect(home_response):
            raise TraxmilesAuthError("Credentials rejected by Traxmiles")

        if home_response.status != 200:
            raise TraxmilesAuthError(
                f"Authenticated /home probe returned HTTP {home_response.status}"
            )

        home_html = await home_response.text()
        home_csrf = extract_csrf_token(home_html)
        if not home_csrf:
            raise TraxmilesAuthError("Authenticated /home response had no CSRF token")

        self._csrf_token = home_csrf
        self._last_validated = datetime.now(UTC)
        _LOGGER.debug("Traxmiles login flow completed; cached fresh CSRF token")

    def _clear_session_cookies(self) -> None:
        """Drop all cookies on this integration's dedicated session jar."""
        jar = self._session.cookie_jar
        try:
            jar.clear()
        except Exception:  # pragma: no cover - defensive
            _LOGGER.debug("Failed to clear Traxmiles cookie jar", exc_info=True)

    async def ensure_session(self) -> None:
        """Ensure a valid session exists."""
        now = datetime.now(UTC)
        if (
            self._last_validated is None
            or (now - self._last_validated).total_seconds() > SESSION_STALE_SECONDS
        ):
            await self.login()

    async def fetch_home(self) -> HomeSnapshot:
        """Fetch and parse /home after ensuring session."""
        async with self._request_lock:
            await self.ensure_session()

            home_response = await self._request("GET", HOME_URL, allow_login_redirect_check=True)
            if self._is_login_redirect(home_response):
                await self.login()
                home_response = await self._request(
                    "GET", HOME_URL, allow_login_redirect_check=True
                )
                if self._is_login_redirect(home_response):
                    raise TraxmilesAuthError("Session invalid after re-login attempt")

            home_html = await home_response.text()
            snapshot = parse_home_snapshot(home_html)

            # Some accounts render "business miles this month" only on /log/<id>.
            if snapshot.business_miles_this_month is None:
                edit_lock_url = extract_edit_lock_url(home_html)
                if edit_lock_url:
                    log_url = self._absolute_url(edit_lock_url)
                    try:
                        log_response = await self._request(
                            "GET",
                            log_url,
                            headers={"Referer": HOME_URL},
                            allow_login_redirect_check=True,
                        )
                        if not self._is_login_redirect(log_response):
                            log_html = await log_response.text()
                            log_text = re.sub(
                                r"\s+",
                                " ",
                                BeautifulSoup(log_html, "html.parser").get_text(" ", strip=True),
                            )
                            business_miles = _extract_business_miles_this_month(log_text)
                            if business_miles is not None:
                                snapshot.business_miles_this_month = business_miles
                    except TraxmilesError:
                        _LOGGER.debug(
                            "Unable to read business miles from /log page", exc_info=True
                        )

            self._csrf_token = snapshot.csrf_token
            self._last_validated = datetime.now(UTC)
            return snapshot

    async def lock_and_submit(self, *, closing_odometer: float) -> dict[str, str | HomeSnapshot]:
        """Lock and submit the current record.

        Always performs the full §3.3 login flow first. The plugin may have
        been dormant since the last hourly poll, the user may have signed in
        from a browser (Traxmiles only allows one active session per
        account, see §3.6), or the cached CSRF token may have rotated. A
        fresh login guarantees we have a valid ``traxmiles_session`` cookie
        and a current ``_token`` before issuing the destructive POST.
        """
        if closing_odometer <= 0:
            raise TraxmilesValidationError("Closing odometer must be a positive number")

        async with self._request_lock:
            _LOGGER.debug(
                "lock_and_submit: forcing full login flow before submit (closing_odometer=%s)",
                closing_odometer,
            )
            await self.login()
            return await self._lock_and_submit_with_retry(
                closing_odometer=closing_odometer,
                login_retry=True,
                csrf_retry=True,
            )

    async def _lock_and_submit_with_retry(
        self,
        *,
        closing_odometer: float,
        login_retry: bool,
        csrf_retry: bool,
    ) -> dict[str, str | HomeSnapshot]:
        home_response = await self._request("GET", HOME_URL, allow_login_redirect_check=True)
        if self._is_login_redirect(home_response):
            if not login_retry:
                raise TraxmilesAuthError("Redirected to /login before submit")
            await self.login()
            return await self._lock_and_submit_with_retry(
                closing_odometer=closing_odometer,
                login_retry=False,
                csrf_retry=csrf_retry,
            )

        home_html = await home_response.text()
        snapshot = parse_home_snapshot(home_html)
        self._csrf_token = snapshot.csrf_token
        self._last_validated = datetime.now(UTC)

        if not snapshot.record_id:
            raise TraxmilesError("Could not determine current record ID from /home")

        submit_url = f"https://traxmiles.co.uk/log/update/{snapshot.record_id}"
        referer = self._absolute_url(extract_edit_lock_url(home_html) or f"/log/{snapshot.record_id}")
        payload = urlencode(
            {
                "_method": "PATCH",
                "_token": snapshot.csrf_token,
                "closing_odometer": str(closing_odometer),
                "terms_and_conditions": "1",
            }
        )

        submit_response = await self._request(
            "POST",
            submit_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://traxmiles.co.uk",
                "Referer": referer,
            },
            allow_login_redirect_check=True,
        )
        submit_body = await submit_response.text()

        if submit_response.status == 419:
            if not csrf_retry:
                raise TraxmilesError("CSRF mismatch while submitting closing odometer")
            await self.login()
            return await self._lock_and_submit_with_retry(
                closing_odometer=closing_odometer,
                login_retry=login_retry,
                csrf_retry=False,
            )

        if submit_response.status == 401 or self._is_login_redirect(submit_response):
            if not login_retry:
                raise TraxmilesAuthError("Session expired while submitting closing odometer")
            await self.login()
            return await self._lock_and_submit_with_retry(
                closing_odometer=closing_odometer,
                login_retry=False,
                csrf_retry=csrf_retry,
            )

        if submit_response.status == 422:
            first_msg = self._parse_validation_message(submit_body)
            raise TraxmilesValidationError(first_msg or "Traxmiles rejected submitted odometer")

        body_preview = submit_body[:500].lower()
        if submit_response.status not in (200, 302) or any(
            token in body_preview for token in ("error", "invalid", "required")
        ):
            raise TraxmilesError(
                f"Submit failed (HTTP {submit_response.status}): {submit_body[:200].strip()}"
            )

        refreshed_home_response = await self._request(
            "GET", HOME_URL, allow_login_redirect_check=True
        )
        if self._is_login_redirect(refreshed_home_response):
            raise TraxmilesAuthError("Session expired immediately after submit")
        refreshed_home_html = await refreshed_home_response.text()
        refreshed_snapshot = parse_home_snapshot(refreshed_home_html)
        self._csrf_token = refreshed_snapshot.csrf_token
        self._last_validated = datetime.now(UTC)
        return {"record_id": snapshot.record_id, "snapshot": refreshed_snapshot}

    async def validate_credentials(self) -> None:
        """Validate credentials using the full login probe."""
        await self.login()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        allow_login_redirect_check: bool = False,
    ) -> ClientResponse:
        req_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if headers:
            req_headers.update(headers)

        response = await self._session.request(
            method,
            url,
            headers=req_headers,
            data=data,
            allow_redirects=False,
        )

        if response.status >= 500:
            body = await response.text()
            raise TraxmilesError(
                f"Traxmiles server error {response.status}: {body[:200].strip()}"
            )

        if response.status == 401:
            body = await response.text()
            raise TraxmilesAuthError(f"Unauthenticated: {body[:200].strip()}")

        if response.status == 302 and not allow_login_redirect_check:
            location = response.headers.get("Location", "")
            if "/login" in location:
                raise TraxmilesAuthError("Redirected to /login")

        return response

    @staticmethod
    def _is_login_redirect(response: ClientResponse) -> bool:
        if response.status != 302:
            return False
        location = response.headers.get("Location", "")
        return "/login" in location

    @staticmethod
    def _absolute_url(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("/"):
            return f"https://traxmiles.co.uk{url}"
        return f"https://traxmiles.co.uk/{url}"

    @staticmethod
    def _parse_validation_message(raw_body: str) -> str | None:
        match = re.search(r'"errors"\s*:\s*\{\s*"[^"]+"\s*:\s*\[\s*"([^"]+)"', raw_body)
        if match:
            return match.group(1)
        return None

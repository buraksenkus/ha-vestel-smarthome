"""Cloud API client for the Vestel Smart Home platform."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    API_BASE,
    CLIENT_ID,
    CLIENT_SECRET,
    COGNITO_URL,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
TOKEN_EXPIRY_MARGIN = 120


class VestelError(Exception):
    """Generic error talking to the Vestel cloud."""


class VestelAuthError(VestelError):
    """Credentials or tokens were rejected."""


def _secret_hash(username: str) -> str:
    digest = hmac.new(
        CLIENT_SECRET.encode(), (username + CLIENT_ID).encode(), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


def _jwt_expiry(token: str) -> float:
    """Return the exp claim of a JWT, or 0 when it cannot be read."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except (IndexError, ValueError, KeyError, binascii.Error, json.JSONDecodeError):
        return 0.0


class VestelApi:
    """Talks to Cognito for tokens and to the appliance API for everything else."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._email = email
        self._password = password
        self._refresh_token = refresh_token
        self._id_token: str | None = None
        self._id_token_expires: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def refresh_token(self) -> str | None:
        """Return the current refresh token, if any."""
        return self._refresh_token

    async def _cognito(self, target: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.post(
                COGNITO_URL,
                data=json.dumps(payload),
                headers={
                    "Content-Type": "application/x-amz-json-1.1",
                    "X-Amz-Target": f"AWSCognitoIdentityProviderService.{target}",
                    "Accept": "*/*",
                },
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status != 200:
                    kind = str(body.get("__type", ""))
                    message = str(body.get("message", body))
                    if "NotAuthorized" in kind or "UserNotFound" in kind:
                        raise VestelAuthError(message)
                    raise VestelError(f"{kind}: {message}")
                return body
        except (ClientError, asyncio.TimeoutError) as err:
            raise VestelError(f"Cognito request failed: {err}") from err

    def _store_tokens(self, result: dict[str, Any]) -> None:
        self._id_token = result["IdToken"]
        self._id_token_expires = _jwt_expiry(self._id_token) or (
            time.time() + float(result.get("ExpiresIn", 3600))
        )
        # Refresh token rotation is disabled on this pool, so it is only
        # returned by the initial login.
        if result.get("RefreshToken"):
            self._refresh_token = result["RefreshToken"]

    async def async_login(self) -> None:
        """Authenticate with e-mail and password."""
        if not self._password:
            raise VestelAuthError("No password available")
        body = await self._cognito(
            "InitiateAuth",
            {
                "AuthFlow": "USER_PASSWORD_AUTH",
                "ClientId": CLIENT_ID,
                "AuthParameters": {
                    "USERNAME": self._email,
                    "PASSWORD": self._password,
                    "SECRET_HASH": _secret_hash(self._email),
                },
            },
        )
        if "AuthenticationResult" not in body:
            # e.g. an MFA or NEW_PASSWORD_REQUIRED challenge
            raise VestelAuthError(
                f"Unsupported auth challenge: {body.get('ChallengeName')}"
            )
        self._store_tokens(body["AuthenticationResult"])

    async def async_refresh(self) -> None:
        """Exchange the refresh token for a fresh ID token."""
        if not self._refresh_token:
            raise VestelAuthError("No refresh token available")
        body = await self._cognito(
            "GetTokensFromRefreshToken",
            {
                "ClientMetadata": {},
                "ClientSecret": CLIENT_SECRET,
                "ClientId": CLIENT_ID,
                "RefreshToken": self._refresh_token,
            },
        )
        self._store_tokens(body["AuthenticationResult"])

    async def async_get_token(self) -> str:
        """Return a valid ID token, refreshing or re-logging in as needed."""
        async with self._lock:
            if self._id_token and time.time() < self._id_token_expires - TOKEN_EXPIRY_MARGIN:
                return self._id_token

            if self._refresh_token:
                try:
                    await self.async_refresh()
                except VestelAuthError:
                    if not self._password:
                        raise
                    _LOGGER.debug("Refresh token rejected, logging in again")
                    self._refresh_token = None
                    await self.async_login()
            else:
                await self.async_login()

            assert self._id_token is not None
            return self._id_token

    async def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        for attempt in (1, 2):
            token = await self.async_get_token()
            try:
                async with self._session.request(
                    method,
                    f"{API_BASE}{path}",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Language": "tr-TR;q=1.0, en-TR;q=0.9",
                        "User-Agent": USER_AGENT,
                        "Token": token,
                    },
                    timeout=REQUEST_TIMEOUT,
                ) as resp:
                    if resp.status in (401, 403) and attempt == 1:
                        # Force a new token and try once more.
                        self._id_token_expires = 0.0
                        continue
                    if resp.status in (401, 403):
                        raise VestelAuthError(f"HTTP {resp.status} from {path}")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise VestelError(f"HTTP {resp.status} from {path}: {text[:200]}")
                    return await resp.json(content_type=None)
            except (ClientError, asyncio.TimeoutError) as err:
                raise VestelError(f"Request to {path} failed: {err}") from err

        raise VestelError(f"Request to {path} failed after retry")

    async def async_get_homes(self) -> list[dict[str, Any]]:
        """Return the homes registered to the account."""
        body = await self._request("GET", "/homes")
        items = body.get("items") or body.get("data") or body
        if isinstance(items, dict):
            items = items.get("homes", [])
        return list(items or [])

    async def async_get_devices(self, home_id: str) -> list[dict[str, Any]]:
        """Return the appliances belonging to a home."""
        body = await self._request("GET", f"/homes/{home_id}/devices")
        return list((body.get("items") or {}).get("homeappliances") or [])

    async def async_get_discovery(self, uuid: str) -> dict[str, Any]:
        """Return the capability schema of an appliance."""
        body = await self._request("GET", f"/device/discovery?uuid={uuid}")
        return body.get("data") or {}

    async def async_get_status(self, uuid: str) -> dict[str, str]:
        """Return the raw register values of an appliance."""
        body = await self._request("GET", f"/homeappliances/legacy/status?uuid={uuid}")
        return dict(body.get("data") or {})

    async def async_send_command(self, device: dict[str, Any], command: str) -> None:
        """Send a raw register command such as ``ACGENSI00001``."""
        uuid = device["deviceId"]
        payload = {
            "brand": str(device.get("oemBrand", "Vestel")).capitalize(),
            "device_type": device.get("deviceType", "AC"),
            "wifi_card_type": device.get("wifiCardType", ""),
            "message": json.dumps({"cmd": f"c:{uuid},{command}"}),
        }
        body = await self._request(
            "POST", f"/customer/devices/{uuid}/legacy/command", payload
        )
        if str(body.get("message", "")).lower() != "success":
            raise VestelError(f"Command {command} rejected: {body}")

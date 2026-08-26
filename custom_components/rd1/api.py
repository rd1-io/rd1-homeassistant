"""Async REST client for the RD1 control unit."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from .const import CATALOG_PATH, CMD_PATH, REQUEST_TIMEOUT, STATUS_PATH


class Rd1ApiError(HomeAssistantError):
    """Transport-level error talking to the CU."""


class Rd1CommandRejected(HomeAssistantError):
    """The CU consciously refused a command (interlock)."""


class Rd1ApiClient:
    """Thin wrapper over the CU's local REST API."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self._host = host.rstrip("/")
        self._base = f"http://{self._host}"

    @property
    def host(self) -> str:
        return self._host

    async def _get_json(self, path: str) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
        except TimeoutError as exc:
            raise Rd1ApiError(f"Таймаут запроса к {self._host}") from exc
        except aiohttp.ClientError as exc:
            raise Rd1ApiError(f"Ошибка запроса к {self._host}: {exc}") from exc
        except ValueError as exc:
            raise Rd1ApiError(f"Невалидный JSON от {self._host}") from exc
        if not isinstance(data, dict):
            raise Rd1ApiError(f"Неожиданный ответ от {self._host}")
        return data

    async def get_catalog(self) -> dict[str, Any]:
        """GET /api/ha → the entity descriptor catalog."""
        return await self._get_json(CATALOG_PATH)

    async def get_status(self) -> dict[str, Any]:
        """GET /api/status → the state document the catalog points into."""
        return await self._get_json(STATUS_PATH)

    async def post_command(self, command: dict[str, Any]) -> None:
        """POST /api/cmd. Raises Rd1CommandRejected on a conscious refusal."""
        url = f"{self._base}{CMD_PATH}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.post(url, json=command) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise Rd1ApiError(f"CU ответил {resp.status}: {text[:200]}")
                    data = await resp.json(content_type=None)
        except TimeoutError as exc:
            raise Rd1ApiError(f"Таймаут команды к {self._host}") from exc
        except aiohttp.ClientError as exc:
            raise Rd1ApiError(f"Ошибка запроса к {self._host}: {exc}") from exc

        if not isinstance(data, dict):
            raise Rd1ApiError(f"Неожиданный ответ от {self._host}")
        if data.get("ok") is True:
            return
        reason = data.get("reason", "error")
        message = data.get("message") or "Команда отклонена устройством"
        raise Rd1CommandRejected(message, translation_domain="rd1", translation_key=reason)

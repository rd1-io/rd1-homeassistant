"""DataUpdateCoordinator for the RD1 integration.

Polls GET /api/status every POLL_INTERVAL. The catalog (GET /api/ha) is
re-fetched only when `ha_rev` in the status document changes (or on the
first poll / older firmware that does not publish `ha_rev`).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Rd1ApiClient
from .config_flow import entry_title
from .const import CONF_HOST, DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class Rd1Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches catalog + status and exposes them to the platform entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Rd1ApiClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data['serial']}",
            update_interval=POLL_INTERVAL,
        )
        self.client = client
        self.entry = entry
        self.catalog: dict[str, Any] = {}
        self.status: dict[str, Any] = {}
        self.rev: int | None = None
        self.last_reload_rev: int | None = None

    @property
    def serial(self) -> str:
        return str(self.entry.data["serial"])

    @property
    def entities(self) -> list[dict[str, Any]]:
        return list(self.catalog.get("entities") or [])

    def device_info(self) -> dict[str, Any]:
        host = str(self.entry.data.get(CONF_HOST) or self.client.host)
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self.serial)},
            "name": self.catalog.get("name") or self.catalog.get("product") or self.serial,
            "manufacturer": "rd1.io",
            "model": self.catalog.get("product") or self.serial,
        }
        if host:
            info["configuration_url"] = f"http://{host}"
        if self.catalog.get("sw_version"):
            info["sw_version"] = self.catalog["sw_version"]
        if self.catalog.get("hw_version"):
            info["hw_version"] = self.catalog["hw_version"]
        return info

    def sync_entry_title(self) -> None:
        host = str(self.entry.data.get(CONF_HOST) or self.client.host)
        name = str(self.catalog.get("name") or self.catalog.get("product") or self.serial)
        title = entry_title(name, host)
        if self.entry.title != title:
            self.hass.config_entries.async_update_entry(self.entry, title=title)

    async def _async_update_data(self) -> dict[str, Any]:
        host = str(self.entry.data.get(CONF_HOST) or "")
        if host and host != self.client.host:
            self.client.set_host(host)
            self.sync_entry_title()

        try:
            status = await self.client.get_status()
        except Exception as exc:  # noqa: BLE001 — surfaced to HA as UpdateFailed
            raise UpdateFailed(f"Ошибка опроса {self.client.host}: {exc}") from exc

        status_rev = status.get("ha_rev")
        # First poll, missing ha_rev (old firmware), or a real rev change.
        need_catalog = (
            not self.catalog
            or self.rev is None
            or status_rev is None
            or status_rev != self.rev
        )
        if need_catalog:
            try:
                catalog = await self.client.get_catalog()
            except Exception as exc:  # noqa: BLE001
                raise UpdateFailed(f"Ошибка опроса {self.client.host}: {exc}") from exc
            if catalog.get("ha_api") != 1:
                raise UpdateFailed(
                    f"Устройство отдало неподдерживаемый ha_api={catalog.get('ha_api')}"
                )
            new_rev = catalog.get("rev")
            if self.catalog == {} or self.rev is None or new_rev != self.rev:
                _LOGGER.info(
                    "catalog rev %s → %s (%d entities)",
                    self.rev,
                    new_rev,
                    len(catalog.get("entities") or []),
                )
                self.catalog = catalog
                self.rev = new_rev

        self.status = status
        return {"catalog": self.catalog, "status": status}

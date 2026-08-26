"""Diagnostics support: dump the catalog + status with secrets redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_SECRET_KEYS = {"ssid", "wifi_pass", "saved_ssid", "bssid", "password", "pass"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("**REDACTED**" if key.lower() in _SECRET_KEYS else _redact(val))
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "host": coordinator.client.host,
        "catalog": coordinator.catalog,
        "status": _redact(coordinator.status),
    }

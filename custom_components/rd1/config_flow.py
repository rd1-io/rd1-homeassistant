"""Config flow for the RD1 local REST integration.

Discovery: the CU advertises `_rd1._tcp.local.` with TXT records
serial/product/ha_api/rev. Manual host entry stays available as a fallback
(different VLAN, mDNS filtered by the router).
"""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .api import Rd1ApiClient, Rd1ApiError
from .const import CONF_SERIAL, DOMAIN, SERIAL_RE

_SERIAL = re.compile(SERIAL_RE)


def _host_from_discovery(info: Any) -> str:
    host = getattr(info, "host", None)
    if not host:
        host = info.get("host")  # dict fallback for tests
    return str(host).rstrip(".")


def entry_title(name: str, host: str) -> str:
    """Integration row: device name plus the address HA talks to."""
    host = host.strip().rstrip(".")
    name = (name or "").strip()
    if not name:
        return host
    if not host:
        return name
    return f"{name} · {host}"


class Rd1ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RD1."""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._discovered_host: str | None = None
        self._catalog: dict[str, Any] | None = None
        self._discovery_placeholders: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return Rd1OptionsFlow()

    async def _validate_host(self, host: str) -> dict[str, Any]:
        """Fetch /api/ha from the host; raise ValueError with a reason on failure."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        client = Rd1ApiClient(session, host)
        try:
            catalog = await client.get_catalog()
        except Rd1ApiError as exc:
            raise ValueError("unreachable") from exc
        if catalog.get("ha_api") != 1:
            raise ValueError("unsupported_api")
        serial = str(catalog.get("serial") or "")
        if not _SERIAL.match(serial):
            raise ValueError("bad_serial")
        self._catalog = catalog
        return catalog

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            try:
                catalog = await self._validate_host(host)
            except ValueError as exc:
                errors["base"] = str(exc)
            else:
                return self._make_entry(host, str(catalog["serial"]), catalog)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: Any) -> ConfigFlowResult:
        """mDNS discovery: `_rd1._tcp.local.` with serial/product TXT records."""
        host = _host_from_discovery(discovery_info)
        props: dict[str, Any] = getattr(discovery_info, "properties", {}) or {}
        serial = str(props.get("serial") or "")
        product = str(props.get("product") or "")

        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._discovered_host = host
        self._discovery_placeholders = {
            "serial": serial or "?",
            "product": product or "?",
            "host": host,
        }
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            host = self._discovered_host
            try:
                catalog = await self._validate_host(host)
            except ValueError as exc:
                return self.async_abort(reason=str(exc))
            return self._make_entry(host, str(catalog["serial"]), catalog)
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders=self._discovery_placeholders,
        )

    def _make_entry(self, host: str, serial: str, catalog: dict[str, Any]) -> ConfigFlowResult:
        name = str(catalog.get("name") or catalog.get("product") or serial)
        return self.async_create_entry(
            title=entry_title(name, host),
            data={CONF_HOST: host, CONF_SERIAL: serial},
        )


class Rd1OptionsFlow(OptionsFlow):
    """Change the controller address without removing the integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = str(self.config_entry.data.get(CONF_HOST) or "")
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            session = aiohttp_client.async_get_clientsession(self.hass)
            client = Rd1ApiClient(session, host)
            try:
                catalog = await client.get_catalog()
            except Rd1ApiError:
                errors["base"] = "unreachable"
            else:
                if catalog.get("ha_api") != 1:
                    errors["base"] = "unsupported_api"
                elif str(catalog.get("serial") or "") != str(self.config_entry.data.get(CONF_SERIAL)):
                    errors["base"] = "serial_mismatch"
                else:
                    name = str(catalog.get("name") or catalog.get("product") or catalog.get("serial"))
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, CONF_HOST: host},
                        title=entry_title(name, host),
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=current): str}),
            errors=errors,
        )

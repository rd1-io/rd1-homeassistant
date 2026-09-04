"""Config flow tests for the RD1 integration.

Covers the four cases from the plan: manual host, zeroconf discovery,
duplicate serial (already configured), and unreachable device.

Requires a Home Assistant test environment:
    pip install homeassistant pytest-homeassistant-custom-component
Run with: pytest --asyncio-mode=auto
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.rd1 import config_flow  # noqa: E402
from custom_components.rd1.const import CONF_HOST, CONF_SERIAL, DOMAIN  # noqa: E402

CATALOG = {
    "ha_api": 1,
    "rev": 1,
    "product": "sauna1-cu",
    "serial": "RD1S-AABBCC",
    "name": "Sauna1 Controller",
    "sw_version": "1.2.3",
    "entities": [],
}


def _mock_get_json(catalog: dict | None):
    async def _get_json(self, path: str):
        if path == "/api/ha":
            if catalog is None:
                raise TimeoutError
            return catalog
        if path == "/api/status":
            return {"serial": "RD1S-AABBCC"}
        raise AssertionError(f"unexpected path {path}")

    return _get_json


@patch("custom_components.rd1.config_flow.aiohttp_client.async_get_clientsession")
@patch.object(config_flow.Rd1ApiClient, "_get_json", autospec=True)
async def test_user_flow_manual_host(mock_get, _session, hass: HomeAssistant):
    mock_get.side_effect = _mock_get_json(CATALOG)
    flow = config_flow.Rd1ConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result["type"] == "form"

    result = await flow.async_step_user({CONF_HOST: "192.168.1.10"})
    assert result["type"] == "create_entry"
    assert result["data"] == {CONF_HOST: "192.168.1.10", CONF_SERIAL: "RD1S-AABBCC"}
    assert result["title"] == "Sauna1 Controller · 192.168.1.10"


@patch("custom_components.rd1.config_flow.aiohttp_client.async_get_clientsession")
@patch.object(config_flow.Rd1ApiClient, "_get_json", autospec=True)
async def test_user_flow_unreachable(mock_get, _session, hass: HomeAssistant):
    mock_get.side_effect = _mock_get_json(None)
    flow = config_flow.Rd1ConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user({CONF_HOST: "192.168.1.99"})
    assert result["type"] == "form"
    assert result["errors"] == {"base": "unreachable"}


@patch("custom_components.rd1.config_flow.aiohttp_client.async_get_clientsession")
@patch.object(config_flow.Rd1ApiClient, "_get_json", autospec=True)
async def test_zeroconf_flow(mock_get, _session, hass: HomeAssistant):
    mock_get.side_effect = _mock_get_json(CATALOG)
    flow = config_flow.Rd1ConfigFlow()
    flow.hass = hass

    discovery = type(
        "ZeroconfInfo",
        (),
        {"host": "rd1-aabbcc.local.", "properties": {"serial": "RD1S-AABBCC", "product": "sauna1-cu"}},
    )()
    result = await flow.async_step_zeroconf(discovery)
    assert result["type"] == "form"
    assert result["step_id"] == "zeroconf_confirm"

    result = await flow.async_step_zeroconf_confirm({})
    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "rd1-aabbcc.local"


async def test_zeroconf_duplicate_serial(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "10.0.0.5", CONF_SERIAL: "RD1S-AABBCC"},
        unique_id="RD1S-AABBCC",
    )
    entry.add_to_hass(hass)

    flow = config_flow.Rd1ConfigFlow()
    flow.hass = hass
    discovery = type(
        "ZeroconfInfo",
        (),
        {"host": "rd1-aabbcc.local.", "properties": {"serial": "RD1S-AABBCC", "product": "sauna1-cu"}},
    )()
    result = await flow.async_step_zeroconf(discovery)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"

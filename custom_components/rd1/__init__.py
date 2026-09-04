"""RD1 local REST integration for Home Assistant.

One HA device per control unit; its entities come entirely from the device's
catalog (GET /api/ha). No product-specific code lives here.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import Rd1ApiClient
from .const import CONF_HOST, DOMAIN
from .coordinator import Rd1Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.LIGHT,
    Platform.FAN,
    Platform.CLIMATE,
    Platform.HUMIDIFIER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    client = Rd1ApiClient(session, entry.data[CONF_HOST])
    coordinator = Rd1Coordinator(hass, client, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # A catalog `rev` change means the entity set changed (e.g. ventilation
    # role rebinding). Reload the entry so platforms pick up added/removed
    # entities without an HA restart.
    def _reload_on_rev_change() -> None:
        if coordinator.rev != coordinator.last_reload_rev:
            coordinator.last_reload_rev = coordinator.rev
            hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))

    coordinator.last_reload_rev = coordinator.rev
    coordinator.sync_entry_title()
    entry.async_on_unload(
        coordinator.async_add_listener(_reload_on_rev_change)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

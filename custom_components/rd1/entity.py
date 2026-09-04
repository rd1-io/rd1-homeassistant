"""Base entity for RD1 catalog-driven platforms."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import Rd1Coordinator
from .state_resolver import MISSING, attr, attr_bool, build_command, entity_available


class Rd1Entity(CoordinatorEntity[Rd1Coordinator], Entity):
    """Entity backed by a catalog descriptor + /api/status pointers."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Rd1Coordinator, desc: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self.desc = desc
        self._attr_unique_id = f"{coordinator.serial}:{desc['platform']}:{desc['id']}"
        self._attr_name = str(desc.get("name") or desc["id"])

    @property
    def device_info(self) -> dict[str, Any]:
        return self.coordinator.device_info()

    @property
    def available(self) -> bool:
        return super().available and entity_available(self.desc, self.coordinator.status)

    def _attr(self, attribute: str) -> Any:
        value, _ = attr(self.desc, attribute, self.coordinator.status)
        return None if value is MISSING else value

    def _attr_bool(self, attribute: str) -> bool | None:
        return attr_bool(self.desc, attribute, self.coordinator.status)

    async def _send_command(self, name: str, fields: dict[str, Any] | None = None) -> None:
        """Instantiate a catalog command from the HA service call and POST it.

        On a conscious refusal the CU answers ok:false; HA raises
        HomeAssistantError and immediately refreshes so the optimistic state is
        rolled back to the real device state.
        """
        template = (self.desc.get("commands") or {}).get(name)
        if not isinstance(template, dict):
            raise HomeAssistantError(f"Команда {name} не описана в каталоге устройства")
        command = build_command(template, fields or {})
        try:
            await self.coordinator.client.post_command(command)
        except HomeAssistantError:
            await self.coordinator.async_request_refresh()
            raise
        await self.coordinator.async_request_refresh()

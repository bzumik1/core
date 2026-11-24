"""Base entity for WAFE heat recovery units."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import override

from modbus_connection import ModbusError
from wafe_modbus import READINGS, WafeUnit

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WafeDataUpdateCoordinator, WafeRuntimeData


@dataclass(frozen=True, kw_only=True)
class WafeEntityDescription(EntityDescription):
    """Describe a WAFE entity."""

    component: str
    """Attribute name of the library component the entity reads."""


class WafeEntity(CoordinatorEntity[WafeDataUpdateCoordinator]):
    """An entity of a WAFE unit."""

    _attr_has_entity_name = True
    entity_description: WafeEntityDescription

    def __init__(
        self,
        runtime_data: WafeRuntimeData,
        entity_description: WafeEntityDescription,
    ) -> None:
        """Initialize the entity."""
        coordinator = (
            runtime_data.readings
            if entity_description.component in READINGS
            else runtime_data.settings
        )
        super().__init__(coordinator)
        self._runtime_data = runtime_data
        self.entity_description = entity_description
        self._attr_unique_id = f"{coordinator.device.unit_id}_{entity_description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def device(self) -> WafeUnit:
        """The library object of the unit."""
        return self.coordinator.device

    @property
    @override
    def available(self) -> bool:
        """Whether this entity's component answered the latest poll."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.component in self.coordinator.data.updated
        )

    async def _async_write(self, write: Callable[[], Awaitable[None]]) -> None:
        """Write to the unit, then read back both polls.

        A write can change values in the other poll, like a setting that also
        sets a coil, so both are read again right away.
        """
        try:
            await write()
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_value",
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            ) from err
        await self._runtime_data.readings.async_refresh()
        await self._runtime_data.settings.async_refresh()

"""Data update coordinator for WAFE heat recovery units."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, override

from modbus_connection import ModbusConnectionError, ModbusError, ModbusTimeoutError
from wafe_modbus import UpdateReport, WafeUnit

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
    UpdateFailedUnreachable,
)

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


class WafeDataUpdateCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Run one of the unit's update methods on its own interval."""

    config_entry: WafeConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WafeConfigEntry,
        name: str,
        device: WafeUnit,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=interval,
        )
        self.device = device
        self._poll = poll
        self._failing: set[str] = set()

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the unit to the device registry."""
        if TYPE_CHECKING:
            assert self.config_entry.unique_id is not None
        model = self.device.model
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.unique_id)},
            manufacturer=MANUFACTURER,
            model=model.name if model is not None else None,
            name=self.config_entry.title,
        )

    @override
    async def _async_update_data(self) -> UpdateReport:
        try:
            report = await self._poll()
        except (ModbusConnectionError, ModbusTimeoutError) as err:
            raise UpdateFailedUnreachable(
                translation_domain=DOMAIN,
                translation_key="unit_unreachable",
            ) from err
        except ModbusError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="modbus_error",
            ) from err
        if not report.updated:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="no_component_answered",
            ) from ExceptionGroup(
                "all components failed to refresh", list(report.failed.values())
            )
        self._log_component_changes(report)
        return report

    def _log_component_changes(self, report: UpdateReport) -> None:
        """Log a component's first failure and its recovery, once each."""
        for name, cause in report.failed.items():
            if name not in self._failing:
                self._failing.add(name)
                _LOGGER.warning(
                    "%s: %s failed to refresh, its entities are unavailable: %s",
                    self.name,
                    name,
                    cause,
                )
        for name in report.updated & self._failing:
            self._failing.discard(name)
            _LOGGER.info("%s: %s is available again", self.name, name)


@dataclass
class WafeRuntimeData:
    """Runtime data of a WAFE config entry."""

    readings: WafeDataUpdateCoordinator
    settings: WafeDataUpdateCoordinator


type WafeConfigEntry = ConfigEntry[WafeRuntimeData]

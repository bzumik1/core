"""Binary sensors of WAFE heat recovery units."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from wafe_modbus import SubMode, WafeUnit

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import WafeConfigEntry
from .entity import WafeEntity, WafeEntityDescription

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WafeBinarySensorEntityDescription(
    BinarySensorEntityDescription, WafeEntityDescription
):
    """Describe a WAFE binary sensor."""

    value_fn: Callable[[WafeUnit], bool | None]


def _sub_mode(flag: SubMode) -> Callable[[WafeUnit], bool | None]:
    def value(device: WafeUnit) -> bool | None:
        sub_mode = device.status.sub_mode
        return None if sub_mode is None else flag in sub_mode

    return value


BINARY_SENSOR_DESCRIPTIONS: tuple[WafeBinarySensorEntityDescription, ...] = (
    WafeBinarySensorEntityDescription(
        key="bypass",
        translation_key="bypass",
        component="status",
        value_fn=_sub_mode(SubMode.BYPASS),
    ),
    WafeBinarySensorEntityDescription(
        key="holiday_ventilation",
        translation_key="holiday_ventilation",
        component="status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_sub_mode(SubMode.HOLIDAY_VENTILATION),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WafeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WAFE binary sensors."""
    async_add_entities(
        WafeBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class WafeBinarySensor(WafeEntity, BinarySensorEntity):
    """A binary sensor of a WAFE unit."""

    entity_description: WafeBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return whether the condition holds."""
        return self.entity_description.value_fn(self.device)

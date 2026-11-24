"""Switches of WAFE heat recovery units."""

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import WafeConfigEntry
from .entity import WafeEntity, WafeEntityDescription

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class WafeSwitchEntityDescription(SwitchEntityDescription, WafeEntityDescription):
    """Describe a switch backed by a coil or a 0/1 setting."""

    field: str
    """Attribute name of the field on the component."""


def _function(key: str, *, enabled: bool = True) -> WafeSwitchEntityDescription:
    return WafeSwitchEntityDescription(
        key=key,
        translation_key=key,
        component="functions",
        field=key,
        entity_registry_enabled_default=enabled,
    )


def _setting(key: str, *, enabled: bool = True) -> WafeSwitchEntityDescription:
    return WafeSwitchEntityDescription(
        key=key,
        translation_key=key,
        component="settings",
        field=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
    )


SWITCH_DESCRIPTIONS: tuple[WafeSwitchEntityDescription, ...] = (
    _function("short_boost"),
    _function("long_boost"),
    _function("holiday"),
    _function("silent"),
    _function("sleep"),
    _function("fireplace", enabled=False),
    _function("bypass_off"),
    _setting("bypass_disabled", enabled=False),
    _setting("bypass_by_co2", enabled=False),
    _setting("airflow_limit", enabled=False),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WafeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WAFE switches."""
    async_add_entities(
        WafeSwitch(entry.runtime_data, description)
        for description in SWITCH_DESCRIPTIONS
    )


class WafeSwitch(WafeEntity, SwitchEntity):
    """A switch of a WAFE unit."""

    entity_description: WafeSwitchEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the state the unit reported."""
        value: bool | None = getattr(
            getattr(self.device, self.entity_description.component),
            self.entity_description.field,
        )
        return value

    async def _async_set(self, value: bool) -> None:
        component = getattr(self.device, self.entity_description.component)
        await self._async_write(
            lambda: component.write(self.entity_description.field, value)
        )

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the function on."""
        await self._async_set(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the function off."""
        await self._async_set(False)

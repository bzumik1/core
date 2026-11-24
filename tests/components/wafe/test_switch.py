"""Tests for the WAFE switch platform."""

from unittest.mock import patch

from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_get_unit")
async def test_all_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all switches match their snapshot."""
    with patch("homeassistant.components.wafe.PLATFORMS", [Platform.SWITCH]):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "coil"),
    [
        pytest.param("switch.wafe_w201_short_boost", 7, id="short_boost"),
        pytest.param("switch.wafe_w201_long_boost", 8, id="long_boost"),
        pytest.param("switch.wafe_w201_holiday_mode", 5, id="holiday"),
        pytest.param("switch.wafe_w201_silent_mode", 6, id="silent"),
        pytest.param("switch.wafe_w201_standby", 4, id="sleep"),
        pytest.param("switch.wafe_w201_bypass_off", 9, id="bypass_off"),
    ],
)
async def test_function_switch(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    entity_id: str,
    coil: int,
) -> None:
    """Test a function switch writes its coil and shows the read-back state."""
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert mock_unit.coil[coil] is True
    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert mock_unit.coil[coil] is False
    assert hass.states.get(entity_id).state == STATE_OFF


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("entity_id", "register"),
    [
        pytest.param("switch.wafe_w201_bypass_disabled", 2026, id="bypass_disabled"),
        pytest.param("switch.wafe_w201_bypass_airflow_by_co2", 2025, id="by_co2"),
        pytest.param("switch.wafe_w201_airflow_limit", 2012, id="airflow_limit"),
    ],
)
async def test_setting_switch(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    entity_id: str,
    register: int,
) -> None:
    """Test a setting switch writes its holding register."""
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert mock_unit.holding[register] == 1
    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert mock_unit.holding[register] == 0
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_switch_write_failed(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
) -> None:
    """Test a failed write raises a translated error."""
    mock_unit.fail_write(7, ModbusTimeoutError(), register_type="coil")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.wafe_w201_short_boost"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "write_failed"

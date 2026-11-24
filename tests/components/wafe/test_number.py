"""Tests for the WAFE number platform."""

from unittest.mock import patch

from modbus_connection import IllegalDataValueError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

MANUAL_AIRFLOW = "number.wafe_w201_manual_airflow"


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_get_unit")
async def test_all_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all numbers match their snapshot."""
    with patch("homeassistant.components.wafe.PLATFORMS", [Platform.NUMBER]):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_set_manual_airflow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
) -> None:
    """Test setting the manual airflow."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: MANUAL_AIRFLOW, ATTR_VALUE: 120},
        blocking=True,
    )

    assert mock_unit.holding[2009] == 120
    assert hass.states.get(MANUAL_AIRFLOW).state == "120"


async def test_set_manual_airflow_outside_fresh_limits(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
) -> None:
    """Test a value outside limits changed on the unit since the poll is refused."""
    mock_unit.holding[2008] = 100

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: MANUAL_AIRFLOW, ATTR_VALUE: 60},
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_value"
    assert mock_unit.holding[2009] == 75


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("entity_id", "value", "register", "raw"),
    [
        pytest.param("number.wafe_w201_co2_setpoint", 800, 2006, 800, id="co2"),
        pytest.param(
            "number.wafe_w201_short_boost_duration", 1200, 2027, 1200, id="boost"
        ),
        pytest.param(
            "number.wafe_w201_bypass_minimum_temperature_difference",
            2.5,
            2014,
            25,
            id="scaled",
        ),
        pytest.param(
            "number.wafe_w201_fan_imbalance", -20, 2002, 0x10000 - 20, id="signed"
        ),
        pytest.param(
            "number.wafe_w201_preheater_start_temperature",
            -5.5,
            2055,
            0x10000 - 55,
            id="negative_scaled",
        ),
    ],
)
async def test_set_setting(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    entity_id: str,
    value: float,
    register: int,
    raw: int,
) -> None:
    """Test a setting writes its holding register with the right encoding."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )

    assert mock_unit.holding[register] == raw
    assert float(hass.states.get(entity_id).state) == value


async def test_set_value_write_failed(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
) -> None:
    """Test a failed write raises a translated error."""
    mock_unit.fail_write(2006, IllegalDataValueError())

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "number.wafe_w201_co2_setpoint", ATTR_VALUE: 800},
            blocking=True,
        )

    assert exc_info.value.translation_key == "write_failed"

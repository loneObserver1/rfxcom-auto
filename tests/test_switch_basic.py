"""Tests basiques pour switch.py avec mocks corrects."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.switch'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()

# Mock CoordinatorEntity et SwitchEntity
class MockCoordinatorEntity:
    def __class_getitem__(cls, item):
        return MockCoordinatorEntity
    
    def __init__(self, coordinator):
        self.coordinator = coordinator

class MockSwitchEntity:
    pass

sys.modules['homeassistant.helpers.update_coordinator'].CoordinatorEntity = MockCoordinatorEntity
sys.modules['homeassistant.components.switch'].SwitchEntity = MockSwitchEntity

# Mock DeviceInfo
class MockDeviceInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules['homeassistant.helpers.entity'].DeviceInfo = MockDeviceInfo

from custom_components.rfxcom.switch import RFXCOMSwitch, async_setup_entry
from custom_components.rfxcom.const import (
    DOMAIN,
    PROTOCOL_ARC,
    PROTOCOL_AC,
    CMD_ON,
    CMD_OFF,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
)
from custom_components.rfxcom.coordinator import RFXCOMCoordinator


@pytest.fixture
def mock_coordinator():
    """Mock du coordinateur."""
    coordinator = Mock(spec=RFXCOMCoordinator)
    coordinator.send_command = AsyncMock(return_value=True)
    return coordinator


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.options = {
        "devices": [
            {
                "name": "Test ARC Switch",
                CONF_PROTOCOL: PROTOCOL_ARC,
                CONF_HOUSE_CODE: "A",
                CONF_UNIT_CODE: "1",
            },
            {
                "name": "Test AC Switch",
                CONF_PROTOCOL: PROTOCOL_AC,
                CONF_DEVICE_ID: "01020304",
                CONF_UNIT_CODE: "1",
            },
        ]
    }
    return entry


@pytest.fixture
def mock_hass(mock_coordinator):
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "test_entry": mock_coordinator
        }
    }
    
    # Mock device registry
    mock_dr = MagicMock()
    mock_device_entry = Mock()
    mock_dr.async_get.return_value = mock_dr
    mock_dr.async_get_or_create.return_value = mock_device_entry
    sys.modules['homeassistant.helpers.device_registry'].async_get = Mock(return_value=mock_dr)
    
    return hass


class TestRFXCOMSwitch:
    """Tests pour RFXCOMSwitch."""

    def test_switch_initialization_arc(self, mock_coordinator):
        """Test d'initialisation d'un switch ARC."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch_1",
            device_info=MockDeviceInfo(identifiers={("rfxcom", "ARC_A_1_0")}),
        )
        
        assert switch._attr_name == "Test Switch"
        assert switch._attr_unique_id == "test_switch_1"
        assert switch._house_code == "A"
        assert switch._unit_code == "1"

    def test_switch_initialization_ac(self, mock_coordinator):
        """Test d'initialisation d'un switch AC."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test AC Switch",
            protocol=PROTOCOL_AC,
            device_id="01020304",
            unit_code="1",
            unique_id="test_switch_ac",
            device_info=MockDeviceInfo(identifiers={("rfxcom", "AC_01020304_0")}),
        )
        
        assert switch._attr_name == "Test AC Switch"
        assert switch._device_id == "01020304"

    @pytest.mark.asyncio
    async def test_switch_turn_on_arc(self, mock_coordinator):
        """Test d'activation d'un switch ARC."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch_1",
        )
        switch.async_write_ha_state = AsyncMock()
        
        await switch.async_turn_on()
        
        mock_coordinator.send_command.assert_called_once()
        call_kwargs = mock_coordinator.send_command.call_args[1]
        assert call_kwargs["protocol"] == PROTOCOL_ARC
        assert call_kwargs["command"] == CMD_ON
        assert call_kwargs["house_code"] == "A"
        assert call_kwargs["unit_code"] == "1"
        assert switch._is_on is True

    @pytest.mark.asyncio
    async def test_switch_turn_off_arc(self, mock_coordinator):
        """Test de désactivation d'un switch ARC."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch_1",
        )
        switch.async_write_ha_state = AsyncMock()
        switch._is_on = True
        
        await switch.async_turn_off()
        
        mock_coordinator.send_command.assert_called_once()
        call_kwargs = mock_coordinator.send_command.call_args[1]
        assert call_kwargs["protocol"] == PROTOCOL_ARC
        assert call_kwargs["command"] == CMD_OFF
        assert call_kwargs["house_code"] == "A"
        assert call_kwargs["unit_code"] == "1"
        assert switch._is_on is False

    @pytest.mark.asyncio
    async def test_setup_entry(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration des switches."""
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        assert async_add_entities.called
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 2  # 2 switches
        assert all(isinstance(e, RFXCOMSwitch) for e in call_args)

    @pytest.mark.asyncio
    async def test_setup_entry_skip_cover(self, mock_hass, mock_entry, mock_coordinator):
        """Test que les covers sont ignorés."""
        mock_entry.options = {
            "devices": [
                {
                    "name": "Test Switch",
                    CONF_PROTOCOL: PROTOCOL_ARC,
                    CONF_HOUSE_CODE: "A",
                    CONF_UNIT_CODE: "1",
                },
                {
                    "name": "Test Cover",
                    CONF_PROTOCOL: PROTOCOL_ARC,
                    CONF_HOUSE_CODE: "A",
                    CONF_UNIT_CODE: "2",
                    "device_type": "cover",
                },
            ]
        }
        
        async_add_entities = AsyncMock()
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 1  # Seulement le switch, pas le cover


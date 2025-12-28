"""Tests basiques pour cover.py avec mocks corrects."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.cover'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()

# Mock CoordinatorEntity et CoverEntity
class MockCoordinatorEntity:
    def __class_getitem__(cls, item):
        return MockCoordinatorEntity
    
    def __init__(self, coordinator):
        self.coordinator = coordinator

class MockCoverEntity:
    pass

sys.modules['homeassistant.helpers.update_coordinator'].CoordinatorEntity = MockCoordinatorEntity
sys.modules['homeassistant.components.cover'].CoverEntity = MockCoverEntity

# Mock CoverEntityFeature
class MockCoverEntityFeature:
    OPEN = 1
    CLOSE = 2
    STOP = 4

sys.modules['homeassistant.components.cover'].CoverEntityFeature = MockCoverEntityFeature

# Mock DeviceInfo
class MockDeviceInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules['homeassistant.helpers.entity'].DeviceInfo = MockDeviceInfo

from custom_components.rfxcom.cover import RFXCOMCover, async_setup_entry
from custom_components.rfxcom.const import (
    DOMAIN,
    PROTOCOL_ARC,
    CMD_ON,
    CMD_OFF,
    DEVICE_TYPE_COVER,
    CONF_PROTOCOL,
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
                "name": "Test Cover",
                CONF_PROTOCOL: PROTOCOL_ARC,
                CONF_HOUSE_CODE: "A",
                CONF_UNIT_CODE: "1",
                "device_type": DEVICE_TYPE_COVER,
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


class TestRFXCOMCover:
    """Tests pour RFXCOMCover."""

    def test_cover_initialization(self, mock_coordinator):
        """Test d'initialisation d'un cover."""
        cover = RFXCOMCover(
            coordinator=mock_coordinator,
            name="Test Cover",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_cover_1",
            device_info=MockDeviceInfo(identifiers={("rfxcom", "ARC_A_1_0")}),
        )
        
        assert cover._attr_name == "Test Cover"
        assert cover._attr_unique_id == "test_cover_1"
        assert cover._house_code == "A"
        assert cover._unit_code == "1"

    @pytest.mark.asyncio
    async def test_cover_open(self, mock_coordinator):
        """Test d'ouverture d'un cover."""
        cover = RFXCOMCover(
            coordinator=mock_coordinator,
            name="Test Cover",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_cover_1",
        )
        cover.async_write_ha_state = AsyncMock()
        
        await cover.async_open_cover()
        
        mock_coordinator.send_command.assert_called_once()
        call_kwargs = mock_coordinator.send_command.call_args[1]
        assert call_kwargs["protocol"] == PROTOCOL_ARC
        assert call_kwargs["command"] == CMD_ON
        assert call_kwargs["house_code"] == "A"
        assert call_kwargs["unit_code"] == "1"

    @pytest.mark.asyncio
    async def test_cover_close(self, mock_coordinator):
        """Test de fermeture d'un cover."""
        cover = RFXCOMCover(
            coordinator=mock_coordinator,
            name="Test Cover",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_cover_1",
        )
        cover.async_write_ha_state = AsyncMock()
        
        await cover.async_close_cover()
        
        mock_coordinator.send_command.assert_called_once()
        call_kwargs = mock_coordinator.send_command.call_args[1]
        assert call_kwargs["protocol"] == PROTOCOL_ARC
        assert call_kwargs["command"] == CMD_OFF
        assert call_kwargs["house_code"] == "A"
        assert call_kwargs["unit_code"] == "1"

    @pytest.mark.asyncio
    async def test_cover_stop(self, mock_coordinator):
        """Test d'arrêt d'un cover."""
        cover = RFXCOMCover(
            coordinator=mock_coordinator,
            name="Test Cover",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_cover_1",
        )
        cover.async_write_ha_state = AsyncMock()
        
        await cover.async_stop_cover()
        
        # Pour ARC, stop utilise unit_code=3
        mock_coordinator.send_command.assert_called_once()
        call_kwargs = mock_coordinator.send_command.call_args[1]
        assert call_kwargs["protocol"] == PROTOCOL_ARC
        assert call_kwargs["command"] == CMD_ON
        assert call_kwargs["house_code"] == "A"
        assert call_kwargs["unit_code"] == "3"

    @pytest.mark.asyncio
    async def test_setup_entry(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration des covers."""
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        assert async_add_entities.called
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 1  # 1 cover
        assert isinstance(call_args[0], RFXCOMCover)

    @pytest.mark.asyncio
    async def test_setup_entry_skip_switch(self, mock_hass, mock_entry, mock_coordinator):
        """Test que les switches sont ignorés."""
        mock_entry.options = {
            "devices": [
                {
                    "name": "Test Cover",
                    CONF_PROTOCOL: PROTOCOL_ARC,
                    CONF_HOUSE_CODE: "A",
                    CONF_UNIT_CODE: "1",
                    "device_type": DEVICE_TYPE_COVER,
                },
                {
                    "name": "Test Switch",
                    CONF_PROTOCOL: PROTOCOL_ARC,
                    CONF_HOUSE_CODE: "A",
                    CONF_UNIT_CODE: "2",
                },
            ]
        }
        
        async_add_entities = AsyncMock()
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 1  # Seulement le cover, pas le switch


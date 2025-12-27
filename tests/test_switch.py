"""Tests pour les entités switch."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.components.switch import SwitchEntity

from custom_components.rfxcom.switch import RFXCOMSwitch
from custom_components.rfxcom.const import PROTOCOL_ARC, CMD_ON, CMD_OFF
from custom_components.rfxcom.coordinator import RFXCOMCoordinator


@pytest.fixture
def mock_coordinator():
    """Mock du coordinateur."""
    coordinator = Mock(spec=RFXCOMCoordinator)
    coordinator.send_command = AsyncMock(return_value=True)
    return coordinator


@pytest.fixture
def switch(mock_coordinator):
    """Créer un switch pour les tests."""
    return RFXCOMSwitch(
        coordinator=mock_coordinator,
        name="Test Switch",
        protocol=PROTOCOL_ARC,
        house_code="A",
        unit_code="1",
        unique_id="test_switch_1",
    )


class TestRFXCOMSwitch:
    """Tests pour RFXCOMSwitch."""

    def test_initialization(self, switch):
        """Test d'initialisation."""
        assert switch.name == "Test Switch"
        assert switch._protocol == PROTOCOL_ARC
        assert switch._house_code == "A"
        assert switch._unit_code == "1"
        assert switch._is_on is False

    @pytest.mark.asyncio
    async def test_turn_on(self, switch, mock_coordinator):
        """Test d'allumage."""
        await switch.async_turn_on()
        
        assert switch._is_on is True
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_ON,
            house_code="A",
            unit_code="1",
        )

    @pytest.mark.asyncio
    async def test_turn_off(self, switch, mock_coordinator):
        """Test d'extinction."""
        switch._is_on = True
        await switch.async_turn_off()
        
        assert switch._is_on is False
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_OFF,
            house_code="A",
            unit_code="1",
        )

    def test_is_on_property(self, switch):
        """Test de la propriété is_on."""
        switch._is_on = True
        assert switch.is_on is True
        
        switch._is_on = False
        assert switch.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_failure(self, switch, mock_coordinator):
        """Test d'échec d'allumage."""
        mock_coordinator.send_command.return_value = False
        switch._is_on = False
        
        await switch.async_turn_on()
        
        # L'état ne devrait pas changer en cas d'échec
        assert switch._is_on is False


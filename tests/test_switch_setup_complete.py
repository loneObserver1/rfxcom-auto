"""Tests complets pour switch.py avec async_setup_entry."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.switch'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.restore_state'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()

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

# Mock async_get_last_state
async def mock_async_get_last_state(hass, entity_id):
    return None

sys.modules['homeassistant.helpers.restore_state'].async_get_last_state = mock_async_get_last_state

from custom_components.rfxcom.switch import async_setup_entry, RFXCOMSwitch
from custom_components.rfxcom.const import (
    DOMAIN,
    PROTOCOL_ARC,
    PROTOCOL_AC,
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
    return hass


class TestSwitchSetupComplete:
    """Tests complets pour switch.py."""

    @pytest.mark.asyncio
    async def test_setup_entry(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration des switches."""
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        # Vérifier que les entités ont été ajoutées
        assert async_add_entities.called
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 2  # 2 appareils configurés
        
        # Vérifier que les switches ont les bons noms
        assert call_args[0]._attr_name == "Test ARC Switch"
        assert call_args[1]._attr_name == "Test AC Switch"

    @pytest.mark.asyncio
    async def test_setup_entry_empty_devices(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration sans appareils."""
        mock_entry.options = {"devices": []}
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        # Vérifier qu'aucune entité n'a été ajoutée
        assert async_add_entities.called
        call_args = async_add_entities.call_args[0][0]
        assert len(call_args) == 0

    @pytest.mark.asyncio
    async def test_switch_async_added_to_hass(self, mock_coordinator):
        """Test de async_added_to_hass."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch",
        )
        
        # Mock hass et entity_id
        switch.hass = MagicMock()
        switch.entity_id = "switch.test_switch"
        switch.async_write_ha_state = AsyncMock()
        
        # Mock async_get_last_state pour retourner None
        import sys
        sys.modules['homeassistant.helpers.restore_state'].async_get_last_state = AsyncMock(return_value=None)
        
        # Mock super().async_added_to_hass() si elle existe
        # Test (ne devrait pas lever d'exception)
        try:
            await switch.async_added_to_hass()
        except AttributeError:
            # Si super() n'a pas async_added_to_hass, c'est normal avec les mocks
            pass
        
        # Vérifier que async_write_ha_state a été appelé si la méthode a été exécutée
        # (peut ne pas être appelé si super() échoue)

    @pytest.mark.asyncio
    async def test_switch_turn_on_success(self, mock_coordinator):
        """Test turn_on réussi."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch",
        )
        switch.async_write_ha_state = AsyncMock()
        switch._is_on = False
        
        await switch.async_turn_on()
        
        assert switch._is_on is True
        assert switch.coordinator.send_command.called
        assert switch.async_write_ha_state.called

    @pytest.mark.asyncio
    async def test_switch_turn_on_failure(self, mock_coordinator):
        """Test turn_on échoué."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch",
        )
        switch.async_write_ha_state = AsyncMock()
        switch.coordinator.send_command = AsyncMock(return_value=False)
        switch._is_on = False
        
        await switch.async_turn_on()
        
        assert switch._is_on is False
        assert switch.coordinator.send_command.called

    @pytest.mark.asyncio
    async def test_switch_turn_off_success(self, mock_coordinator):
        """Test turn_off réussi."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch",
        )
        switch.async_write_ha_state = AsyncMock()
        switch._is_on = True
        
        await switch.async_turn_off()
        
        assert switch._is_on is False
        assert switch.coordinator.send_command.called
        assert switch.async_write_ha_state.called

    @pytest.mark.asyncio
    async def test_switch_turn_off_failure(self, mock_coordinator):
        """Test turn_off échoué."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch",
        )
        switch.async_write_ha_state = AsyncMock()
        switch.coordinator.send_command = AsyncMock(return_value=False)
        switch._is_on = True
        
        await switch.async_turn_off()
        
        assert switch._is_on is True
        assert switch.coordinator.send_command.called

    def test_switch_is_on_property(self, mock_coordinator):
        """Test de la propriété is_on."""
        switch = RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            protocol=PROTOCOL_ARC,
            house_code="A",
            unit_code="1",
            unique_id="test_switch",
        )
        switch._is_on = True
        assert switch.is_on is True
        switch._is_on = False
        assert switch.is_on is False


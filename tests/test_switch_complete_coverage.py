"""Tests complets pour switch.py pour augmenter la couverture."""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.rfxcom.switch import async_setup_entry, RFXCOMSwitch
from custom_components.rfxcom.const import (
    PROTOCOL_AC,
    PROTOCOL_ARC,
    CMD_ON,
    CMD_OFF,
    DOMAIN,
)


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {}
    entry.options = {
        "devices": [
            {
                "name": "Switch AC",
                "protocol": PROTOCOL_AC,
                "device_id": "02382C82",
                "unit_code": "2",
                "device_type": "switch",
            },
            {
                "name": "Switch ARC",
                "protocol": PROTOCOL_ARC,
                "house_code": "A",
                "unit_code": "1",
                "device_type": "switch",
            },
        ]
    }
    return entry


@pytest.fixture
def mock_coordinator():
    """Mock du coordinator."""
    coordinator = MagicMock()
    coordinator.send_command = AsyncMock(return_value=True)
    coordinator.get_discovered_devices = Mock(return_value=[])
    return coordinator


class TestSwitchSetup:
    """Tests pour async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_entry_with_devices(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration avec des appareils."""
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator
        
        # Mock device registry
        mock_dr = MagicMock()
        mock_device_entry = Mock()
        mock_dr.async_get_or_create.return_value = mock_device_entry
        
        with patch('custom_components.rfxcom.switch.dr.async_get', return_value=mock_dr):
            add_entities = Mock()
            
            await async_setup_entry(mock_hass, mock_entry, add_entities)
            
            # Vérifier que des entités ont été ajoutées
            assert add_entities.called
            assert len(add_entities.call_args[0][0]) == 2

    @pytest.mark.asyncio
    async def test_setup_entry_no_devices(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration sans appareils."""
        mock_entry.options = {"devices": []}
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator
        
        mock_dr = MagicMock()
        with patch('custom_components.rfxcom.switch.dr.async_get', return_value=mock_dr):
            add_entities = Mock()
            
            await async_setup_entry(mock_hass, mock_entry, add_entities)
            
            # Vérifier qu'aucune entité n'a été ajoutée
            assert add_entities.called
            assert len(add_entities.call_args[0][0]) == 0

    @pytest.mark.asyncio
    async def test_setup_entry_only_switch_type(self, mock_hass, mock_entry, mock_coordinator):
        """Test que seuls les appareils de type switch sont créés."""
        mock_entry.options = {
            "devices": [
                {
                    "name": "Switch AC",
                    "protocol": PROTOCOL_AC,
                    "device_id": "02382C82",
                    "unit_code": "2",
                    "device_type": "switch",
                },
                {
                    "name": "Cover ARC",
                    "protocol": PROTOCOL_ARC,
                    "house_code": "A",
                    "unit_code": "1",
                    "device_type": "cover",  # Pas un switch
                },
            ]
        }
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator
        
        mock_dr = MagicMock()
        mock_device_entry = Mock()
        mock_dr.async_get_or_create.return_value = mock_device_entry
        
        with patch('custom_components.rfxcom.switch.dr.async_get', return_value=mock_dr):
            add_entities = Mock()
            
            await async_setup_entry(mock_hass, mock_entry, add_entities)
            
            # Vérifier qu'une seule entité switch a été ajoutée
            assert add_entities.called
            assert len(add_entities.call_args[0][0]) == 1


class TestRFXCOMSwitch:
    """Tests pour RFXCOMSwitch."""

    @pytest.fixture
    def switch_ac(self, mock_coordinator):
        """Créer un switch AC."""
        # Utiliser le mock DeviceInfo depuis conftest
        from homeassistant.helpers.entity import DeviceInfo
        
        return RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Switch AC",
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            house_code=None,
            unit_code="2",
            unique_id="test_ac_switch",
            device_info=DeviceInfo(
                identifiers={(DOMAIN, "test_ac_switch")},
                name="Switch AC",
            ),
        )

    @pytest.fixture
    def switch_arc(self, mock_coordinator):
        """Créer un switch ARC."""
        # Utiliser le mock DeviceInfo depuis conftest
        from homeassistant.helpers.entity import DeviceInfo
        
        return RFXCOMSwitch(
            coordinator=mock_coordinator,
            name="Switch ARC",
            protocol=PROTOCOL_ARC,
            device_id=None,
            house_code="A",
            unit_code="1",
            unique_id="test_arc_switch",
            device_info=DeviceInfo(
                identifiers={(DOMAIN, "test_arc_switch")},
                name="Switch ARC",
            ),
        )

    def test_init_ac(self, switch_ac):
        """Test d'initialisation d'un switch AC."""
        assert switch_ac._attr_name == "Switch AC"
        assert switch_ac._protocol == PROTOCOL_AC
        assert switch_ac._device_id == "02382C82"
        assert switch_ac._unit_code == "2"
        assert switch_ac._is_on is False

    def test_init_arc(self, switch_arc):
        """Test d'initialisation d'un switch ARC."""
        assert switch_arc._attr_name == "Switch ARC"
        assert switch_arc._protocol == PROTOCOL_ARC
        assert switch_arc._house_code == "A"
        assert switch_arc._unit_code == "1"
        assert switch_arc._is_on is False

    def test_is_on_property(self, switch_ac):
        """Test de la propriété is_on."""
        switch_ac._is_on = True
        assert switch_ac.is_on is True
        
        switch_ac._is_on = False
        assert switch_ac.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_ac(self, switch_ac, mock_coordinator):
        """Test d'allumage d'un switch AC."""
        mock_coordinator.send_command = AsyncMock(return_value=True)
        switch_ac.async_write_ha_state = Mock()
        
        await switch_ac.async_turn_on()
        
        assert switch_ac._is_on is True
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            command=CMD_ON,
            house_code=None,
            unit_code="2",
        )

    @pytest.mark.asyncio
    async def test_turn_on_arc(self, switch_arc, mock_coordinator):
        """Test d'allumage d'un switch ARC."""
        mock_coordinator.send_command = AsyncMock(return_value=True)
        switch_arc.async_write_ha_state = Mock()
        
        await switch_arc.async_turn_on()
        
        assert switch_arc._is_on is True
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_ON,
            house_code="A",
            unit_code="1",
        )

    @pytest.mark.asyncio
    async def test_turn_off_ac(self, switch_ac, mock_coordinator):
        """Test d'extinction d'un switch AC."""
        switch_ac._is_on = True
        mock_coordinator.send_command = AsyncMock(return_value=True)
        switch_ac.async_write_ha_state = Mock()
        
        await switch_ac.async_turn_off()
        
        assert switch_ac._is_on is False
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            command=CMD_OFF,
            house_code=None,
            unit_code="2",
        )

    @pytest.mark.asyncio
    async def test_turn_off_arc(self, switch_arc, mock_coordinator):
        """Test d'extinction d'un switch ARC."""
        switch_arc._is_on = True
        mock_coordinator.send_command = AsyncMock(return_value=True)
        switch_arc.async_write_ha_state = Mock()
        
        await switch_arc.async_turn_off()
        
        assert switch_arc._is_on is False
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_OFF,
            house_code="A",
            unit_code="1",
        )

    @pytest.mark.asyncio
    async def test_turn_on_failure(self, switch_ac, mock_coordinator):
        """Test d'échec d'allumage."""
        mock_coordinator.send_command = AsyncMock(return_value=False)
        switch_ac.async_write_ha_state = Mock()
        
        await switch_ac.async_turn_on()
        
        # Selon l'implémentation, l'état n'est pas mis à jour en cas d'échec
        assert switch_ac._is_on is False

    @pytest.mark.asyncio
    async def test_turn_off_failure(self, switch_ac, mock_coordinator):
        """Test d'échec d'extinction."""
        switch_ac._is_on = True
        mock_coordinator.send_command = AsyncMock(return_value=False)
        switch_ac.async_write_ha_state = Mock()
        
        await switch_ac.async_turn_off()
        
        # Selon l'implémentation, l'état n'est pas mis à jour en cas d'échec
        assert switch_ac._is_on is True


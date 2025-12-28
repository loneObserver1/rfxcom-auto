"""Tests complets pour cover.py pour augmenter la couverture."""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.rfxcom.cover import async_setup_entry, RFXCOMCover
from custom_components.rfxcom.const import (
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
                "name": "Cover ARC",
                "protocol": PROTOCOL_ARC,
                "house_code": "A",
                "unit_code": "1",
                "device_type": "cover",
            },
        ]
    }
    return entry


@pytest.fixture
def mock_coordinator():
    """Mock du coordinator."""
    coordinator = MagicMock()
    coordinator.send_command = AsyncMock(return_value=True)
    return coordinator


class TestCoverSetup:
    """Tests pour async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_entry_with_cover(self, mock_hass, mock_entry, mock_coordinator):
        """Test de configuration avec un volet."""
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator
        
        # Mock device registry
        mock_dr = MagicMock()
        mock_device_entry = Mock()
        mock_dr.async_get_or_create.return_value = mock_device_entry
        
        with patch('custom_components.rfxcom.cover.dr.async_get', return_value=mock_dr):
            add_entities = Mock()
            
            await async_setup_entry(mock_hass, mock_entry, add_entities)
            
            # Vérifier qu'une entité a été ajoutée
            assert add_entities.called
            assert len(add_entities.call_args[0][0]) == 1

    @pytest.mark.asyncio
    async def test_setup_entry_only_cover_type(self, mock_hass, mock_entry, mock_coordinator):
        """Test que seuls les appareils de type cover sont créés."""
        mock_entry.options = {
            "devices": [
                {
                    "name": "Cover ARC",
                    "protocol": PROTOCOL_ARC,
                    "house_code": "A",
                    "unit_code": "1",
                    "device_type": "cover",
                },
                {
                    "name": "Switch ARC",
                    "protocol": PROTOCOL_ARC,
                    "house_code": "A",
                    "unit_code": "2",
                    "device_type": "switch",  # Pas un cover
                },
            ]
        }
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator
        
        mock_dr = MagicMock()
        mock_device_entry = Mock()
        mock_dr.async_get_or_create.return_value = mock_device_entry
        
        with patch('custom_components.rfxcom.cover.dr.async_get', return_value=mock_dr):
            add_entities = Mock()
            
            await async_setup_entry(mock_hass, mock_entry, add_entities)
            
            # Vérifier qu'une seule entité cover a été ajoutée
            assert add_entities.called
            assert len(add_entities.call_args[0][0]) == 1


class TestRFXCOMCover:
    """Tests pour RFXCOMCover."""

    @pytest.fixture
    def cover(self, mock_coordinator):
        """Créer un cover ARC."""
        # Utiliser le mock DeviceInfo depuis conftest
        from homeassistant.helpers.entity import DeviceInfo
        
        return RFXCOMCover(
            coordinator=mock_coordinator,
            name="Cover ARC",
            protocol=PROTOCOL_ARC,
            device_id=None,
            house_code="A",
            unit_code="1",
            unique_id="test_cover",
            device_info=DeviceInfo(
                identifiers={(DOMAIN, "test_cover")},
                name="Cover ARC",
            ),
        )

    def test_init(self, cover):
        """Test d'initialisation."""
        assert cover._attr_name == "Cover ARC"
        assert cover._protocol == PROTOCOL_ARC
        assert cover._house_code == "A"
        assert cover._unit_code == "1"
        assert cover.is_closed is None

    @pytest.mark.asyncio
    async def test_open_cover(self, cover, mock_coordinator):
        """Test d'ouverture du volet."""
        mock_coordinator.send_command = AsyncMock(return_value=True)
        
        await cover.async_open_cover()
        
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_ON,
            house_code="A",
            unit_code="1",
        )

    @pytest.mark.asyncio
    async def test_close_cover(self, cover, mock_coordinator):
        """Test de fermeture du volet."""
        mock_coordinator.send_command = AsyncMock(return_value=True)
        
        await cover.async_close_cover()
        
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_OFF,
            house_code="A",
            unit_code="1",
        )

    @pytest.mark.asyncio
    async def test_stop_cover(self, cover, mock_coordinator):
        """Test d'arrêt du volet."""
        mock_coordinator.send_command = AsyncMock(return_value=True)
        
        await cover.async_stop_cover()
        
        # Pour ARC, stop envoie ON à unit_code=3
        mock_coordinator.send_command.assert_called_once_with(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_ON,
            house_code="A",
            unit_code="3",
        )


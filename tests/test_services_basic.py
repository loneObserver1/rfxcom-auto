"""Tests basiques pour services.py."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()

# Mock voluptuous
sys.modules['voluptuous'] = MagicMock()
sys.modules['voluptuous'].vol = MagicMock()
sys.modules['voluptuous'].vol.Required = lambda x: x
sys.modules['voluptuous'].vol.Optional = lambda x, **kwargs: x
sys.modules['voluptuous'].vol.In = lambda x: x
sys.modules['voluptuous'].vol.Schema = lambda x: x

from custom_components.rfxcom.services import async_setup_services, async_unload_services
from custom_components.rfxcom.const import (
    DOMAIN,
    PROTOCOL_ARC,
    PROTOCOL_AC,
    PROTOCOL_TEMP_HUM,
    CONF_PROTOCOL,
    CONF_DEVICE_ID,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
)


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_register = AsyncMock()
    hass.services.async_remove = AsyncMock()
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.options = {"devices": []}
    return entry


class TestServices:
    """Tests pour les services RFXCOM."""

    @pytest.mark.asyncio
    async def test_setup_services(self, mock_hass):
        """Test de configuration des services."""
        await async_setup_services(mock_hass)
        
        # Vérifier que les services ont été enregistrés
        assert mock_hass.services.async_register.called
        # Vérifier qu'au moins 2 services sont enregistrés (pair_device et send_command)
        assert mock_hass.services.async_register.call_count >= 2
        registered_services = [call[0][1] for call in mock_hass.services.async_register.call_args_list]
        assert "pair_device" in registered_services
        assert "send_command" in registered_services

    @pytest.mark.asyncio
    async def test_unload_services(self, mock_hass):
        """Test de déchargement des services."""
        await async_unload_services(mock_hass)
        
        # Vérifier que les services ont été supprimés
        assert mock_hass.services.async_remove.called
        # Vérifier qu'au moins 2 services sont supprimés
        assert mock_hass.services.async_remove.call_count >= 2
        removed_services = [call[0][1] for call in mock_hass.services.async_remove.call_args_list]
        assert "pair_device" in removed_services
        assert "send_command" in removed_services


"""Tests basiques pour __init__.py."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()

# Mock ConfigEntryNotReady
class MockConfigEntryNotReady(Exception):
    pass

sys.modules['homeassistant.exceptions'].ConfigEntryNotReady = MockConfigEntryNotReady

# Mock Platform
class MockPlatform:
    SWITCH = "switch"
    COVER = "cover"
    SENSOR = "sensor"

sys.modules['homeassistant.const'].Platform = MockPlatform

from custom_components.rfxcom import (
    DOMAIN,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    async_update_options,
    _update_log_level,
)
from custom_components.rfxcom.coordinator import RFXCOMCoordinator


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock()
    hass.config_entries.async_reload = AsyncMock()
    
    # Mock device registry
    mock_device_registry = MagicMock()
    mock_device_registry.async_get_or_create = MagicMock()
    hass.helpers = MagicMock()
    hass.helpers.device_registry = MagicMock()
    hass.helpers.device_registry.async_get = MagicMock(return_value=mock_device_registry)
    
    return hass


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "connection_type": "usb",
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
    }
    entry.options = {
        "devices": [],
        "auto_registry": False,
    }
    return entry


class TestInit:
    """Tests pour __init__.py."""

    @pytest.mark.asyncio
    async def test_async_setup(self, mock_hass):
        """Test de configuration de l'intégration."""
        result = await async_setup(mock_hass, {})
        assert result is True

    # Note: test_async_setup_entry nécessite des mocks plus complexes pour RFXCOMCoordinator
    # et est testé indirectement via les tests d'intégration

    @pytest.mark.asyncio
    async def test_async_unload_entry(self, mock_hass, mock_entry):
        """Test de déchargement d'une entrée."""
        # Préparer les données
        mock_coord = MagicMock()
        mock_coord.async_shutdown = AsyncMock()
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: mock_coord}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        with patch('custom_components.rfxcom.async_unload_services', new_callable=AsyncMock):
            result = await async_unload_entry(mock_hass, mock_entry)
            assert result is True
            assert mock_coord.async_shutdown.called

    @pytest.mark.asyncio
    async def test_async_unload_entry_multiple_entries(self, mock_hass, mock_entry):
        """Test de déchargement avec plusieurs entrées."""
        mock_coord = MagicMock()
        mock_coord.async_shutdown = AsyncMock()
        mock_hass.data[DOMAIN] = {
            mock_entry.entry_id: mock_coord,
            "other_entry": MagicMock(),
        }
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        with patch('custom_components.rfxcom.async_unload_services', new_callable=AsyncMock) as mock_unload:
            result = await async_unload_entry(mock_hass, mock_entry)
            assert result is True
            # Ne doit pas décharger les services si d'autres entrées existent
            assert not mock_unload.called

    def test_update_log_level(self):
        """Test de mise à jour du niveau de log."""
        _update_log_level(True)
        _update_log_level(False)
        # Pas d'assertion, juste vérifier que ça ne plante pas

    @pytest.mark.asyncio
    async def test_async_update_options(self, mock_hass, mock_entry):
        """Test de mise à jour des options."""
        mock_entry.options = {"debug": True}
        await async_update_options(mock_hass, mock_entry)
        
        mock_entry.options = {"debug": False}
        await async_update_options(mock_hass, mock_entry)
        # Vérifier que ça ne plante pas


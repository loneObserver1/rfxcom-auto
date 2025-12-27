"""Tests pour __init__.py."""
import pytest
import logging
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.components.switch'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()

# Mock async_setup_services et async_unload_services avant l'import
async def mock_async_setup_services(hass):
    pass

async def mock_async_unload_services(hass):
    pass

sys.modules['custom_components.rfxcom.services'] = MagicMock()
sys.modules['custom_components.rfxcom.services'].async_setup_services = mock_async_setup_services
sys.modules['custom_components.rfxcom.services'].async_unload_services = mock_async_unload_services

# Mock log_handler
sys.modules['custom_components.rfxcom.log_handler'] = MagicMock()
sys.modules['custom_components.rfxcom.log_handler'].setup_log_handler = MagicMock(return_value=MagicMock())

from custom_components.rfxcom import async_setup, async_setup_entry, async_unload_entry, _update_log_level, async_update_options
from custom_components.rfxcom.const import DOMAIN, CONF_DEBUG, DEFAULT_DEBUG


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {"connection_type": "usb", "port": "/dev/ttyUSB0"}
    entry.options = {"devices": []}
    return entry


class TestInit:
    """Tests pour __init__.py."""

    @pytest.mark.asyncio
    async def test_async_setup(self, mock_hass):
        """Test de async_setup."""
        result = await async_setup(mock_hass, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, mock_hass, mock_entry):
        """Test de async_setup_entry avec succès."""
        # Mock du coordinateur
        coordinator = MagicMock()
        coordinator.async_setup = AsyncMock()
        
        # Mock RFXCOMCoordinator et async_forward_entry_setups
        with patch('custom_components.rfxcom.RFXCOMCoordinator', return_value=coordinator):
            mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
            result = await async_setup_entry(mock_hass, mock_entry)
            assert result is True
            assert DOMAIN in mock_hass.data
            assert mock_entry.entry_id in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_setup_entry_failure(self, mock_hass, mock_entry):
        """Test de async_setup_entry avec échec."""
        # Mock du coordinateur qui lève une exception
        coordinator = MagicMock()
        coordinator.async_setup = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('custom_components.rfxcom.RFXCOMCoordinator', return_value=coordinator):
            # Importer ConfigEntryNotReady depuis le vrai module
            import sys
            sys.modules['homeassistant.exceptions'].ConfigEntryNotReady = Exception
            ConfigEntryNotReady = Exception
            
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(mock_hass, mock_entry)

    @pytest.mark.asyncio
    async def test_async_unload_entry(self, mock_hass, mock_entry):
        """Test de async_unload_entry."""
        # Créer un coordinateur mock dans hass.data
        coordinator = MagicMock()
        coordinator.async_shutdown = AsyncMock()
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: coordinator}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        result = await async_unload_entry(mock_hass, mock_entry)
        
        assert result is True
        assert mock_entry.entry_id not in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_unload_entry_multiple_entries(self, mock_hass, mock_entry):
        """Test de async_unload_entry avec plusieurs entrées."""
        # Créer deux coordinateurs
        coordinator1 = MagicMock()
        coordinator1.async_shutdown = AsyncMock()
        coordinator2 = MagicMock()
        coordinator2.async_shutdown = AsyncMock()
        
        mock_hass.data[DOMAIN] = {
            "entry1": coordinator1,
            "entry2": coordinator2,
        }
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        mock_entry.entry_id = "entry1"
        
        result = await async_unload_entry(mock_hass, mock_entry)
        
        assert result is True
        assert "entry1" not in mock_hass.data[DOMAIN]
        assert "entry2" in mock_hass.data[DOMAIN]  # L'autre entrée doit rester

    def test_update_log_level_debug(self):
        """Test de la mise à jour du niveau de log en mode debug."""
        _update_log_level(True)
        logger = logging.getLogger("custom_components.rfxcom")
        assert logger.level == logging.DEBUG

    def test_update_log_level_info(self):
        """Test de la mise à jour du niveau de log en mode info."""
        _update_log_level(False)
        logger = logging.getLogger("custom_components.rfxcom")
        assert logger.level == logging.INFO

    @pytest.mark.asyncio
    async def test_async_update_options(self):
        """Test de la mise à jour des options."""
        hass = MagicMock()
        entry = Mock()
        entry.options = {CONF_DEBUG: True}
        
        await async_update_options(hass, entry)
        
        # Vérifier que le niveau de log a été mis à jour
        logger = logging.getLogger("custom_components.rfxcom")
        assert logger.level == logging.DEBUG


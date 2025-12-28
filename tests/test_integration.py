"""Tests d'intégration pour RFXCOM."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.rfxcom import async_setup_entry, async_unload_entry
from custom_components.rfxcom.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_and_unload(hass: HomeAssistant):
    """Test de configuration et déchargement de l'intégration."""
    entry = Mock(spec=ConfigEntry)
    entry.data = {
        "connection_type": "usb",
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
    }
    entry.entry_id = "test_entry"
    entry.options = {"devices": []}
    
    with patch("custom_components.rfxcom.coordinator.serial.Serial") as mock_serial:
        mock_serial.return_value.is_open = True
        
        # Test setup
        result = await async_setup_entry(hass, entry)
        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        
        # Test unload
        result = await async_unload_entry(hass, entry)
        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]



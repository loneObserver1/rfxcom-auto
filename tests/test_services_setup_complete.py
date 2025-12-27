"""Tests complets pour services.py."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock Home Assistant
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()

# Mock voluptuous
sys.modules['voluptuous'] = MagicMock()
sys.modules['voluptuous'].vol = MagicMock()
sys.modules['voluptuous'].vol.Required = lambda x, **kwargs: x
sys.modules['voluptuous'].vol.Optional = lambda x, **kwargs: x
sys.modules['voluptuous'].vol.In = lambda x: x
sys.modules['voluptuous'].vol.Schema = lambda x: x

from custom_components.rfxcom.services import async_setup_services, async_unload_services
from custom_components.rfxcom.const import (
    DOMAIN,
    PROTOCOL_AC,
    PROTOCOL_ARC,
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
    hass.config_entries = MagicMock()
    hass.services = MagicMock()
    hass.services.async_register = AsyncMock()
    hass.services.async_remove = AsyncMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.options = {"devices": []}
    entry.async_update_entry = AsyncMock()
    return entry


@pytest.fixture
def mock_hass_with_reload(mock_hass):
    """Mock de Home Assistant avec async_reload."""
    mock_hass.config_entries.async_reload = AsyncMock()
    return mock_hass


class TestServicesComplete:
    """Tests complets pour services.py."""

    @pytest.mark.asyncio
    async def test_setup_services(self, mock_hass):
        """Test de configuration des services."""
        await async_setup_services(mock_hass)
        
        # Vérifier que le service a été enregistré
        assert mock_hass.services.async_register.called
        call_args = mock_hass.services.async_register.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == "pair_device"

    @pytest.mark.asyncio
    async def test_unload_services(self, mock_hass):
        """Test de déchargement des services."""
        await async_unload_services(mock_hass)
        
        # Vérifier que le service a été retiré
        assert mock_hass.services.async_remove.called

    @pytest.mark.asyncio
    async def test_pair_device_arc_success(self, mock_hass_with_reload, mock_config_entry):
        """Test d'appairage réussi d'un appareil ARC."""
        mock_hass_with_reload.config_entries.async_entries.return_value = [mock_config_entry]
        
        # Récupérer la fonction de service
        await async_setup_services(mock_hass_with_reload)
        service_func = mock_hass_with_reload.services.async_register.call_args[0][2]
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            "name": "Test ARC",
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        await service_func(call)
        
        # Vérifier que l'appareil a été ajouté
        devices = mock_config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0]["name"] == "Test ARC"
        assert devices[0][CONF_PROTOCOL] == PROTOCOL_ARC

    @pytest.mark.asyncio
    async def test_pair_device_ac_success(self, mock_hass_with_reload, mock_config_entry):
        """Test d'appairage réussi d'un appareil AC."""
        mock_hass_with_reload.config_entries.async_entries.return_value = [mock_config_entry]
        
        await async_setup_services(mock_hass_with_reload)
        service_func = mock_hass_with_reload.services.async_register.call_args[0][2]
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_AC,
            "name": "Test AC",
            CONF_DEVICE_ID: "01020304",
        }
        
        await service_func(call)
        
        devices = mock_config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0][CONF_PROTOCOL] == PROTOCOL_AC
        assert devices[0][CONF_DEVICE_ID] == "01020304"

    @pytest.mark.asyncio
    async def test_pair_device_temp_hum_success(self, mock_hass_with_reload, mock_config_entry):
        """Test d'appairage réussi d'un capteur TEMP_HUM."""
        mock_hass_with_reload.config_entries.async_entries.return_value = [mock_config_entry]
        
        await async_setup_services(mock_hass_with_reload)
        service_func = mock_hass_with_reload.services.async_register.call_args[0][2]
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
            "name": "Test Sensor",
            CONF_DEVICE_ID: "26627",
        }
        
        await service_func(call)
        
        devices = mock_config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0][CONF_PROTOCOL] == PROTOCOL_TEMP_HUM
        assert "sensor_data" in devices[0]


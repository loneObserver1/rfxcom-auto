"""Tests pour les services RFXCOM."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys

# Mock Home Assistant
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()

from custom_components.rfxcom.services import async_setup_services, pair_device
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
    return hass


@pytest.fixture
def mock_config_entry():
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
        
        # Vérifier que le service a été enregistré
        assert mock_hass.services.async_register.called

    @pytest.mark.asyncio
    async def test_pair_device_arc(self, mock_hass, mock_config_entry):
        """Test d'appairage d'un appareil ARC."""
        mock_hass.config_entries.async_entries.return_value = [mock_config_entry]
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            "name": "Test ARC",
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        # Le service pair_device est défini dans async_setup_services
        # On doit l'appeler via le service
        await async_setup_services(mock_hass)
        
        # Récupérer la fonction enregistrée
        registered_call = mock_hass.services.async_register.call_args
        if registered_call:
            service_func = registered_call[0][2]  # La fonction callback
            await service_func(call)
            
            # Vérifier que l'appareil a été ajouté
            devices = mock_config_entry.options.get("devices", [])
            assert len(devices) == 1
            assert devices[0]["name"] == "Test ARC"
            assert devices[0][CONF_PROTOCOL] == PROTOCOL_ARC

    @pytest.mark.asyncio
    async def test_pair_device_ac(self, mock_hass, mock_config_entry):
        """Test d'appairage d'un appareil AC."""
        mock_hass.config_entries.async_entries.return_value = [mock_config_entry]
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_AC,
            "name": "Test AC",
            CONF_DEVICE_ID: "01020304",
        }
        
        await async_setup_services(mock_hass)
        
        registered_call = mock_hass.services.async_register.call_args
        if registered_call:
            service_func = registered_call[0][2]
            await service_func(call)
            
            devices = mock_config_entry.options.get("devices", [])
            assert len(devices) == 1
            assert devices[0]["name"] == "Test AC"
            assert devices[0][CONF_PROTOCOL] == PROTOCOL_AC
            assert devices[0][CONF_DEVICE_ID] == "01020304"

    @pytest.mark.asyncio
    async def test_pair_device_temp_hum(self, mock_hass, mock_config_entry):
        """Test d'appairage d'un capteur TEMP_HUM."""
        mock_hass.config_entries.async_entries.return_value = [mock_config_entry]
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
            "name": "Test Sensor",
            CONF_DEVICE_ID: "26627",
        }
        
        await async_setup_services(mock_hass)
        
        registered_call = mock_hass.services.async_register.call_args
        if registered_call:
            service_func = registered_call[0][2]
            await service_func(call)
            
            devices = mock_config_entry.options.get("devices", [])
            assert len(devices) == 1
            assert devices[0]["name"] == "Test Sensor"
            assert devices[0][CONF_PROTOCOL] == PROTOCOL_TEMP_HUM

    @pytest.mark.asyncio
    async def test_pair_device_no_entry(self, mock_hass):
        """Test d'appairage sans entrée de configuration."""
        mock_hass.config_entries.async_entries.return_value = []
        
        call = Mock()
        call.data = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            "name": "Test",
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        await async_setup_services(mock_hass)
        
        registered_call = mock_hass.services.async_register.call_args
        if registered_call:
            service_func = registered_call[0][2]
            # Ne devrait pas lever d'exception, juste logger une erreur
            await service_func(call)


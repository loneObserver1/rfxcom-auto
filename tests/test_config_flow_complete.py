"""Tests complets pour config_flow."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys

# Mock Home Assistant avant les imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.data_entry_flow'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()

# Mock voluptuous
sys.modules['voluptuous'] = MagicMock()
sys.modules['voluptuous'].vol = MagicMock()
sys.modules['voluptuous'].vol.Required = lambda x, **kwargs: x
sys.modules['voluptuous'].vol.Optional = lambda x, **kwargs: x
sys.modules['voluptuous'].vol.In = lambda x: x
sys.modules['voluptuous'].vol.All = lambda *args: args[0]
sys.modules['voluptuous'].vol.Coerce = lambda x: x
sys.modules['voluptuous'].vol.Range = lambda **kwargs: lambda x: x
sys.modules['voluptuous'].vol.Schema = lambda x: x

# Mock serial.tools.list_ports
sys.modules['serial'] = MagicMock()
sys.modules['serial.tools'] = MagicMock()
sys.modules['serial.tools.list_ports'] = MagicMock()

from custom_components.rfxcom.config_flow import RFXCOMConfigFlow, RFXCOMOptionsFlowHandler
from custom_components.rfxcom.const import (
    PROTOCOL_AC,
    PROTOCOL_ARC,
    PROTOCOL_TEMP_HUM,
    CONF_PORT,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_NETWORK_PORT,
    CONF_AUTO_REGISTRY,
    DEFAULT_AUTO_REGISTRY,
)


@pytest.fixture
def flow():
    """Créer un flux de configuration."""
    flow = RFXCOMConfigFlow()
    flow.hass = MagicMock()
    return flow


@pytest.fixture
def config_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {"connection_type": "usb", "port": "/dev/ttyUSB0"}
    entry.options = {"devices": []}
    return entry


@pytest.fixture
def options_flow(config_entry):
    """Créer un flux d'options."""
    flow = RFXCOMOptionsFlowHandler(config_entry)
    flow.hass = MagicMock()
    return flow


class TestConfigFlow:
    """Tests pour RFXCOMConfigFlow."""

    @pytest.mark.asyncio
    async def test_user_step_show_form(self, flow):
        """Test d'affichage du formulaire utilisateur."""
        result = await flow.async_step_user()
        
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_usb(self, flow):
        """Test de sélection USB."""
        user_input = {
            CONF_CONNECTION_TYPE: "usb",
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == "form"
        assert result["step_id"] == "usb"

    @pytest.mark.asyncio
    async def test_user_step_network(self, flow):
        """Test de sélection réseau."""
        user_input = {
            CONF_CONNECTION_TYPE: "network",
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == "form"
        assert result["step_id"] == "network"

    @pytest.mark.asyncio
    async def test_usb_step_create_entry(self, flow):
        """Test de création d'entrée USB."""
        # Mock des ports série
        mock_port = Mock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "USB Serial"
        
        with patch('serial.tools.list_ports.comports', return_value=[mock_port]):
            user_input = {
                CONF_PORT: "/dev/ttyUSB0",
                CONF_BAUDRATE: 38400,
                CONF_AUTO_REGISTRY: False,
            }
            
            result = await flow.async_step_usb(user_input)
            
            assert result["type"] == "create_entry"
            assert result["data"][CONF_PORT] == "/dev/ttyUSB0"
            assert result["data"][CONF_BAUDRATE] == 38400

    @pytest.mark.asyncio
    async def test_network_step_create_entry(self, flow):
        """Test de création d'entrée réseau."""
        user_input = {
            CONF_HOST: "192.168.1.100",
            CONF_NETWORK_PORT: 10001,
            CONF_AUTO_REGISTRY: True,
        }
        
        result = await flow.async_step_network(user_input)
        
        assert result["type"] == "create_entry"
        assert result["data"][CONF_HOST] == "192.168.1.100"
        assert result["data"][CONF_NETWORK_PORT] == 10001
        assert result["options"][CONF_AUTO_REGISTRY] is True

    @pytest.mark.asyncio
    async def test_usb_manual_step(self, flow):
        """Test de saisie manuelle USB."""
        # Simuler que l'utilisateur a choisi "Saisie manuelle"
        user_input = {
            CONF_PORT: "manual",
            CONF_BAUDRATE: 38400,
        }
        
        result = await flow.async_step_usb(user_input)
        
        # Devrait rediriger vers usb_manual
        assert result["type"] == "form"
        assert result["step_id"] == "usb_manual"

    @pytest.mark.asyncio
    async def test_usb_manual_create_entry(self, flow):
        """Test de création d'entrée avec saisie manuelle."""
        user_input = {
            CONF_PORT: "/dev/ttyUSB1",
            CONF_BAUDRATE: 115200,
            CONF_AUTO_REGISTRY: True,
        }
        
        result = await flow.async_step_usb_manual(user_input)
        
        assert result["type"] == "create_entry"
        assert result["data"][CONF_PORT] == "/dev/ttyUSB1"


class TestOptionsFlow:
    """Tests pour RFXCOMOptionsFlowHandler."""

    @pytest.mark.asyncio
    async def test_init_step(self, options_flow, config_entry):
        """Test de l'étape d'initialisation."""
        result = await options_flow.async_step_init()
        
        assert result["type"] == "menu"

    @pytest.mark.asyncio
    async def test_add_device_arc(self, options_flow, config_entry):
        """Test d'ajout d'un appareil ARC."""
        user_input = {
            "name": "Test Switch",
            "protocol": PROTOCOL_ARC,
            "house_code": "A",
            "unit_code": "1",
        }
        
        result = await options_flow.async_step_add_device(user_input)
        
        assert result["type"] == "create_entry"
        devices = config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0]["name"] == "Test Switch"

    @pytest.mark.asyncio
    async def test_add_device_ac(self, options_flow, config_entry):
        """Test d'ajout d'un appareil AC."""
        user_input = {
            "name": "Test AC",
            "protocol": PROTOCOL_AC,
            "device_id": "01020304",
        }
        
        result = await options_flow.async_step_add_device(user_input)
        
        assert result["type"] == "create_entry"
        devices = config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0]["name"] == "Test AC"
        assert devices[0]["protocol"] == PROTOCOL_AC

    @pytest.mark.asyncio
    async def test_add_device_temp_hum(self, options_flow, config_entry):
        """Test d'ajout d'un capteur TEMP_HUM."""
        user_input = {
            "name": "Test Sensor",
            "protocol": PROTOCOL_TEMP_HUM,
            "device_id": "26627",
        }
        
        result = await options_flow.async_step_add_device(user_input)
        
        assert result["type"] == "create_entry"
        devices = config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0]["protocol"] == PROTOCOL_TEMP_HUM

    @pytest.mark.asyncio
    async def test_add_device_error_missing_fields(self, options_flow):
        """Test d'erreur si des champs sont manquants."""
        user_input = {
            "name": "Test",
            "protocol": PROTOCOL_ARC,
            # house_code et unit_code manquants
        }
        
        result = await options_flow.async_step_add_device(user_input)
        
        assert result["type"] == "form"
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_edit_device(self, options_flow, config_entry):
        """Test de modification d'un appareil."""
        # Ajouter un appareil d'abord
        config_entry.options["devices"] = [
            {
                "name": "Test Switch",
                "protocol": PROTOCOL_ARC,
                "house_code": "A",
                "unit_code": "1",
            }
        ]
        
        user_input = {
            "name": "Test Switch Updated",
            "protocol": PROTOCOL_ARC,
            "house_code": "B",
            "unit_code": "2",
        }
        
        result = await options_flow.async_step_edit_device(0, user_input)
        
        assert result["type"] == "create_entry"
        devices = config_entry.options.get("devices", [])
        assert devices[0]["name"] == "Test Switch Updated"
        assert devices[0]["house_code"] == "B"

    @pytest.mark.asyncio
    async def test_delete_device(self, options_flow, config_entry):
        """Test de suppression d'un appareil."""
        config_entry.options["devices"] = [
            {
                "name": "Test Switch",
                "protocol": PROTOCOL_ARC,
                "house_code": "A",
                "unit_code": "1",
            }
        ]
        
        result = await options_flow.async_step_delete_device(0, {})
        
        assert result["type"] == "create_entry"
        devices = config_entry.options.get("devices", [])
        assert len(devices) == 0

    @pytest.mark.asyncio
    async def test_auto_registry_step(self, options_flow, config_entry):
        """Test de configuration de l'auto-registry."""
        user_input = {
            CONF_AUTO_REGISTRY: True,
        }
        
        result = await options_flow.async_step_auto_registry(user_input)
        
        assert result["type"] == "create_entry"
        assert config_entry.options[CONF_AUTO_REGISTRY] is True


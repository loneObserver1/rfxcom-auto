"""Tests pour le flux de configuration."""
import pytest
from unittest.mock import Mock, patch
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rfxcom.config_flow import RFXCOMConfigFlow, RFXCOMOptionsFlowHandler
from custom_components.rfxcom.const import (
    PROTOCOL_AC,
    PROTOCOL_ARC,
    CONF_PORT,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_NETWORK_PORT,
)


@pytest.fixture
def flow():
    """Créer un flux de configuration."""
    return RFXCOMConfigFlow()


class TestRFXCOMConfigFlow:
    """Tests pour RFXCOMConfigFlow."""

    @pytest.mark.asyncio
    async def test_user_step_show_form(self, flow):
        """Test d'affichage du formulaire utilisateur."""
        result = await flow.async_step_user()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_create_entry_usb(self, flow):
        """Test de création d'entrée USB."""
        user_input = {
            CONF_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 38400,
            CONF_CONNECTION_TYPE: "usb",
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PORT] == "/dev/ttyUSB0"
        assert result["data"][CONF_BAUDRATE] == 38400

    @pytest.mark.asyncio
    async def test_user_step_create_entry_network(self, flow):
        """Test de création d'entrée réseau."""
        user_input = {
            CONF_CONNECTION_TYPE: "network",
            CONF_HOST: "192.168.1.100",
            CONF_NETWORK_PORT: 10001,
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_HOST] == "192.168.1.100"
        assert result["data"][CONF_NETWORK_PORT] == 10001

    @pytest.mark.asyncio
    async def test_user_step_error_missing_port(self, flow):
        """Test d'erreur si le port est manquant."""
        user_input = {
            CONF_PORT: "",
            CONF_BAUDRATE: 38400,
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert "errors" in result


class TestRFXCOMOptionsFlowHandler:
    """Tests pour RFXCOMOptionsFlowHandler."""

    @pytest.fixture
    def config_entry(self):
        """Créer une entrée de configuration mock."""
        entry = Mock()
        entry.options = {"devices": []}
        return entry

    @pytest.fixture
    def options_flow(self, config_entry):
        """Créer un flux d'options."""
        return RFXCOMOptionsFlowHandler(config_entry)

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
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert len(config_entry.options.get("devices", [])) == 1

    @pytest.mark.asyncio
    async def test_add_device_ac(self, options_flow, config_entry):
        """Test d'ajout d'un appareil AC."""
        user_input = {
            "name": "Test AC",
            "protocol": PROTOCOL_AC,
            "device_id": "0102030405060708",
        }
        
        result = await options_flow.async_step_add_device(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        devices = config_entry.options.get("devices", [])
        assert len(devices) == 1
        assert devices[0]["name"] == "Test AC"

    @pytest.mark.asyncio
    async def test_add_device_error_missing_fields(self, options_flow):
        """Test d'erreur si des champs sont manquants."""
        user_input = {
            "name": "Test",
            "protocol": PROTOCOL_ARC,
            # house_code et unit_code manquants
        }
        
        result = await options_flow.async_step_add_device(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert "errors" in result



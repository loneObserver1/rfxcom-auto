"""Tests pour l'envoi de commandes."""
import pytest
import sys
import os
import importlib.util
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Charger const directement
const_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'const.py')
spec = importlib.util.spec_from_file_location("const", const_path)
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)

# Mock Home Assistant
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()

# Mock DataUpdateCoordinator
class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_interval):
        pass

sys.modules['homeassistant.helpers.update_coordinator'].DataUpdateCoordinator = MockDataUpdateCoordinator

# Mock serial et socket
sys.modules['serial'] = MagicMock()
sys.modules['socket'] = MagicMock()

# Créer un package mock pour les imports relatifs
sys.modules['custom_components'] = MagicMock()
sys.modules['custom_components.rfxcom'] = MagicMock()
sys.modules['custom_components.rfxcom.const'] = const

# Charger coordinator
coordinator_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'coordinator.py')
spec = importlib.util.spec_from_file_location("custom_components.rfxcom.coordinator", coordinator_path)
coordinator_module = importlib.util.module_from_spec(spec)
sys.modules['custom_components.rfxcom.coordinator'] = coordinator_module

with patch('serial.Serial'), patch('socket.socket'):
    spec.loader.exec_module(coordinator_module)

RFXCOMCoordinator = coordinator_module.RFXCOMCoordinator


class MockHass:
    def __init__(self):
        self.async_add_executor_job = AsyncMock()


class MockEntry:
    def __init__(self, data, options=None):
        self.data = data
        self.options = options or {}
        self.entry_id = "test"


class MockSerialPort:
    def __init__(self):
        self.is_open = True
        self.write = Mock()
        self.flush = Mock()


class MockSocket:
    def __init__(self):
        self.sendall = Mock()


class TestSendCommand:
    """Tests pour l'envoi de commandes."""

    @pytest.mark.asyncio
    async def test_send_command_arc_usb(self):
        """Test d'envoi de commande ARC via USB."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Mock du port série avec async_setup
        mock_port = MockSerialPort()
        coordinator.serial_port = mock_port
        
        # Simuler que async_setup a été appelé
        coordinator._receive_task = None
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_ARC,
            device_id="",
            command=const.CMD_ON,
            house_code="A",
            unit_code="1",
        )
        
        assert result is True
        # Vérifier que write a été appelé via async_add_executor_job
        assert hass.async_add_executor_job.called

    @pytest.mark.asyncio
    async def test_send_command_ac_network(self):
        """Test d'envoi de commande AC via réseau."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_NETWORK})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Mock de la socket avec async_setup
        mock_socket = MockSocket()
        coordinator.socket = mock_socket
        coordinator._receive_task = None
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_AC,
            device_id="01020304",
            command=const.CMD_ON,
        )
        
        assert result is True
        # Vérifier que sendall a été appelé via async_add_executor_job
        assert hass.async_add_executor_job.called

    @pytest.mark.asyncio
    async def test_send_command_unsupported_protocol(self):
        """Test d'envoi avec un protocole non supporté."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        result = await coordinator.send_command(
            protocol="UNKNOWN_PROTOCOL",
            device_id="",
            command=const.CMD_ON,
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_port_closed(self):
        """Test d'envoi avec port série fermé."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        mock_port = MockSerialPort()
        mock_port.is_open = False
        coordinator.serial_port = mock_port
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_ARC,
            device_id="",
            command=const.CMD_ON,
            house_code="A",
            unit_code="1",
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_lighting3(self):
        """Test d'envoi de commande Lighting3."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        mock_port = MockSerialPort()
        coordinator.serial_port = mock_port
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_IKEA_KOPPLA,
            device_id="0102",
            command=const.CMD_ON,
            unit_code="1",
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_command_lighting4(self):
        """Test d'envoi de commande Lighting4."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        mock_port = MockSerialPort()
        coordinator.serial_port = mock_port
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_PT2262,
            device_id="010203",
            command=const.CMD_ON,
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_command_lighting5(self):
        """Test d'envoi de commande Lighting5."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        mock_port = MockSerialPort()
        coordinator.serial_port = mock_port
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_LIGHTWAVERF,
            device_id="010203",
            command=const.CMD_ON,
            unit_code="0",
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_command_lighting6(self):
        """Test d'envoi de commande Lighting6."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        mock_port = MockSerialPort()
        coordinator.serial_port = mock_port
        
        result = await coordinator.send_command(
            protocol=const.PROTOCOL_BLYSS,
            device_id="0102",
            command=const.CMD_ON,
        )
        
        assert result is True


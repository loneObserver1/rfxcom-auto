"""Tests pour le parsing des paquets RFXCOM."""
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

# Mock serial
sys.modules['serial'] = MagicMock()

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


class TestPacketParsing:
    """Tests pour le parsing des paquets RFXCOM."""

    def test_parse_lighting1_arc_packet(self):
        """Test de parsing d'un paquet Lighting1 ARC."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet ARC: 07 10 01 62 41 01 01 00
        # 07=longueur, 10=Lighting1, 01=ARC, 62=seq, 41=A, 01=unit, 01=ON, 00=signal
        packet = bytes([0x07, 0x10, 0x01, 0x62, 0x41, 0x01, 0x01, 0x00])
        
        device_info = coordinator._parse_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_ARC
        assert device_info[const.CONF_HOUSE_CODE] == "A"
        assert device_info[const.CONF_UNIT_CODE] == "1"
        assert device_info["command"] == const.CMD_ON

    def test_parse_lighting2_ac_packet(self):
        """Test de parsing d'un paquet Lighting2 AC."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet AC: 0B 11 00 01 01 02 03 04 00 01 0F 00
        # 0B=longueur, 11=Lighting2, 00=AC, 01=seq, 01020304=ID, 00=unit, 01=ON, 0F=level, 00=signal
        packet = bytes([0x0B, 0x11, 0x00, 0x01, 0x01, 0x02, 0x03, 0x04, 0x00, 0x01, 0x0F, 0x00])
        
        device_info = coordinator._parse_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_AC
        assert device_info[const.CONF_DEVICE_ID] == "01020304"
        assert device_info["command"] == const.CMD_ON

    def test_parse_temp_hum_packet(self):
        """Test de parsing d'un paquet TEMP_HUM."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet TEMP_HUM: 0A 52 0D 35 68 03 00 D4 27 02 89
        # 0A=longueur, 52=TEMP_HUM, 0D=TH13, 35=seq, 6803=ID, 00D4=temp, 27=hum, 02=status, 89=signal/battery
        packet = bytes([0x0A, 0x52, 0x0D, 0x35, 0x68, 0x03, 0x00, 0xD4, 0x27, 0x02, 0x89])
        
        device_info = coordinator._parse_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_TEMP_HUM
        assert device_info[const.CONF_DEVICE_ID] == "26627"  # 0x6803 = 26627
        assert "temperature" in device_info
        assert "humidity" in device_info

    def test_parse_packet_too_short(self):
        """Test avec un paquet trop court."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        packet = bytes([0x03, 0x10, 0x01])  # Trop court
        
        device_info = coordinator._parse_packet(packet)
        
        assert device_info is None

    def test_parse_lighting1_x10_packet(self):
        """Test de parsing d'un paquet Lighting1 X10."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet X10: 07 10 00 62 41 01 01 00
        packet = bytes([0x07, 0x10, 0x00, 0x62, 0x41, 0x01, 0x01, 0x00])
        
        device_info = coordinator._parse_lighting1_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_X10

    def test_parse_lighting3_packet(self):
        """Test de parsing d'un paquet Lighting3."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet Lighting3: 08 12 01 01 02 00 01 01 00
        packet = bytes([0x08, 0x12, 0x01, 0x01, 0x02, 0x00, 0x01, 0x01, 0x00])
        
        device_info = coordinator._parse_lighting3_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_IKEA_KOPPLA

    def test_parse_lighting4_packet(self):
        """Test de parsing d'un paquet Lighting4."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet Lighting4: 07 13 01 01 02 03 01 00
        packet = bytes([0x07, 0x13, 0x01, 0x01, 0x02, 0x03, 0x01, 0x00])
        
        device_info = coordinator._parse_lighting4_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_PT2262

    def test_parse_lighting5_packet(self):
        """Test de parsing d'un paquet Lighting5."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet Lighting5: 0A 14 00 01 01 02 03 00 01 0F 00
        packet = bytes([0x0A, 0x14, 0x00, 0x01, 0x01, 0x02, 0x03, 0x00, 0x01, 0x0F, 0x00])
        
        device_info = coordinator._parse_lighting5_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_LIGHTWAVERF

    def test_parse_lighting6_packet(self):
        """Test de parsing d'un paquet Lighting6."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        # Paquet Lighting6: 08 15 01 01 02 00 00 01 00
        packet = bytes([0x08, 0x15, 0x01, 0x01, 0x02, 0x00, 0x00, 0x01, 0x00])
        
        device_info = coordinator._parse_lighting6_packet(packet)
        
        assert device_info is not None
        assert device_info[const.CONF_PROTOCOL] == const.PROTOCOL_BLYSS



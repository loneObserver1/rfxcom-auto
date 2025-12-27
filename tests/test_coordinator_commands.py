"""Tests pour la construction de commandes RFXCOM."""
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


class TestCommandBuilding:
    """Tests pour la construction de commandes."""

    def test_build_lighting3_command(self):
        """Test de construction d'une commande Lighting3."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        cmd = coordinator._build_lighting3_command(
            const.PROTOCOL_IKEA_KOPPLA, "0102", "1", const.CMD_ON
        )
        
        assert len(cmd) == 9  # 08 12 [seq] 01 02 [group] [unit] [cmd] 00
        assert cmd[0] == 0x08  # Longueur
        assert cmd[1] == const.PACKET_TYPE_LIGHTING3  # 0x12
        assert cmd[3] == 0x01  # ID byte 1 (après seq à index 2)
        assert cmd[4] == 0x02  # ID byte 2
        assert cmd[7] == 0x01  # ON command

    def test_build_lighting4_command(self):
        """Test de construction d'une commande Lighting4."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        cmd = coordinator._build_lighting4_command(
            const.PROTOCOL_PT2262, "010203", const.CMD_ON
        )
        
        assert len(cmd) == 8  # 07 13 [seq] 01 02 03 [cmd] 00
        assert cmd[0] == 0x07  # Longueur
        assert cmd[1] == const.PACKET_TYPE_LIGHTING4  # 0x13
        assert cmd[3] == 0x01  # ID byte 1
        assert cmd[4] == 0x02  # ID byte 2
        assert cmd[5] == 0x03  # ID byte 3
        assert cmd[6] == 0x01  # ON command

    def test_build_lighting5_command(self):
        """Test de construction d'une commande Lighting5."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        cmd = coordinator._build_lighting5_command(
            const.PROTOCOL_LIGHTWAVERF, const.SUBTYPE_LIGHTWAVERF, "010203", "0", const.CMD_ON
        )
        
        assert len(cmd) == 11  # 0A 14 [subtype] [seq] [id(3)] [unit] [cmd] [level] 00
        assert cmd[0] == 0x0A  # Longueur
        assert cmd[1] == const.PACKET_TYPE_LIGHTING5  # 0x14
        assert cmd[2] == const.SUBTYPE_LIGHTWAVERF
        assert cmd[4] == 0x01  # ID byte 1
        assert cmd[5] == 0x02  # ID byte 2
        assert cmd[6] == 0x03  # ID byte 3
        assert cmd[8] == 0x01  # ON command
        assert cmd[9] == 0x0F  # Level 100%

    def test_build_lighting6_command(self):
        """Test de construction d'une commande Lighting6."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        cmd = coordinator._build_lighting6_command(
            const.PROTOCOL_BLYSS, "0102", const.CMD_ON
        )
        
        assert len(cmd) == 9  # 08 15 [seq] 01 02 [group] [unit] [cmd] 00
        assert cmd[0] == 0x08  # Longueur
        assert cmd[1] == const.PACKET_TYPE_LIGHTING6  # 0x15
        assert cmd[3] == 0x01  # ID byte 1
        assert cmd[4] == 0x02  # ID byte 2
        assert cmd[7] == 0x01  # ON command

    def test_build_lighting1_x10_command(self):
        """Test de construction d'une commande Lighting1 X10."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        cmd = coordinator._build_lighting1_command(
            const.PROTOCOL_X10, const.SUBTYPE_X10, "A", "1", const.CMD_ON
        )
        
        assert len(cmd) == 8
        assert cmd[0] == 0x07  # Longueur
        assert cmd[1] == const.PACKET_TYPE_LIGHTING1
        assert cmd[2] == const.SUBTYPE_X10
        assert cmd[4] == ord("A")  # House code
        assert cmd[5] == 1  # Unit code
        assert cmd[6] == 0x01  # ON

    def test_build_lighting2_homeeasy_command(self):
        """Test de construction d'une commande Lighting2 HomeEasy."""
        hass = MockHass()
        entry = MockEntry({"connection_type": const.CONNECTION_TYPE_USB})
        coordinator = RFXCOMCoordinator(hass, entry)
        
        cmd = coordinator._build_lighting2_command(
            const.PROTOCOL_HOMEEASY_EU, const.SUBTYPE_HOMEEASY_EU, "01020304", const.CMD_ON
        )
        
        assert len(cmd) == 12
        assert cmd[1] == const.PACKET_TYPE_LIGHTING2
        assert cmd[2] == const.SUBTYPE_HOMEEASY_EU
        assert cmd[4:8] == bytes([0x01, 0x02, 0x03, 0x04])


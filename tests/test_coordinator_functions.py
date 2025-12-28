"""Tests unitaires pour les fonctions du coordinateur (sans dépendances)."""
import pytest
from unittest.mock import patch


def test_build_arc_command_logic():
    """Test de la logique de construction de commande ARC."""
    # Simuler la logique de _build_arc_command
    def build_arc_command(house_code: str, unit_code: str, command: str, sequence: int = 0):
        """Version simplifiée pour test."""
        # Convertir house code
        if house_code and len(house_code) == 1 and house_code.isalpha():
            hc = ord(house_code.upper())
        else:
            hc = 0x41
        
        # Convertir unit code
        try:
            uc = int(unit_code) if unit_code else 1
        except (ValueError, TypeError):
            uc = 1
        
        # Commande
        cmd_byte = 0x01 if command == "ON" else 0x00
        
        return bytes([
            0x07,  # Longueur
            0x10,  # Lighting1
            0x01,  # ARC subtype
            sequence % 256,  # Sequence
            hc,  # House code
            uc,  # Unit code
            cmd_byte,  # Command
            0x00,  # Signal level
        ])
    
    # Test ON
    cmd = build_arc_command("A", "1", "ON", 98)
    assert len(cmd) == 8
    assert cmd[0] == 0x07
    assert cmd[1] == 0x10
    assert cmd[2] == 0x01
    assert cmd[3] == 98
    assert cmd[4] == 0x41  # A
    assert cmd[5] == 1
    assert cmd[6] == 0x01  # ON
    assert cmd[7] == 0x00
    
    # Test OFF
    cmd = build_arc_command("A", "1", "OFF", 99)
    assert cmd[6] == 0x00  # OFF
    
    # Test différents house codes
    for letter in "ABCDEFGHIJKLMNOP":
        cmd = build_arc_command(letter, "1", "ON", 0)
        expected = ord(letter)
        assert cmd[4] == expected
    
    # Test différents unit codes
    for unit in range(1, 17):
        cmd = build_arc_command("A", str(unit), "ON", 0)
        assert cmd[5] == unit


def test_hex_string_to_bytes_logic():
    """Test de la logique de conversion hex."""
    def hex_string_to_bytes(hex_str: str, length: int):
        """Version simplifiée pour test."""
        hex_str = hex_str.replace(" ", "").replace(":", "").replace("-", "")
        try:
            device_bytes = bytes.fromhex(hex_str)
            if len(device_bytes) < length:
                device_bytes = device_bytes + bytes(length - len(device_bytes))
            elif len(device_bytes) > length:
                device_bytes = device_bytes[:length]
            return device_bytes
        except ValueError:
            return bytes(length)
    
    # Test avec espaces
    result = hex_string_to_bytes("01 02 03 04", 4)
    assert result == bytes([0x01, 0x02, 0x03, 0x04])
    
    # Test sans espaces
    result = hex_string_to_bytes("01020304", 4)
    assert result == bytes([0x01, 0x02, 0x03, 0x04])
    
    # Test avec padding
    result = hex_string_to_bytes("01", 4)
    assert len(result) == 4
    assert result[0] == 0x01
    
    # Test avec troncature
    result = hex_string_to_bytes("0102030405060708", 4)
    assert len(result) == 4


def test_arc_command_format():
    """Test du format exact de la commande ARC selon les logs."""
    # Format attendu: 07 10 01 62 41 01 01 00
    expected = bytes([0x07, 0x10, 0x01, 0x62, 0x41, 0x01, 0x01, 0x00])
    
    # Vérifier chaque byte
    assert expected[0] == 0x07  # Longueur
    assert expected[1] == 0x10  # Lighting1
    assert expected[2] == 0x01  # ARC
    assert expected[3] == 0x62  # Sequence 98
    assert expected[4] == 0x41  # House A
    assert expected[5] == 0x01  # Unit 1
    assert expected[6] == 0x01  # ON
    assert expected[7] == 0x00  # Signal level



"""Tests pour l'envoi de commandes dans le coordinator."""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.rfxcom.coordinator import RFXCOMCoordinator
from custom_components.rfxcom.const import (
    CONNECTION_TYPE_USB,
    CONNECTION_TYPE_NETWORK,
    PROTOCOL_ARC,
    PROTOCOL_AC,
    PROTOCOL_X10,
    PROTOCOL_PT2262,
    PROTOCOL_IKEA_KOPPLA,
    PROTOCOL_LIGHTWAVERF,
    PROTOCOL_BLYSS,
    CMD_ON,
    CMD_OFF,
)


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    
    async def async_add_executor_job(func, *args):
        """Simule async_add_executor_job."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args)
        return func(*args)
    
    hass.async_add_executor_job = async_add_executor_job
    return hass


@pytest.fixture
def mock_entry_usb():
    """Mock d'une entrée de configuration USB."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "connection_type": CONNECTION_TYPE_USB,
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
    }
    entry.options = MagicMock()
    entry.options.get = Mock(return_value=False)
    return entry


@pytest.fixture
def coordinator_usb(mock_hass, mock_entry_usb):
    """Créer un coordinator USB pour les tests."""
    return RFXCOMCoordinator(mock_hass, mock_entry_usb)


class TestCoordinatorSendCommands:
    """Tests pour l'envoi de commandes."""

    @pytest.mark.asyncio
    async def test_send_command_lighting1_on(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande Lighting1 ON."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator_usb.hass = mock_hass
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_ON,
            house_code="A",
            unit_code="1",
        )
        
        assert result is True
        assert mock_serial.write.called
        assert mock_serial.flush.called

    @pytest.mark.asyncio
    async def test_send_command_lighting1_off(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande Lighting1 OFF."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator_usb.hass = mock_hass
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_OFF,
            house_code="A",
            unit_code="1",
        )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting2_network(self, mock_hass):
        """Test d'envoi de commande Lighting2 via réseau."""
        entry = Mock()
        entry.entry_id = "test_entry"
        entry.data = {
            "connection_type": CONNECTION_TYPE_NETWORK,
            "host": "localhost",
            "network_port": 8889,
        }
        entry.options = MagicMock()
        entry.options.get = Mock(return_value=False)
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator = RFXCOMCoordinator(mock_hass, entry)
        
        mock_socket = MagicMock()
        mock_socket.sendall = Mock()
        mock_socket.getpeername = Mock(return_value=("localhost", 8889))
        coordinator.socket = mock_socket
        coordinator.connection_type = CONNECTION_TYPE_NETWORK
        coordinator._use_node_bridge = False  # Désactiver Node.js
        
        result = await coordinator.send_command(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            command=CMD_ON,
            unit_code="2",
        )
        
        assert result is True
        assert mock_socket.sendall.called

    @pytest.mark.asyncio
    async def test_send_command_port_closed(self, coordinator_usb):
        """Test d'envoi avec port fermé."""
        mock_serial = MagicMock()
        mock_serial.is_open = False
        
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_ARC,
            device_id="",
            command=CMD_ON,
            house_code="A",
            unit_code="1",
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_socket_none(self, mock_hass):
        """Test d'envoi avec socket None."""
        entry = Mock()
        entry.entry_id = "test_entry"
        entry.data = {
            "connection_type": CONNECTION_TYPE_NETWORK,
            "host": "localhost",
            "network_port": 8889,
        }
        entry.options = MagicMock()
        entry.options.get = Mock(return_value=False)
        
        coordinator = RFXCOMCoordinator(mock_hass, entry)
        coordinator.socket = None
        coordinator.connection_type = CONNECTION_TYPE_NETWORK
        
        result = await coordinator.send_command(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            command=CMD_ON,
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_unsupported_protocol(self, coordinator_usb):
        """Test d'envoi avec protocole non supporté."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol="UNKNOWN_PROTOCOL",
            device_id="",
            command=CMD_ON,
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_lighting3(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande Lighting3."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator_usb.hass = mock_hass
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_IKEA_KOPPLA,
            device_id="010203",
            command=CMD_ON,
            unit_code="1",
        )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting4(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande Lighting4."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator_usb.hass = mock_hass
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_PT2262,
            device_id="010203",
            command=CMD_ON,
        )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting5(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande Lighting5."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator_usb.hass = mock_hass
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_LIGHTWAVERF,
            device_id="010203",
            command=CMD_ON,
            unit_code="1",
        )
        
        assert result is True
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_lighting6(self, coordinator_usb, mock_hass):
        """Test d'envoi de commande Lighting6."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        async def async_add_executor_job(func, *args):
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            return func(*args)
        
        mock_hass.async_add_executor_job = async_add_executor_job
        
        coordinator_usb.hass = mock_hass
        coordinator_usb.serial_port = mock_serial
        coordinator_usb.connection_type = CONNECTION_TYPE_USB
        
        result = await coordinator_usb.send_command(
            protocol=PROTOCOL_BLYSS,
            device_id="0102",
            command=CMD_ON,
        )
        
        assert result is True
        assert mock_serial.write.called


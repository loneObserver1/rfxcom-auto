"""Tests pour l'intégration Node.js bridge dans le coordinator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from custom_components.rfxcom.coordinator import RFXCOMCoordinator
from custom_components.rfxcom.const import (
    PROTOCOL_AC,
    CMD_ON,
    CMD_OFF,
    CONNECTION_TYPE_USB,
    CONNECTION_TYPE_NETWORK,
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
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "connection_type": CONNECTION_TYPE_USB,
        "port": "/dev/ttyUSB0",
        "baudrate": 38400,
    }
    entry.options = MagicMock()
    entry.options.get = Mock(return_value=False)  # auto_registry désactivé par défaut
    entry.options.__getitem__ = Mock(return_value=[])  # Pour devices
    return entry


class TestCoordinatorNodeBridge:
    """Tests pour l'intégration Node.js bridge."""

    @pytest.mark.asyncio
    async def test_send_command_ac_with_node_bridge(self, mock_hass, mock_entry):
        """Test d'envoi de commande AC avec Node.js bridge."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry)
        
        # Mock du port série
        mock_serial = MagicMock()
        mock_serial.is_open = True
        coordinator.serial_port = mock_serial
        
        # Mock du bridge Node.js
        mock_bridge = MagicMock()
        mock_bridge.send_command = AsyncMock(return_value=True)
        coordinator._node_bridge = mock_bridge
        coordinator._use_node_bridge = True
        
        # Mock de la connexion USB
        with patch("serial.Serial", return_value=mock_serial):
            await coordinator.async_setup()
        
        # Envoyer une commande AC
        result = await coordinator.send_command(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            unit_code="2",
            command=CMD_ON,
        )
        
        # Vérifier que le bridge Node.js a été appelé
        assert result is True
        mock_bridge.send_command.assert_called_once_with(
            PROTOCOL_AC, "02382C82", 2, "on"
        )

    @pytest.mark.asyncio
    async def test_send_command_ac_fallback_to_python(self, mock_hass, mock_entry):
        """Test de fallback vers Python si Node.js échoue."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry)
        
        # Mock du port série
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        coordinator.serial_port = mock_serial
        
        # Mock du bridge Node.js qui échoue
        mock_bridge = MagicMock()
        mock_bridge.send_command = AsyncMock(return_value=False)
        coordinator._node_bridge = mock_bridge
        coordinator._use_node_bridge = True
        
        # Mock de la connexion USB
        with patch("serial.Serial", return_value=mock_serial):
            await coordinator.async_setup()
        
        # Envoyer une commande AC
        result = await coordinator.send_command(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            unit_code="2",
            command=CMD_ON,
        )
        
        # Vérifier que le fallback Python a été utilisé
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_send_command_ac_no_bridge(self, mock_hass, mock_entry):
        """Test d'envoi AC sans bridge Node.js."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry)
        
        # Mock du port série
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        coordinator.serial_port = mock_serial
        
        # Pas de bridge Node.js
        coordinator._node_bridge = None
        coordinator._use_node_bridge = False
        
        # Mock de la connexion USB
        with patch("serial.Serial", return_value=mock_serial):
            await coordinator.async_setup()
        
        # Envoyer une commande AC
        result = await coordinator.send_command(
            protocol=PROTOCOL_AC,
            device_id="02382C82",
            unit_code="2",
            command=CMD_ON,
        )
        
        # Vérifier que Python a été utilisé
        assert mock_serial.write.called

    @pytest.mark.asyncio
    async def test_node_bridge_initialization_success(self, mock_hass, mock_entry):
        """Test d'initialisation réussie du bridge Node.js."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry)
        
        # Mock du port série
        mock_serial = MagicMock()
        mock_serial.is_open = True
        coordinator.serial_port = mock_serial
        
        # Mock du bridge Node.js
        mock_bridge = MagicMock()
        mock_bridge.initialize = AsyncMock()
        mock_bridge.close = AsyncMock()
        
        with patch("serial.Serial", return_value=mock_serial), \
             patch("custom_components.rfxcom.coordinator.NodeBridge", return_value=mock_bridge):
            await coordinator.async_setup()
        
        # Vérifier que le bridge a été initialisé
        assert coordinator._node_bridge is not None
        mock_bridge.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_node_bridge_initialization_failure(self, mock_hass, mock_entry):
        """Test d'initialisation échouée du bridge Node.js (fallback)."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry)
        
        # Mock du port série
        mock_serial = MagicMock()
        mock_serial.is_open = True
        coordinator.serial_port = mock_serial
        
        # Mock du bridge Node.js qui échoue
        mock_bridge = MagicMock()
        mock_bridge.initialize = AsyncMock(side_effect=Exception("Bridge failed"))
        
        with patch("serial.Serial", return_value=mock_serial), \
             patch("custom_components.rfxcom.coordinator.NodeBridge", return_value=mock_bridge):
            await coordinator.async_setup()
        
        # Vérifier que le fallback a été activé
        assert coordinator._use_node_bridge is False

    @pytest.mark.asyncio
    async def test_shutdown_with_node_bridge(self, mock_hass, mock_entry):
        """Test de fermeture avec bridge Node.js."""
        coordinator = RFXCOMCoordinator(mock_hass, mock_entry)
        
        # Mock du port série
        mock_serial = MagicMock()
        mock_serial.is_open = True
        coordinator.serial_port = mock_serial
        
        # Mock du bridge Node.js
        mock_bridge = MagicMock()
        mock_bridge.close = AsyncMock()
        coordinator._node_bridge = mock_bridge
        
        await coordinator.async_shutdown()
        
        # Vérifier que le bridge a été fermé
        mock_bridge.close.assert_called_once()


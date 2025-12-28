"""Tests pour le bridge Node.js."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from custom_components.rfxcom.node_bridge import NodeBridge


class TestNodeBridge:
    """Tests pour NodeBridge."""

    @pytest.fixture
    def bridge(self):
        """Créer une instance de NodeBridge."""
        return NodeBridge(port="/dev/ttyUSB0")

    def test_init(self, bridge):
        """Test de l'initialisation."""
        assert bridge.port == "/dev/ttyUSB0"
        assert bridge.process is None
        assert bridge._initialized is False

    def test_get_script_path(self, bridge):
        """Test du chemin du script."""
        path = bridge._get_script_path()
        assert path.exists() or path.name == "rfxcom_node_bridge.js"
        assert "tmp" in str(path) or "rfxcom_node_bridge.js" in str(path)

    @pytest.mark.asyncio
    async def test_initialize_success(self, bridge):
        """Test de l'initialisation réussie."""
        mock_process = MagicMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "ready", "port": "/dev/ttyUSB0"}).encode()
        )

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch.object(bridge, "_get_script_path", return_value=mock_path):
            await bridge.initialize()

        assert bridge._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_failure(self, bridge):
        """Test de l'initialisation échouée."""
        mock_process = MagicMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "error", "error": "Connection failed"}).encode()
        )

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch.object(bridge, "_get_script_path", return_value=mock_path):
            with pytest.raises(RuntimeError, match="Échec de l'initialisation"):
                await bridge.initialize()

    @pytest.mark.asyncio
    async def test_send_command_success(self, bridge):
        """Test de l'envoi de commande réussi."""
        bridge._initialized = True
        bridge.process = MagicMock()
        bridge.process.stdin = AsyncMock()
        bridge.process.stdout = AsyncMock()
        bridge.process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "success"}).encode()
        )

        result = await bridge.send_command("AC", "02382C82", 2, "on")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_command_not_initialized(self, bridge):
        """Test de l'envoi de commande sans initialisation."""
        with pytest.raises(RuntimeError, match="non initialisé"):
            await bridge.send_command("AC", "02382C82", 2, "on")

    @pytest.mark.asyncio
    async def test_send_command_failure(self, bridge):
        """Test de l'envoi de commande échoué."""
        bridge._initialized = True
        bridge.process = MagicMock()
        bridge.process.stdin = AsyncMock()
        bridge.process.stdout = AsyncMock()
        bridge.process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "error", "error": "Send failed"}).encode()
        )

        result = await bridge.send_command("AC", "02382C82", 2, "on")

        assert result is False

    @pytest.mark.asyncio
    async def test_pair_device_success(self, bridge):
        """Test de l'appairage réussi."""
        bridge._initialized = True
        bridge.process = MagicMock()
        bridge.process.stdin = AsyncMock()
        bridge.process.stdout = AsyncMock()
        bridge.process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "success", "result": {"sent": 100, "errors": 0}}).encode()
        )

        result = await bridge.pair_device("AC", "02382C82", 2)

        assert result == {"sent": 100, "errors": 0}

    @pytest.mark.asyncio
    async def test_pair_device_failure(self, bridge):
        """Test de l'appairage échoué."""
        bridge._initialized = True
        bridge.process = MagicMock()
        bridge.process.stdin = AsyncMock()
        bridge.process.stdout = AsyncMock()
        bridge.process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "error", "error": "Pairing failed"}).encode()
        )

        with pytest.raises(RuntimeError, match="Échec de l'appairage"):
            await bridge.pair_device("AC", "02382C82", 2)

    @pytest.mark.asyncio
    async def test_close(self, bridge):
        """Test de la fermeture."""
        bridge._initialized = True
        bridge.process = MagicMock()
        bridge.process.stdin = AsyncMock()
        bridge.process.stdout = AsyncMock()
        bridge.process.stdout.readline = AsyncMock(
            return_value=json.dumps({"status": "closed"}).encode()
        )
        bridge.process.returncode = None
        bridge.process.wait = AsyncMock(return_value=0)

        await bridge.close()

        assert bridge._initialized is False
        assert bridge.process is None


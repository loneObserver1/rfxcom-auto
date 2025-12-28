"""Tests étendus pour services.py pour augmenter la couverture."""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.rfxcom.services import async_setup_services, async_unload_services, _call_node_script
from custom_components.rfxcom.const import (
    DOMAIN,
    PROTOCOL_ARC,
    PROTOCOL_AC,
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
    hass.services = MagicMock()
    hass.services.async_register = AsyncMock()
    hass.services.async_remove = AsyncMock()
    hass.config_entries = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_entry():
    """Mock d'une entrée de configuration."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.options = {"devices": []}
    return entry


class TestServicesExtended:
    """Tests étendus pour les services."""

    @pytest.mark.asyncio
    async def test_pair_device_arc_success(self, mock_hass):
        """Test d'appairage ARC réussi."""
        entry = Mock()
        entry.entry_id = "test_entry"
        entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        await async_setup_services(mock_hass)
        
        # Appeler le service pair_device
        call = Mock()
        # Créer un dict qui supporte .get() et [] 
        class CallData(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        
        call.data = CallData({
            CONF_PROTOCOL: PROTOCOL_ARC,
            "name": "Test ARC",
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        })
        
        # Récupérer la fonction enregistrée
        registered_service = mock_hass.services.async_register.call_args[0][2]
        await registered_service(call)
        
        # Vérifier que l'appareil a été ajouté
        assert mock_hass.config_entries.async_update_entry.called
        assert mock_hass.config_entries.async_reload.called

    @pytest.mark.asyncio
    async def test_pair_device_ac_success(self, mock_hass):
        """Test d'appairage AC réussi."""
        entry = Mock()
        entry.entry_id = "test_entry"
        entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        await async_setup_services(mock_hass)
        
        call = Mock()
        class CallData(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        
        call.data = CallData({
            CONF_PROTOCOL: PROTOCOL_AC,
            "name": "Test AC",
            CONF_DEVICE_ID: "02382C82",
            CONF_UNIT_CODE: "2",
        })
        
        registered_service = mock_hass.services.async_register.call_args[0][2]
        await registered_service(call)
        
        assert mock_hass.config_entries.async_update_entry.called

    @pytest.mark.asyncio
    async def test_pair_device_temp_hum_success(self, mock_hass):
        """Test d'appairage TEMP_HUM réussi."""
        entry = Mock()
        entry.entry_id = "test_entry"
        entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        await async_setup_services(mock_hass)
        
        call = Mock()
        class CallData(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        
        call.data = CallData({
            CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
            "name": "Test Temp Hum",
            CONF_DEVICE_ID: "6803",
        })
        
        registered_service = mock_hass.services.async_register.call_args[0][2]
        await registered_service(call)
        
        assert mock_hass.config_entries.async_update_entry.called

    @pytest.mark.asyncio
    async def test_pair_device_missing_fields_arc(self, mock_hass):
        """Test d'appairage ARC avec champs manquants."""
        entry = Mock()
        entry.entry_id = "test_entry"
        entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        
        await async_setup_services(mock_hass)
        
        call = Mock()
        class CallData(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        
        call.data = CallData({
            CONF_PROTOCOL: PROTOCOL_ARC,
            "name": "Test ARC",
            # house_code et unit_code manquants
        })
        
        registered_service = mock_hass.services.async_register.call_args[0][2]
        await registered_service(call)
        
        # Ne devrait pas mettre à jour l'entrée
        assert not mock_hass.config_entries.async_update_entry.called

    @pytest.mark.asyncio
    async def test_pair_device_no_entries(self, mock_hass):
        """Test d'appairage sans entrées configurées."""
        mock_hass.config_entries.async_entries = Mock(return_value=[])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        
        await async_setup_services(mock_hass)
        
        call = Mock()
        class CallData(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        
        call.data = CallData({
            CONF_PROTOCOL: PROTOCOL_ARC,
            "name": "Test ARC",
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        })
        
        registered_service = mock_hass.services.async_register.call_args[0][2]
        await registered_service(call)
        
        # Ne devrait pas mettre à jour l'entrée
        assert not mock_hass.config_entries.async_update_entry.called

    @pytest.mark.asyncio
    async def test_send_command_success(self, mock_hass):
        """Test d'envoi de commande via Node.js."""
        from pathlib import Path
        
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(
            b'{"status": "success"}',
            b'',
        ))
        mock_process.returncode = 0
        
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("custom_components.rfxcom.services._get_node_script_path", return_value=mock_path):
            result = await _call_node_script(mock_hass, "on", "02382C82", "2", None)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_command_failure(self, mock_hass):
        """Test d'échec d'envoi de commande."""
        from pathlib import Path
        
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(
            b'',
            b'Error occurred',
        ))
        mock_process.returncode = 1
        
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("custom_components.rfxcom.services._get_node_script_path", return_value=mock_path):
            result = await _call_node_script(mock_hass, "on", "02382C82", "2", None)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_script_not_found(self, mock_hass):
        """Test avec script Node.js introuvable."""
        from pathlib import Path
        
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.__str__ = Mock(return_value="/nonexistent/script.js")
        mock_path.__fspath__ = Mock(return_value="/nonexistent/script.js")
        
        with patch("custom_components.rfxcom.services._get_node_script_path", return_value=mock_path):
            result = await _call_node_script(mock_hass, "on", "02382C82", "2", None)
        
        # Le script n'existe pas, donc devrait retourner False
        assert result is False


"""Tests pour l'auto-enregistrement des appareils."""
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
    PROTOCOL_ARC,
    PROTOCOL_AC,
    PROTOCOL_TEMP_HUM,
    CONF_PROTOCOL,
    CONF_HOUSE_CODE,
    CONF_UNIT_CODE,
    CONF_DEVICE_ID,
    DEVICE_TYPE_SENSOR,
)


@pytest.fixture
def mock_hass():
    """Mock de Home Assistant."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = Mock(return_value=[])
    return hass


@pytest.fixture
def mock_entry_usb():
    """Mock d'une entrée de configuration USB."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "connection_type": CONNECTION_TYPE_USB,
        "port": "/dev/ttyUSB0",
    }
    entry.options = MagicMock()
    entry.options.get = Mock(return_value=True)  # auto_registry activé
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_entry_usb):
    """Créer un coordinator pour les tests."""
    return RFXCOMCoordinator(mock_hass, mock_entry_usb)


class TestCoordinatorAutoRegister:
    """Tests pour l'auto-enregistrement."""

    @pytest.mark.asyncio
    async def test_auto_register_arc_device(self, coordinator, mock_hass):
        """Test d'auto-enregistrement d'un appareil ARC."""
        coordinator.auto_registry = True
        coordinator._discovered_devices = {}
        
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[mock_entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        device_info = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        # Vérifier que l'appareil a été ajouté
        assert len(coordinator._discovered_devices) > 0

    @pytest.mark.asyncio
    async def test_auto_register_ac_device(self, coordinator, mock_hass):
        """Test d'auto-enregistrement d'un appareil AC."""
        coordinator.auto_registry = True
        coordinator._discovered_devices = {}
        
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[mock_entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        device_info = {
            CONF_PROTOCOL: PROTOCOL_AC,
            CONF_DEVICE_ID: "02382C82",
            CONF_UNIT_CODE: "2",
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        # Vérifier que l'appareil a été ajouté
        assert len(coordinator._discovered_devices) > 0

    @pytest.mark.asyncio
    async def test_auto_register_temp_hum_device(self, coordinator, mock_hass):
        """Test d'auto-enregistrement d'un capteur TEMP_HUM."""
        coordinator.auto_registry = True
        coordinator._discovered_devices = {}
        
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.options = {"devices": []}
        mock_hass.config_entries.async_entries = Mock(return_value=[mock_entry])
        mock_hass.config_entries.async_update_entry = AsyncMock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        device_info = {
            CONF_PROTOCOL: PROTOCOL_TEMP_HUM,
            CONF_DEVICE_ID: "6803",
            "temperature": 20.5,
            "humidity": 65,
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        # Vérifier que l'appareil a été ajouté
        assert len(coordinator._discovered_devices) > 0

    @pytest.mark.asyncio
    async def test_auto_register_device_already_exists(self, coordinator, mock_hass):
        """Test d'auto-enregistrement d'un appareil déjà existant."""
        coordinator.auto_registry = True
        
        # Ajouter un appareil existant
        unique_id = "ARC_A_1"
        coordinator._discovered_devices[unique_id] = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        # Mock async_update_listeners qui vient de DataUpdateCoordinator
        coordinator.async_update_listeners = Mock()
        
        device_info = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        # L'appareil devrait être mis à jour, pas dupliqué
        assert len(coordinator._discovered_devices) == 1

    @pytest.mark.asyncio
    async def test_auto_register_no_entry(self, coordinator, mock_hass):
        """Test d'auto-enregistrement sans entrée de configuration."""
        coordinator.auto_registry = True
        coordinator._discovered_devices = {}
        
        mock_hass.config_entries.async_entries = Mock(return_value=[])
        
        device_info = {
            CONF_PROTOCOL: PROTOCOL_ARC,
            CONF_HOUSE_CODE: "A",
            CONF_UNIT_CODE: "1",
        }
        
        await coordinator._handle_discovered_device(device_info)
        
        # L'appareil devrait être dans discovered_devices mais pas enregistré
        assert len(coordinator._discovered_devices) > 0


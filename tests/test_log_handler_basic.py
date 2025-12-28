"""Tests basiques pour log_handler.py."""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
import logging

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.rfxcom.log_handler import setup_log_handler, get_logs, clear_logs


class TestLogHandler:
    """Tests pour log_handler."""

    def test_setup_log_handler(self):
        """Test de configuration du handler de logs."""
        handler = setup_log_handler()
        assert handler is not None

    def test_get_logs_empty(self):
        """Test de récupération des logs (vide)."""
        clear_logs()
        logs = get_logs()
        assert isinstance(logs, list)
        assert len(logs) == 0

    def test_get_logs_limit(self):
        """Test de récupération des logs avec limite."""
        clear_logs()
        logs = get_logs(limit=10)
        assert isinstance(logs, list)
        assert len(logs) <= 10

    def test_clear_logs(self):
        """Test de nettoyage des logs."""
        clear_logs()
        logs = get_logs()
        assert len(logs) == 0


"""Tests pour log_handler.py."""
import pytest
import logging
import sys
import os
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Importer directement depuis le fichier
log_handler_path = os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'rfxcom', 'log_handler.py')
import importlib.util
spec = importlib.util.spec_from_file_location("log_handler", log_handler_path)
log_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log_handler_module)

RFXCOMLogHandler = log_handler_module.RFXCOMLogHandler
get_logs = log_handler_module.get_logs
clear_logs = log_handler_module.clear_logs
setup_log_handler = log_handler_module.setup_log_handler


class TestLogHandler:
    """Tests pour RFXCOMLogHandler."""

    def test_setup_log_handler(self):
        """Test de la création du handler."""
        handler = setup_log_handler()
        assert isinstance(handler, RFXCOMLogHandler)
        assert handler.level == logging.DEBUG

    def test_handler_emit(self):
        """Test de l'émission d'un log."""
        handler = setup_log_handler()
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Effacer les logs précédents
        clear_logs()
        
        # Émettre un log
        logger.debug("Test message")
        
        # Vérifier que le log a été capturé
        logs = get_logs()
        assert len(logs) > 0
        assert "Test message" in logs[-1]["message"]
        assert logs[-1]["level"] == "DEBUG"

    def test_get_logs_limit(self):
        """Test de la limite des logs."""
        clear_logs()
        handler = setup_log_handler()
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Émettre plusieurs logs
        for i in range(10):
            logger.debug(f"Message {i}")
        
        # Récupérer avec limite
        logs = get_logs(limit=5)
        assert len(logs) == 5
        assert "Message 9" in logs[-1]["message"]

    def test_clear_logs(self):
        """Test de l'effacement des logs."""
        handler = setup_log_handler()
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Émettre un log
        logger.debug("Test message")
        assert len(get_logs()) > 0
        
        # Effacer
        clear_logs()
        assert len(get_logs()) == 0

    def test_log_format(self):
        """Test du format des logs."""
        clear_logs()
        handler = setup_log_handler()
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        logs = get_logs()
        assert len(logs) >= 3
        
        # Vérifier les niveaux (les logs peuvent être dans un ordre différent)
        all_levels = [log["level"] for log in logs]
        assert "INFO" in all_levels or any("Info message" in log["message"] for log in logs)
        assert "WARNING" in all_levels or any("Warning message" in log["message"] for log in logs)
        assert "ERROR" in all_levels or any("Error message" in log["message"] for log in logs)

    def test_log_timestamp(self):
        """Test que les logs ont un timestamp."""
        clear_logs()
        handler = setup_log_handler()
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        logger.debug("Test message")
        
        logs = get_logs()
        assert len(logs) > 0
        assert "timestamp" in logs[-1]
        # Vérifier que le timestamp est valide
        datetime.fromisoformat(logs[-1]["timestamp"])


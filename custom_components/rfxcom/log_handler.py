"""Gestionnaire de logs pour RFXCOM."""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Stockage des logs en mémoire (limité à 1000 entrées)
_log_buffer: deque[dict[str, Any]] = deque(maxlen=1000)


class RFXCOMLogHandler(logging.Handler):
    """Handler personnalisé pour capturer les logs RFXCOM."""

    def emit(self, record: logging.LogRecord) -> None:
        """Capture un log."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            }
            _log_buffer.append(log_entry)
        except Exception:
            # Ignorer les erreurs dans le handler pour éviter les boucles
            pass


def get_logs(limit: int = 500) -> list[dict[str, Any]]:
    """Retourne les logs récents."""
    return list(_log_buffer)[-limit:]


def clear_logs() -> None:
    """Efface tous les logs."""
    _log_buffer.clear()


def setup_log_handler() -> RFXCOMLogHandler:
    """Configure et retourne le handler de logs."""
    handler = RFXCOMLogHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    return handler



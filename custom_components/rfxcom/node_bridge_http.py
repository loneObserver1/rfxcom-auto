"""Wrapper Python pour communiquer avec l'add-on RFXCOM Node.js Bridge via HTTP."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

try:
    import aiohttp
except ImportError:
    aiohttp = None

_LOGGER = logging.getLogger(__name__)

# URL par défaut de l'add-on (accessible via Supervisor API)
DEFAULT_ADDON_URL = "http://localhost:8888"


class NodeBridgeHTTP:
    """Wrapper pour communiquer avec le bridge Node.js RFXCOM via HTTP."""

    def __init__(self, addon_url: str | None = None, serial_port: str | None = None) -> None:
        """Initialise le bridge HTTP."""
        self.addon_url = addon_url or DEFAULT_ADDON_URL
        self.serial_port = serial_port
        self._session: aiohttp.ClientSession | None = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def _ensure_session(self) -> None:
        """S'assure qu'une session HTTP est créée."""
        if self._session is None:
            if aiohttp is None:
                raise RuntimeError(
                    "aiohttp n'est pas installé. "
                    "Installez-le avec: pip install aiohttp"
                )
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )

    async def check_addon_available(self) -> dict[str, Any] | None:
        """Vérifie si l'add-on est disponible et retourne ses informations."""
        await self._ensure_session()
        
        try:
            async with self._session.get(
                f"{self.addon_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "available": True,
                        "initialized": data.get("initialized", False),
                        "port": data.get("port", "N/A"),
                        "status": "ok"
                    }
                else:
                    return {
                        "available": False,
                        "status": f"HTTP {response.status}",
                        "error": f"Add-on répond avec le code {response.status}"
                    }
        except asyncio.TimeoutError:
            return {
                "available": False,
                "status": "timeout",
                "error": f"Timeout lors de la connexion à {self.addon_url}"
            }
        except aiohttp.ClientConnectorError as e:
            return {
                "available": False,
                "status": "connection_error",
                "error": f"Impossible de se connecter à {self.addon_url}: {e}"
            }
        except aiohttp.ClientError as e:
            return {
                "available": False,
                "status": "client_error",
                "error": f"Erreur client: {e}"
            }
        except Exception as e:
            return {
                "available": False,
                "status": "unknown_error",
                "error": f"Erreur inconnue: {e}"
            }

    async def initialize(self) -> None:
        """Initialise la connexion avec l'add-on."""
        async with self._lock:
            if self._initialized:
                return

            await self._ensure_session()

            # Vérifier que l'add-on est disponible
            addon_info = await self.check_addon_available()
            
            if addon_info and addon_info.get("available"):
                # Initialiser l'add-on avec le port série si fourni
                if self.serial_port:
                    try:
                        async with self._session.post(
                            f"{self.addon_url}/api/init",
                            json={"port": self.serial_port},
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                init_data = await response.json()
                                _LOGGER.info(
                                    "✅ Add-on RFXCOM Node.js Bridge initialisé: port=%s",
                                    init_data.get("port", self.serial_port)
                                )
                            else:
                                error_text = await response.text()
                                _LOGGER.warning(
                                    "⚠️ Erreur lors de l'initialisation de l'add-on (status: %d): %s",
                                    response.status,
                                    error_text
                                )
                    except Exception as e:
                        _LOGGER.warning(
                            "⚠️ Erreur lors de l'initialisation de l'add-on avec le port %s: %s",
                            self.serial_port,
                            e
                        )
                
                _LOGGER.info(
                    "✅ Add-on RFXCOM Node.js Bridge connecté: port=%s, initialisé=%s",
                    addon_info.get("port", "N/A"),
                    addon_info.get("initialized", False)
                )
                self._initialized = True
            else:
                error_msg = addon_info.get("error", "Erreur inconnue") if addon_info else "Aucune réponse"
                status = addon_info.get("status", "unknown") if addon_info else "unknown"
                
                detailed_error = (
                    f"Impossible de se connecter à l'add-on RFXCOM Node.js Bridge "
                    f"sur {self.addon_url}.\n"
                    f"Statut: {status}\n"
                    f"Erreur: {error_msg}\n\n"
                    "Assurez-vous que:\n"
                    "1. L'add-on est installé dans Home Assistant\n"
                    "2. L'add-on est démarré (état: Running)\n"
                    "3. Le port API est correctement configuré (par défaut: 8888)\n"
                    "4. L'add-on a accès au port série RFXCOM\n\n"
                    "Pour vérifier l'add-on:\n"
                    "- Allez dans Paramètres > Modules complémentaires\n"
                    "- Cherchez 'RFXCOM Node.js Bridge'\n"
                    "- Vérifiez que l'état est 'Running'\n"
                    "- Consultez les logs de l'add-on pour plus de détails"
                )
                raise RuntimeError(detailed_error)

    async def send_command(
        self,
        protocol: str,
        device_id: str | None = None,
        house_code: str | None = None,
        unit_code: int | None = None,
        command: str = "on",
    ) -> bool:
        """Envoie une commande ON/OFF."""
        if not self._initialized:
            await self.initialize()

        await self._ensure_session()

        payload = {
            "protocol": protocol,
            "command": command,
        }

        if device_id:
            payload["device_id"] = device_id
        if house_code:
            payload["house_code"] = house_code
        if unit_code is not None:
            payload["unit_code"] = unit_code
        # Transmettre le port série si configuré
        if self.serial_port:
            payload["port"] = self.serial_port

        try:
            async with self._session.post(
                f"{self.addon_url}/api/command",
                json=payload,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        _LOGGER.debug(
                            "Commande %s envoyée avec succès via add-on HTTP",
                            command
                        )
                        return True
                    else:
                        error = data.get("error", "Erreur inconnue")
                        _LOGGER.error(
                            "❌ Erreur add-on lors de l'envoi de la commande %s: %s",
                            command,
                            error,
                        )
                        return False
                else:
                    error_text = await response.text()
                    _LOGGER.error(
                        "❌ Erreur HTTP lors de l'envoi de la commande %s "
                        "(status: %d): %s",
                        command,
                        response.status,
                        error_text,
                    )
                    return False
        except aiohttp.ClientError as e:
            _LOGGER.error(
                "❌ Erreur de connexion lors de l'envoi de la commande %s: %s",
                command,
                e,
            )
            return False
        except asyncio.TimeoutError:
            _LOGGER.error(
                "❌ Timeout lors de l'envoi de la commande %s: pas de réponse après 30s",
                command,
            )
            return False
        except Exception as e:
            _LOGGER.error(
                "❌ Erreur inattendue lors de l'envoi de la commande %s: %s",
                command,
                e,
                exc_info=True,
            )
            return False

    async def pair_device(
        self,
        protocol: str,
        device_id: str | None = None,
        house_code: str | None = None,
        unit_code: int | None = None,
    ) -> dict[str, Any]:
        """Appaire un appareil."""
        # Pour l'instant, on utilise send_command avec command="pair"
        # L'add-on peut être étendu pour supporter un endpoint /api/pair
        success = await self.send_command(
            protocol=protocol,
            device_id=device_id,
            house_code=house_code,
            unit_code=unit_code,
            command="pair",
        )
        return {"status": "success" if success else "error"}

    async def close(self) -> None:
        """Ferme la connexion."""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False


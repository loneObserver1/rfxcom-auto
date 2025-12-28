"""Wrapper Python pour le bridge Node.js RFXCOM."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


class NodeBridge:
    """Wrapper pour communiquer avec le bridge Node.js RFXCOM."""

    def __init__(self, port: str | None = None) -> None:
        """Initialise le bridge Node.js."""
        self.port = port
        self.process: subprocess.Popen | None = None
        self._lock = asyncio.Lock()
        self._initialized = False

    def _get_script_path(self) -> Path:
        """Retourne le chemin du script Node.js."""
        # Le script est dans le même dossier que node_bridge.py
        script_path = Path(__file__).parent / "rfxcom_node_bridge.js"
        return script_path
    
    def _get_package_json_path(self) -> Path:
        """Retourne le chemin du package.json."""
        # Le package.json est dans le même dossier que node_bridge.py
        package_path = Path(__file__).parent / "package.json"
        return package_path
    
    async def _check_npm_dependencies(self) -> bool:
        """Vérifie et installe les dépendances npm si nécessaire."""
        package_json_path = self._get_package_json_path()
        script_path = self._get_script_path()
        
        if not package_json_path.exists():
            _LOGGER.warning("⚠️ package.json introuvable: %s", package_json_path)
            return False
        
        # Vérifier si node_modules existe
        node_modules_path = package_json_path.parent / "node_modules" / "rfxcom"
        if node_modules_path.exists():
            _LOGGER.debug("✅ Dépendances npm déjà installées")
            return True
        
        # Installer les dépendances
        _LOGGER.info("📦 Installation des dépendances npm (rfxcom)...")
        try:
            process = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=str(package_json_path.parent),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                _LOGGER.info("✅ Dépendances npm installées avec succès")
                return True
            else:
                error_msg = stderr.decode().strip() if stderr else stdout.decode().strip()
                _LOGGER.error("❌ Erreur lors de l'installation des dépendances npm: %s", error_msg)
                return False
        except FileNotFoundError:
            _LOGGER.error("❌ npm non trouvé. Veuillez installer Node.js et npm: https://nodejs.org/")
            return False
        except Exception as e:
            _LOGGER.error("❌ Erreur lors de l'installation des dépendances npm: %s", e)
            return False

    async def _check_nodejs_available(self) -> bool:
        """Vérifie si Node.js est disponible sur le système."""
        try:
            process = await asyncio.create_subprocess_exec(
                "node",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                version = stdout.decode().strip()
                _LOGGER.info("✅ Node.js détecté: %s", version)
                return True
            else:
                _LOGGER.warning("⚠️ Node.js non disponible (code de retour: %s)", process.returncode)
                return False
        except FileNotFoundError:
            _LOGGER.warning("⚠️ Node.js non installé ou non trouvé dans le PATH")
            return False
        except Exception as e:
            _LOGGER.warning("⚠️ Erreur lors de la vérification de Node.js: %s", e)
            return False

    async def _try_install_nodejs(self) -> bool:
        """Tente d'installer Node.js automatiquement."""
        import platform
        import shutil
        
        _LOGGER.info("🔧 Tentative d'installation automatique de Node.js...")
        
        system = platform.system().lower()
        
        # Vérifier si on est dans un conteneur Docker
        if Path("/.dockerenv").exists():
            _LOGGER.error(
                "❌ Node.js non disponible dans le conteneur Docker. "
                "Veuillez ajouter Node.js à votre image Docker Home Assistant."
            )
            _LOGGER.info(
                "💡 Options pour installer Node.js dans Docker:"
            )
            _LOGGER.info(
                "   1. Utiliser une image Home Assistant avec Node.js pré-installé"
            )
            _LOGGER.info(
                "   2. Créer un Dockerfile personnalisé basé sur homeassistant/home-assistant"
            )
            _LOGGER.info(
                "   3. Installer Node.js manuellement dans le conteneur (non persistant)"
            )
            return False
        
        # Essayer d'installer selon le système
        if system == "linux":
            # Essayer avec apt-get (Debian/Ubuntu)
            if shutil.which("apt-get"):
                _LOGGER.info("📦 Tentative d'installation via apt-get...")
                try:
                    # Mettre à jour les paquets
                    update_process = await asyncio.create_subprocess_exec(
                        "sudo", "apt-get", "update",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await update_process.communicate()
                    
                    # Installer Node.js et npm
                    install_process = await asyncio.create_subprocess_exec(
                        "sudo", "apt-get", "install", "-y", "nodejs", "npm",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await install_process.communicate()
                    
                    if install_process.returncode == 0:
                        _LOGGER.info("✅ Node.js installé avec succès via apt-get")
                        return True
                    else:
                        error_msg = stderr.decode().strip() if stderr else stdout.decode().strip()
                        _LOGGER.error("❌ Échec de l'installation via apt-get: %s", error_msg)
                        return False
                except FileNotFoundError:
                    _LOGGER.error("❌ sudo ou apt-get non disponible")
                    return False
                except Exception as e:
                    _LOGGER.error("❌ Erreur lors de l'installation via apt-get: %s", e)
                    return False
            else:
                _LOGGER.error("❌ Gestionnaire de paquets non supporté pour l'installation automatique")
                return False
        elif system == "darwin":  # macOS
            # Essayer avec Homebrew
            if shutil.which("brew"):
                _LOGGER.info("📦 Tentative d'installation via Homebrew...")
                try:
                    process = await asyncio.create_subprocess_exec(
                        "brew", "install", "node",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        _LOGGER.info("✅ Node.js installé avec succès via Homebrew")
                        return True
                    else:
                        error_msg = stderr.decode().strip() if stderr else stdout.decode().strip()
                        _LOGGER.error("❌ Échec de l'installation via Homebrew: %s", error_msg)
                        return False
                except Exception as e:
                    _LOGGER.error("❌ Erreur lors de l'installation via Homebrew: %s", e)
                    return False
            else:
                _LOGGER.error("❌ Homebrew non disponible. Installez Node.js manuellement: https://nodejs.org/")
                return False
        else:
            _LOGGER.error("❌ Installation automatique non supportée pour %s", system)
            _LOGGER.info("💡 Installez Node.js manuellement: https://nodejs.org/")
            return False

    async def initialize(self) -> None:
        """Initialise la connexion RFXCOM via Node.js."""
        # Vérifier la présence de Node.js
        _LOGGER.info("🔍 Vérification de la présence de Node.js...")
        if not await self._check_nodejs_available():
            _LOGGER.warning("⚠️ Node.js non détecté, tentative d'installation automatique...")
            if not await self._try_install_nodejs():
                raise RuntimeError(
                    "Node.js n'est pas disponible et n'a pas pu être installé automatiquement. "
                    "Veuillez installer Node.js manuellement: https://nodejs.org/"
                )
            # Vérifier à nouveau après l'installation
            if not await self._check_nodejs_available():
                raise RuntimeError(
                    "Node.js a été installé mais n'est toujours pas détecté. "
                    "Veuillez redémarrer Home Assistant ou vérifier votre PATH."
                )
        
        # Vérifier et installer les dépendances npm
        _LOGGER.info("🔍 Vérification des dépendances npm...")
        if not await self._check_npm_dependencies():
            raise RuntimeError(
                "Les dépendances npm (rfxcom) ne sont pas installées. "
                "Veuillez installer les dépendances manuellement avec 'npm install' dans le répertoire custom_components/rfxcom/."
            )
        
        script_path = self._get_script_path()
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script Node.js introuvable: {script_path}")
        
        _LOGGER.debug("Démarrage du bridge Node.js: %s", script_path)
        
        # Démarrer le processus Node.js
        self.process = await asyncio.create_subprocess_exec(
            "node",
            str(script_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # Envoyer la commande d'initialisation
        init_command = {
            "action": "init",
            "port": self.port,
        }
        
        await self._send_command(init_command)
        
        # Lire la réponse
        response = await self._read_response()
        
        if response.get("status") == "ready":
            self._initialized = True
            _LOGGER.info("Bridge Node.js initialisé sur le port: %s", response.get("port"))
        else:
            error = response.get("error", "Erreur inconnue")
            raise RuntimeError(f"Échec de l'initialisation du bridge Node.js: {error}")

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
            raise RuntimeError("Bridge Node.js non initialisé")
        
        try:
            send_command = {
                "action": "send",
                "protocol": protocol,
                "command": command,
            }
            
            # Ajouter les paramètres selon le protocole
            if device_id:
                send_command["device_id"] = device_id
            if house_code:
                send_command["house_code"] = house_code
            if unit_code is not None:
                send_command["unit_code"] = unit_code
            
            await self._send_command(send_command)
            response = await self._read_response()
            
            if response.get("status") == "success":
                _LOGGER.debug("Commande %s envoyée avec succès via Node.js", command)
                return True
            else:
                error = response.get("error", "Erreur inconnue")
                _LOGGER.error(
                    "❌ Erreur Node.js lors de l'envoi de la commande %s (protocole=%s): %s",
                    command,
                    protocol,
                    error,
                )
                return False
        except RuntimeError as e:
            _LOGGER.error(
                "❌ Erreur Runtime Node.js lors de l'envoi de la commande %s (protocole=%s): %s",
                command,
                protocol,
                e,
            )
            return False
        except asyncio.TimeoutError:
            _LOGGER.error(
                "❌ Timeout Node.js lors de l'envoi de la commande %s (protocole=%s): pas de réponse après 10s",
                command,
                protocol,
            )
            return False
        except json.JSONDecodeError as e:
            _LOGGER.error(
                "❌ Erreur JSON Node.js lors de l'envoi de la commande %s (protocole=%s): %s",
                command,
                protocol,
                e,
            )
            return False
        except Exception as e:
            _LOGGER.error(
                "❌ Erreur inattendue Node.js lors de l'envoi de la commande %s (protocole=%s): %s",
                command,
                protocol,
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
        if not self._initialized:
            raise RuntimeError("Bridge Node.js non initialisé")
        
        try:
            pair_command = {
                "action": "pair",
                "protocol": protocol,
            }
            
            # Ajouter les paramètres selon le protocole
            if device_id:
                pair_command["device_id"] = device_id
            if house_code:
                pair_command["house_code"] = house_code
            if unit_code is not None:
                pair_command["unit_code"] = unit_code
            
            await self._send_command(pair_command)
            response = await self._read_response(timeout=15.0)  # Timeout plus long pour l'appairage
            
            if response.get("status") == "success":
                result = response.get("result", {})
                _LOGGER.info("✅ Appairage Node.js réussi (protocole=%s): %s", protocol, result)
                return result
            else:
                error = response.get("error", "Erreur inconnue")
                _LOGGER.error(
                    "❌ Erreur Node.js lors de l'appairage (protocole=%s): %s",
                    protocol,
                    error,
                )
                raise RuntimeError(f"Échec de l'appairage Node.js: {error}")
        except RuntimeError:
            # Re-lancer les RuntimeError telles quelles
            raise
        except asyncio.TimeoutError:
            error_msg = f"Timeout Node.js lors de l'appairage (protocole={protocol}): pas de réponse après 15s"
            _LOGGER.error("❌ %s", error_msg)
            raise RuntimeError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Erreur JSON Node.js lors de l'appairage (protocole={protocol}): {e}"
            _LOGGER.error("❌ %s", error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Erreur inattendue Node.js lors de l'appairage (protocole={protocol}): {e}"
            _LOGGER.error("❌ %s", error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    async def _send_command(self, command: dict[str, Any]) -> None:
        """Envoie une commande JSON au processus Node.js."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Processus Node.js non démarré")
        
        async with self._lock:
            command_json = json.dumps(command) + "\n"
            _LOGGER.info("📤 Envoi de la commande au bridge Node.js: %s", command_json.strip())
            self.process.stdin.write(command_json.encode())
            await self.process.stdin.drain()

    async def _read_response(self, timeout: float = 10.0) -> dict[str, Any]:
        """Lit une réponse JSON du processus Node.js."""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Processus Node.js non démarré")
        
        try:
            line = await asyncio.wait_for(
                self.process.stdout.readline(), timeout=timeout
            )
            if not line:
                # Vérifier si le processus est toujours en cours
                if self.process and self.process.returncode is not None:
                    raise RuntimeError(
                        f"Processus Node.js terminé inattendu (code de retour: {self.process.returncode})"
                    )
                raise RuntimeError("Processus Node.js terminé inattendu (pas de réponse)")
            
            response_text = line.decode().strip()
            if not response_text:
                raise RuntimeError("Réponse vide du processus Node.js")
            
            response = json.loads(response_text)
            _LOGGER.info("📥 Réponse Node.js reçue: %s", response)
            return response
        except asyncio.TimeoutError:
            raise RuntimeError(f"Timeout lors de la lecture de la réponse (>{timeout}s)")
        except json.JSONDecodeError as e:
            _LOGGER.error("Erreur de décodage JSON Node.js: %s (ligne: %s)", e, line.decode().strip() if line else "vide")
            raise RuntimeError(f"Erreur de décodage JSON: {e}")
        except UnicodeDecodeError as e:
            _LOGGER.error("Erreur de décodage Unicode Node.js: %s", e)
            raise RuntimeError(f"Erreur de décodage Unicode: {e}")

    async def close(self) -> None:
        """Ferme la connexion."""
        if self.process:
            try:
                # Envoyer la commande de fermeture
                close_command = {"action": "close"}
                await self._send_command(close_command)
                
                # Attendre la réponse
                try:
                    await asyncio.wait_for(self._read_response(), timeout=2.0)
                except (asyncio.TimeoutError, RuntimeError):
                    pass
                
                # Terminer le processus
                if self.process.returncode is None:
                    self.process.terminate()
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self.process.kill()
                        await self.process.wait()
                
                _LOGGER.info("Bridge Node.js fermé")
            except Exception as e:
                _LOGGER.error("Erreur lors de la fermeture du bridge: %s", e)
            finally:
                self.process = None
                self._initialized = False


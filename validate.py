#!/usr/bin/env python3
"""Script de validation de l'intégration RFXCOM."""
import json
import os
import sys
from pathlib import Path

# Couleurs pour la sortie
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_file_exists(filepath: Path, description: str) -> bool:
    """Vérifie si un fichier existe."""
    if filepath.exists():
        print(f"{GREEN}✓{RESET} {description}: {filepath}")
        return True
    else:
        print(f"{RED}✗{RESET} {description}: {filepath} - MANQUANT")
        return False


def check_manifest() -> bool:
    """Vérifie le fichier manifest.json."""
    manifest_path = Path("custom_components/rfxcom/manifest.json")
    if not manifest_path.exists():
        print(f"{RED}✗{RESET} manifest.json introuvable")
        return False

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        required_fields = [
            "domain",
            "name",
            "version",
            "config_flow",
            "requirements",
        ]
        missing_fields = [field for field in required_fields if field not in manifest]

        if missing_fields:
            print(f"{RED}✗{RESET} Champs manquants dans manifest.json: {missing_fields}")
            return False

        if not manifest.get("config_flow"):
            print(f"{YELLOW}⚠{RESET} config_flow devrait être true pour l'interface graphique")
            return False

        print(f"{GREEN}✓{RESET} manifest.json valide")
        print(f"   - Domain: {manifest.get('domain')}")
        print(f"   - Version: {manifest.get('version')}")
        print(f"   - Config Flow: {manifest.get('config_flow')}")
        return True

    except json.JSONDecodeError as e:
        print(f"{RED}✗{RESET} Erreur de parsing JSON dans manifest.json: {e}")
        return False


def check_structure() -> bool:
    """Vérifie la structure des fichiers."""
    required_files = [
        ("custom_components/rfxcom/__init__.py", "Fichier d'initialisation"),
        ("custom_components/rfxcom/manifest.json", "Manifest"),
        ("custom_components/rfxcom/config_flow.py", "Flux de configuration"),
        ("custom_components/rfxcom/const.py", "Constantes"),
        ("custom_components/rfxcom/coordinator.py", "Coordinateur"),
        ("custom_components/rfxcom/switch.py", "Entités switch"),
        ("custom_components/rfxcom/services.py", "Services"),
        ("custom_components/rfxcom/services.yaml", "Définition des services"),
        ("custom_components/rfxcom/strings.json", "Traductions"),
        ("README.md", "Documentation README"),
        ("hacs.json", "Configuration HACS"),
    ]

    all_ok = True
    for filepath, description in required_files:
        if not check_file_exists(Path(filepath), description):
            all_ok = False

    return all_ok


def check_imports() -> bool:
    """Vérifie que les imports sont corrects."""
    import_path = Path("custom_components/rfxcom/__init__.py")
    if not import_path.exists():
        return False

    try:
        with open(import_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_imports = [
            "from homeassistant.config_entries import ConfigEntry",
            "from homeassistant.core import HomeAssistant",
            "from .const import DOMAIN",
        ]

        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)

        if missing_imports:
            print(f"{RED}✗{RESET} Imports manquants dans __init__.py:")
            for imp in missing_imports:
                print(f"   - {imp}")
            return False

        print(f"{GREEN}✓{RESET} Imports corrects")
        return True

    except Exception as e:
        print(f"{RED}✗{RESET} Erreur lors de la vérification des imports: {e}")
        return False


def main():
    """Fonction principale de validation."""
    print("=" * 60)
    print("Validation de l'intégration RFXCOM pour Home Assistant")
    print("=" * 60)
    print()

    results = []

    print("1. Vérification de la structure des fichiers...")
    results.append(("Structure", check_structure()))
    print()

    print("2. Vérification du manifest.json...")
    results.append(("Manifest", check_manifest()))
    print()

    print("3. Vérification des imports...")
    results.append(("Imports", check_imports()))
    print()

    print("=" * 60)
    print("Résumé:")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = f"{GREEN}PASSÉ{RESET}" if result else f"{RED}ÉCHOUÉ{RESET}"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print(f"{GREEN}✓ Toutes les validations ont réussi !{RESET}")
        print()
        print("L'intégration est prête à être installée dans Home Assistant.")
        print("Elle apparaîtra automatiquement dans:")
        print("  Configuration > Intégrations > Ajouter une intégration")
        return 0
    else:
        print(f"{RED}✗ Certaines validations ont échoué.{RESET}")
        print("Veuillez corriger les erreurs avant d'installer.")
        return 1


if __name__ == "__main__":
    sys.exit(main())



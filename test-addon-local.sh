#!/bin/bash
# Script pour copier l'add-on dans Home Assistant local pour test

set -e

echo "📦 Installation de l'add-on RFXCOM Node.js Bridge dans Home Assistant local"
echo ""

# Vérifier que le répertoire ha_config existe
if [ ! -d "ha_config" ]; then
    echo "❌ Le répertoire ha_config n'existe pas"
    echo "   Lancez d'abord: ./docker-test.sh"
    exit 1
fi

# Créer le répertoire local_addons
mkdir -p ha_config/local_addons

# Copier l'add-on depuis le dépôt GitLab ou depuis addon/
ADDON_SOURCE=""
if [ -d "/Users/thibault.boulay/Documents/GitLab/rfxcom-nodejs-bridge-addon/rfxcom-nodejs-bridge" ]; then
    ADDON_SOURCE="/Users/thibault.boulay/Documents/GitLab/rfxcom-nodejs-bridge-addon/rfxcom-nodejs-bridge"
    echo "📁 Source: Dépôt GitLab"
elif [ -d "addon/rfxcom-nodejs-bridge" ]; then
    ADDON_SOURCE="addon/rfxcom-nodejs-bridge"
    echo "📁 Source: addon/rfxcom-nodejs-bridge"
else
    echo "❌ Impossible de trouver l'add-on"
    echo "   Cherché dans:"
    echo "   - /Users/thibault.boulay/Documents/GitLab/rfxcom-nodejs-bridge-addon/rfxcom-nodejs-bridge"
    echo "   - addon/rfxcom-nodejs-bridge"
    exit 1
fi

ADDON_DEST="ha_config/local_addons/rfxcom-nodejs-bridge"

echo "📋 Copie de l'add-on..."
echo "   Source: $ADDON_SOURCE"
echo "   Destination: $ADDON_DEST"
echo ""

# Supprimer l'ancien add-on s'il existe
if [ -d "$ADDON_DEST" ]; then
    echo "🗑️  Suppression de l'ancien add-on..."
    rm -rf "$ADDON_DEST"
fi

# Copier l'add-on
cp -r "$ADDON_SOURCE" "$ADDON_DEST"

echo "✅ Add-on copié dans $ADDON_DEST"
echo ""

# Vérifier que config.yaml est présent
if [ ! -f "$ADDON_DEST/config.yaml" ]; then
    echo "⚠️  ATTENTION: config.yaml non trouvé!"
    echo "   Vérifiez que l'add-on a bien été converti en YAML"
    exit 1
fi

echo "📋 Fichiers de l'add-on:"
ls -la "$ADDON_DEST"
echo ""

echo "🔄 Redémarrage de Home Assistant..."
if docker compose version &> /dev/null; then
    docker compose restart homeassistant
else
    docker-compose restart homeassistant
fi

echo ""
echo "⏳ Attente du redémarrage..."
sleep 5

echo ""
echo "✅ Installation terminée!"
echo ""
echo "💡 Prochaines étapes:"
echo "   1. Ouvrez http://localhost:8123"
echo "   2. Allez dans Paramètres > Modules complémentaires"
echo "   3. Cliquez sur 'Add-on store' (bouton en bas à droite)"
echo "   4. Cliquez sur les trois points (⋮) en haut à droite"
echo "   5. Cliquez sur 'Rechercher des mises à jour'"
echo "   6. L'add-on devrait apparaître dans 'Local add-ons'"
echo ""
echo "📝 Pour voir les logs:"
echo "   docker compose logs -f homeassistant"


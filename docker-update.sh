#!/bin/bash
# Script pour mettre à jour l'intégration RFXCOM et redémarrer Home Assistant

set -e

echo "🔄 Mise à jour de l'intégration RFXCOM dans Home Assistant"
echo ""

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Vérifier que docker-compose est installé
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ docker-compose n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Détecter le nom du service depuis docker-compose.yml
SERVICE_NAME="homeassistant"
CONTAINER_NAME="homeassistant-test"

# Vérifier que le conteneur existe
if ! docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Le conteneur ${CONTAINER_NAME} n'existe pas."
    echo "   Lancez d'abord: ./docker-test.sh ou docker compose up -d"
    exit 1
fi

# Vérifier que le conteneur est en cours d'exécution
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠️  Le conteneur n'est pas en cours d'exécution. Démarrage..."
    if docker compose version &> /dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi
    echo "✅ Conteneur démarré"
    echo ""
fi

# Vérifier que le lien symbolique existe pour le plugin
if [ ! -L ha_config/custom_components/rfxcom ] && [ ! -d ha_config/custom_components/rfxcom ]; then
    echo "📁 Création du lien symbolique pour custom_components/rfxcom..."
    mkdir -p ha_config/custom_components
    ln -sfn "$(pwd)/custom_components/rfxcom" ha_config/custom_components/rfxcom
    echo "✅ Lien symbolique créé pour le plugin"
    echo ""
fi

# Installer l'add-on RFXCOM Node.js Bridge depuis Git
ADDON_DEST="ha_config/local_addons/rfxcom-nodejs-bridge"
ADDON_GIT_URL="${RFXCOM_ADDON_GIT_URL:-https://github.com/loneObserver1/rfxcom-nodejs-bridge-addon.git}"

echo "📦 Installation de l'add-on RFXCOM Node.js Bridge..."
mkdir -p ha_config/local_addons

# Cloner le dépôt dans un répertoire temporaire
ADDON_TEMP_DIR="ha_config/local_addons/rfxcom-nodejs-bridge-temp"
rm -rf "$ADDON_TEMP_DIR"

# Si l'add-on existe déjà, vérifier s'il est un dépôt Git
if [ -d "$ADDON_DEST" ] && [ -d "$ADDON_DEST/.git" ]; then
    echo "   Add-on déjà installé depuis Git, mise à jour..."
    cd "$ADDON_DEST"
    git pull || echo "   ⚠️  Erreur lors de la mise à jour Git, continuons..."
    cd - > /dev/null
else
    echo "   Clonage du dépôt Git de l'add-on..."
    git clone "$ADDON_GIT_URL" "$ADDON_TEMP_DIR" || {
        echo "   ⚠️  Erreur lors du clonage Git, tentative avec la source locale..."
        ADDON_SOURCE="addon/rfxcom-nodejs-bridge"
        if [ -d "$ADDON_SOURCE" ]; then
            # Créer la structure correcte pour l'add-on local
            mkdir -p "$ADDON_DEST"
            cp -r "$ADDON_SOURCE"/* "$ADDON_DEST/"
            echo "   ✅ Add-on installé depuis la source locale"
        else
            echo "   ❌ Impossible d'installer l'add-on (Git et source locale introuvables)"
            echo "   L'add-on devra être installé manuellement."
        fi
        ADDON_TEMP_DIR=""
    }
    
    # Si le clonage Git a réussi, copier le contenu du dossier rfxcom-nodejs-bridge/
    if [ -d "$ADDON_TEMP_DIR" ] && [ -d "$ADDON_TEMP_DIR/rfxcom-nodejs-bridge" ]; then
        echo "   Copie de l'add-on depuis le dépôt Git..."
        rm -rf "$ADDON_DEST"
        cp -r "$ADDON_TEMP_DIR/rfxcom-nodejs-bridge" "$ADDON_DEST"
        rm -rf "$ADDON_TEMP_DIR"
        echo "   ✅ Add-on installé depuis Git"
    fi
fi

if [ -d "$ADDON_DEST" ]; then
    echo "✅ Add-on installé dans $ADDON_DEST"
    echo ""
    echo "💡 Pour utiliser l'add-on dans Home Assistant:"
    echo "   1. Allez dans Paramètres > Modules complémentaires > Dépôts de modules complémentaires"
    echo "   2. Ajoutez le dépôt: $ADDON_GIT_URL"
    echo "   3. Ou installez l'add-on manuellement depuis $ADDON_DEST"
    echo "   4. Installez et démarrez l'add-on 'RFXCOM Node.js Bridge'"
    echo ""
fi

echo "🔄 Redémarrage du conteneur Home Assistant..."
echo ""

# Redémarrer le conteneur
if docker compose version &> /dev/null; then
    docker compose restart "$SERVICE_NAME"
else
    docker-compose restart "$SERVICE_NAME"
fi

echo "⏳ Attente du redémarrage de Home Assistant..."
sleep 5

# Afficher les logs récents
echo ""
echo "📋 Logs récents (dernières 30 lignes):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker compose version &> /dev/null; then
    docker compose logs --tail=30 "$SERVICE_NAME" 2>&1 | tail -30
else
    docker-compose logs --tail=30 "$SERVICE_NAME" 2>&1 | tail -30
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier que Home Assistant est accessible
echo "🔍 Vérification de l'accessibilité..."
for i in {1..12}; do
    sleep 2
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8123 2>&1 || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
        echo "✅ Home Assistant est accessible sur http://localhost:8123"
        echo ""
        echo "📝 Pour voir les logs en temps réel:"
        echo "   docker-compose logs -f homeassistant"
        echo ""
        echo "💡 Note: Les modifications de code sont automatiquement disponibles"
        echo "   car le répertoire custom_components est monté comme volume."
        echo "   Home Assistant rechargera l'intégration au prochain redémarrage."
        exit 0
    fi
    echo -n "."
done

echo ""
echo "⚠️  Home Assistant prend plus de temps que prévu à redémarrer"
echo "   Vérifiez les logs avec: docker-compose logs -f homeassistant"
echo "   Ou ouvrez http://localhost:8123 dans votre navigateur"
echo ""



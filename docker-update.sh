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

# Vérifier que le conteneur existe
if ! docker ps -a --format '{{.Names}}' | grep -q "^homeassistant-test$"; then
    echo "❌ Le conteneur homeassistant-test n'existe pas."
    echo "   Lancez d'abord: ./docker-test.sh"
    exit 1
fi

# Vérifier que le conteneur est en cours d'exécution
if ! docker ps --format '{{.Names}}' | grep -q "^homeassistant-test$"; then
    echo "⚠️  Le conteneur n'est pas en cours d'exécution. Démarrage..."
    if docker compose version &> /dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi
    echo "✅ Conteneur démarré"
    echo ""
fi

# Vérifier que le lien symbolique existe
if [ ! -L ha_config/custom_components/rfxcom ] && [ ! -d ha_config/custom_components/rfxcom ]; then
    echo "📁 Création du lien symbolique pour custom_components/rfxcom..."
    mkdir -p ha_config/custom_components
    ln -sfn "$(pwd)/custom_components/rfxcom" ha_config/custom_components/rfxcom
    echo "✅ Lien symbolique créé"
    echo ""
fi

echo "🔄 Redémarrage du conteneur Home Assistant..."
echo ""

# Redémarrer le conteneur
if docker compose version &> /dev/null; then
    docker compose restart homeassistant
else
    docker-compose restart homeassistant
fi

echo "⏳ Attente du redémarrage de Home Assistant..."
sleep 5

# Afficher les logs récents
echo ""
echo "📋 Logs récents (dernières 30 lignes):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker compose version &> /dev/null; then
    docker compose logs --tail=30 homeassistant 2>&1 | tail -30
else
    docker-compose logs --tail=30 homeassistant 2>&1 | tail -30
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



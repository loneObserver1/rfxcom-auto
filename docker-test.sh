#!/bin/bash
# Script pour lancer Home Assistant dans Docker pour tester l'intégration RFXCOM

set -e

echo "🚀 Démarrage de Home Assistant dans Docker pour tester RFXCOM"
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

# Créer le répertoire de configuration si nécessaire
mkdir -p ha_config

# Créer un lien symbolique pour les custom_components si nécessaire
if [ ! -L ha_config/custom_components/rfxcom ] && [ ! -d ha_config/custom_components/rfxcom ]; then
    mkdir -p ha_config/custom_components
    # Utiliser le chemin absolu pour le lien symbolique
    ABS_PATH=$(cd "$(dirname "$0")" && pwd)
    ln -sfn "$ABS_PATH/custom_components/rfxcom" ha_config/custom_components/rfxcom
    echo "✅ Lien symbolique créé pour custom_components/rfxcom"
fi

# Démarrer Home Assistant
echo "📦 Démarrage du conteneur Home Assistant..."
echo ""
echo "🌐 Home Assistant sera accessible sur: http://localhost:8123"
echo "📁 Configuration: ./ha_config"
echo "🔌 Custom components: ./custom_components"
echo ""
echo "Pour arrêter: docker-compose down"
echo "Pour voir les logs: docker-compose logs -f"
echo ""

# Utiliser docker compose (nouvelle version) ou docker-compose (ancienne version)
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo ""
echo "⏳ Attente du démarrage de Home Assistant..."
echo "   (cela peut prendre quelques minutes lors du premier démarrage)"
echo ""

# Attendre que Home Assistant soit prêt
timeout=300
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -s http://localhost:8123 > /dev/null 2>&1; then
        echo ""
        echo "✅ Home Assistant est prêt !"
        echo "🌐 Ouvrez http://localhost:8123 dans votre navigateur"
        echo ""
        echo "📋 Prochaines étapes:"
        echo "   1. Créez un compte administrateur"
        echo "   2. Allez dans Configuration > Intégrations"
        echo "   3. Ajoutez l'intégration RFXCOM"
        echo ""
        exit 0
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo -n "."
done

echo ""
echo "⚠️  Home Assistant prend plus de temps que prévu à démarrer"
echo "   Vérifiez les logs avec: docker-compose logs -f"
echo "   Ou ouvrez http://localhost:8123 dans votre navigateur"
echo ""


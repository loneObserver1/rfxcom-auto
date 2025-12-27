#!/bin/bash
# Script pour vérifier l'accessibilité du port série RFXCOM dans Docker

set -e

echo "🔍 Vérification de l'accessibilité du port série RFXCOM"
echo ""

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé."
    exit 1
fi

# Vérifier que le conteneur existe
if ! docker ps -a --format '{{.Names}}' | grep -q "^homeassistant-test$"; then
    echo "❌ Le conteneur homeassistant-test n'existe pas."
    exit 1
fi

echo "=== 1. Périphériques USB sur l'hôte macOS ==="
echo ""

# Chercher les périphériques RFXCOM
RFXCOM_DEVICE=$(ls -1 /dev/cu.* 2>/dev/null | grep -i usb | head -1)
if [ -n "$RFXCOM_DEVICE" ]; then
    echo "✅ RFXCOM détecté: $RFXCOM_DEVICE"
    
    # Obtenir les infos du périphérique
    DEVICE_INFO=$(ioreg -p IOUSB -l -w 0 2>&1 | grep -A 10 -i "rfxcom" | head -15)
    if [ -n "$DEVICE_INFO" ]; then
        echo ""
        echo "📱 Informations du périphérique:"
        echo "$DEVICE_INFO" | grep -E "(USB Vendor Name|kUSBProductString|USB Serial Number)" | sed 's/^/   /'
    fi
else
    echo "❌ Aucun périphérique RFXCOM détecté dans /dev/cu.*"
    echo "   Vérifiez que le périphérique est branché et reconnu par macOS"
fi

echo ""
echo "=== 2. Périphériques dans le conteneur Docker ==="
echo ""

# Vérifier dans le conteneur
if docker ps --format '{{.Names}}' | grep -q "^homeassistant-test$"; then
    CONTAINER_DEVICES=$(docker exec homeassistant-test ls -1 /dev/ttyUSB* /dev/ttyACM* /dev/cu.* 2>/dev/null | head -10)
    
    if [ -n "$CONTAINER_DEVICES" ]; then
        echo "✅ Périphériques série détectés dans le conteneur:"
        echo "$CONTAINER_DEVICES" | sed 's/^/   /'
    else
        echo "⚠️  Aucun périphérique série détecté dans le conteneur"
    fi
    
    # Vérifier si le montage /dev fonctionne
    echo ""
    echo "📁 Contenu de /dev dans le conteneur (premiers fichiers):"
    docker exec homeassistant-test ls -1 /dev/ | head -20 | sed 's/^/   /'
else
    echo "❌ Le conteneur n'est pas en cours d'exécution"
fi

echo ""
echo "=== 3. Solutions possibles ==="
echo ""

if [ -n "$RFXCOM_DEVICE" ]; then
    echo "🔧 Option 1: Utiliser la connexion réseau (si votre RFXCOM le supporte)"
    echo "   Configurez l'intégration avec l'option 'Network' dans Home Assistant"
    echo ""
    
    echo "🔧 Option 2: Utiliser Docker Desktop pour partager le périphérique USB"
    echo "   1. Ouvrez Docker Desktop"
    echo "   2. Allez dans Settings > Resources > USB"
    echo "   3. Activez le partage USB et sélectionnez votre RFXCOM"
    echo "   4. Redémarrez le conteneur: ./docker-update.sh"
    echo ""
    
    echo "🔧 Option 3: Utiliser socat pour créer un tunnel (avancé)"
    echo "   Installez socat et créez un tunnel entre le port macOS et le conteneur"
    echo ""
    
    echo "📝 Note: Sur macOS, le montage direct de /dev ne fonctionne pas"
    echo "   car Docker Desktop utilise une VM Linux. Les périphériques USB"
    echo "   doivent être partagés via Docker Desktop ou via réseau."
else
    echo "⚠️  Aucun périphérique RFXCOM détecté"
    echo "   Vérifiez que le périphérique est branché et reconnu par macOS"
fi

echo ""
echo "=== 4. Vérification de la configuration Docker ==="
echo ""

if [ -f "docker-compose.yml" ]; then
    echo "📄 Configuration actuelle dans docker-compose.yml:"
    grep -A 2 "volumes:" docker-compose.yml | grep "/dev" | sed 's/^/   /' || echo "   Aucun montage /dev configuré"
else
    echo "❌ Fichier docker-compose.yml non trouvé"
fi

echo ""


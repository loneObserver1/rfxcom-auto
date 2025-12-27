#!/bin/bash
# Script pour configurer l'accès USB au RFXCOM dans Docker sur macOS

set -e

echo "🔧 Configuration de l'accès USB RFXCOM pour Docker"
echo ""

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé."
    exit 1
fi

# Détecter le périphérique RFXCOM
RFXCOM_CU=$(ls -1 /dev/cu.usbserial-* 2>/dev/null | head -1)
RFXCOM_TTY=$(ls -1 /dev/tty.usbserial-* 2>/dev/null | head -1)

if [ -z "$RFXCOM_CU" ] && [ -z "$RFXCOM_TTY" ]; then
    echo "❌ Aucun périphérique RFXCOM détecté"
    echo "   Vérifiez que le périphérique est branché"
    exit 1
fi

if [ -n "$RFXCOM_CU" ]; then
    RFXCOM_DEVICE="$RFXCOM_CU"
    echo "✅ RFXCOM détecté: $RFXCOM_DEVICE"
else
    RFXCOM_DEVICE="$RFXCOM_TTY"
    echo "✅ RFXCOM détecté: $RFXCOM_DEVICE"
fi

echo ""
echo "⚠️  IMPORTANT: Sur macOS, Docker Desktop ne peut pas accéder directement"
echo "   aux périphériques série macOS (/dev/cu.* ou /dev/tty.*)"
echo ""
echo "📋 Solutions disponibles:"
echo ""
echo "1️⃣  Utiliser Docker Desktop USB Passthrough (RECOMMANDÉ)"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   1. Ouvrez Docker Desktop"
echo "   2. Allez dans: Settings (⚙️) > Resources > USB"
echo "   3. Activez 'Enable USB device sharing'"
echo "   4. Cliquez sur 'Add USB device'"
echo "   5. Sélectionnez votre RFXCOM (RFXtrx433)"
echo "   6. Redémarrez le conteneur: ./docker-update.sh"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "2️⃣  Utiliser la connexion réseau (si votre RFXCOM le supporte)"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Si vous avez un RFXtrx433E avec connexion Ethernet:"
echo "   - Configurez l'intégration avec l'option 'Network' dans Home Assistant"
echo "   - Utilisez l'adresse IP et le port du RFXCOM"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "3️⃣  Utiliser socat pour créer un tunnel (AVANCÉ)"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Installez socat: brew install socat"
echo "   Créez un tunnel TCP vers le port série"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier si Docker Desktop USB est disponible
if docker info 2>&1 | grep -q "usb"; then
    echo "✅ Docker Desktop semble supporter USB"
else
    echo "⚠️  Docker Desktop USB passthrough peut ne pas être disponible"
    echo "   Vérifiez la version de Docker Desktop (nécessite une version récente)"
fi

echo ""
echo "📝 Après avoir configuré Docker Desktop USB:"
echo "   1. Redémarrez le conteneur: ./docker-update.sh"
echo "   2. Vérifiez l'accessibilité: ./docker-check-usb.sh"
echo ""


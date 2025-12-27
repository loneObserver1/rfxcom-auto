#!/bin/bash
# Script pour créer un tunnel TCP vers le port série RFXCOM
# Cela permet d'accéder au port série depuis le conteneur Docker via TCP

set -e

# Détecter automatiquement le port RFXCOM
RFXCOM_PORT=$(ls -1 /dev/cu.usbserial-* 2>/dev/null | head -1)
if [ -z "$RFXCOM_PORT" ]; then
    RFXCOM_PORT=$(ls -1 /dev/tty.usbserial-* 2>/dev/null | head -1)
fi

TCP_PORT=8889

echo "🌉 Création d'un tunnel TCP vers le port série RFXCOM"
echo ""

# Vérifier que socat est installé
if ! command -v socat &> /dev/null; then
    echo "❌ socat n'est pas installé"
    echo "   Installation en cours..."
    if command -v brew &> /dev/null; then
        brew install socat
    else
        echo "   Veuillez installer Homebrew puis: brew install socat"
        exit 1
    fi
fi

# Vérifier que le périphérique existe
if [ -z "$RFXCOM_PORT" ] || [ ! -e "$RFXCOM_PORT" ]; then
    echo "❌ Aucun périphérique RFXCOM détecté"
    echo "   Ports recherchés: /dev/cu.usbserial-* ou /dev/tty.usbserial-*"
    echo "   Vérifiez que le RFXCOM est branché et reconnu par macOS"
    echo ""
    echo "Ports disponibles:"
    ls -1 /dev/cu.* /dev/tty.* 2>/dev/null | grep -i usb | head -5 || echo "   Aucun port USB trouvé"
    exit 1
fi

echo "✅ Périphérique détecté: $RFXCOM_PORT"
echo "🌐 Tunnel TCP: localhost:$TCP_PORT -> $RFXCOM_PORT"
echo ""

# Vérifier si un tunnel est déjà en cours
if lsof -Pi :$TCP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Un tunnel est déjà en cours sur le port $TCP_PORT"
    echo "   Arrêt du tunnel existant..."
    pkill -f "socat.*TCP-LISTEN:$TCP_PORT" || true
    sleep 1
fi

echo "🚀 Démarrage du tunnel en arrière-plan..."
echo ""

# Démarrer le tunnel en arrière-plan avec logging
# Utiliser fork pour permettre plusieurs connexions (requis pour TCP-LISTEN)
# Ajouter nodelay pour envoyer immédiatement les données
# Utiliser b38400 (baudrate standard RFXCOM) au lieu de b115200
socat -d -d TCP-LISTEN:$TCP_PORT,reuseaddr,fork,bind=0.0.0.0,nodelay FILE:$RFXCOM_PORT,nonblock,raw,echo=0,b38400 > /tmp/rfxcom-tunnel.log 2>&1 &

TUNNEL_PID=$!
sleep 1

# Vérifier que le tunnel a démarré
if kill -0 $TUNNEL_PID 2>/dev/null; then
    echo "✅ Tunnel démarré avec succès (PID: $TUNNEL_PID)"
    echo ""
    echo "📝 Configuration dans Home Assistant:"
    echo "   1. Allez dans Configuration > Intégrations"
    echo "   2. Ajoutez l'intégration RFXCOM"
    echo "   3. Choisissez 'Network' (Réseau)"
    echo "   4. Host: host.docker.internal"
    echo "   5. Port: $TCP_PORT"
    echo ""
    echo "📋 Commandes utiles:"
    echo "   Voir les logs: tail -f /tmp/rfxcom-tunnel.log"
    echo "   Arrêter: kill $TUNNEL_PID"
    echo "   Arrêter (tous): pkill -f 'socat.*TCP-LISTEN:$TCP_PORT'"
    echo ""
    echo "💡 Le tunnel restera actif jusqu'à ce que vous l'arrêtiez"
    echo "   Pour le démarrer au démarrage, ajoutez-le à votre ~/.zshrc ou créez un service"
    echo ""
else
    echo "❌ Erreur lors du démarrage du tunnel"
    echo "   Vérifiez les logs: cat /tmp/rfxcom-tunnel.log"
    exit 1
fi

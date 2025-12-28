# Vérification de l'add-on RFXCOM Node.js Bridge

Ce guide explique comment vérifier que l'add-on RFXCOM Node.js Bridge est correctement installé et fonctionne.

## Méthode 1: Interface Home Assistant (Recommandé)

1. **Accédez à l'interface Home Assistant**
   - Ouvrez votre navigateur et allez sur `http://localhost:8123` (ou l'URL de votre Home Assistant)

2. **Allez dans les Modules complémentaires**
   - Cliquez sur **Paramètres** (icône d'engrenage en bas à gauche)
   - Cliquez sur **Modules complémentaires** dans le menu de gauche

3. **Recherchez l'add-on**
   - Cherchez **"RFXCOM Node.js Bridge"** dans la liste des add-ons
   - Ou utilisez la barre de recherche en haut

4. **Vérifiez l'état**
   - L'état doit être **"Running"** (En cours d'exécution)
   - Si l'état est **"Stopped"** (Arrêté), cliquez sur **"Démarrer"**
   - Si l'add-on n'apparaît pas, il n'est pas installé

5. **Consultez les logs**
   - Cliquez sur l'add-on pour ouvrir sa page
   - Cliquez sur l'onglet **"Logs"**
   - Vous devriez voir des messages comme:
     ```
     🚀 Serveur RFXCOM Node.js Bridge démarré sur le port 8888
     📡 Port série: /dev/ttyUSB0
     ✅ RFXCOM initialisé sur /dev/ttyUSB0
     ```

## Méthode 2: Vérification via les logs Home Assistant

1. **Accédez aux logs**
   - Allez dans **Paramètres > Système > Logs**
   - Ou utilisez la commande: `docker compose logs homeassistant | grep -i rfxcom`

2. **Recherchez les messages de connexion**
   - Messages de succès:
     ```
     ✅ Add-on RFXCOM Node.js Bridge connecté: port=/dev/ttyUSB0, initialisé=True
     ```
   - Messages d'erreur:
     ```
     ❌ Impossible de se connecter à l'add-on RFXCOM Node.js Bridge
     ```

## Méthode 3: Vérification HTTP directe

1. **Testez l'endpoint health**
   ```bash
   curl http://localhost:8888/health
   ```

2. **Réponse attendue (si l'add-on fonctionne)**
   ```json
   {
     "status": "ok",
     "initialized": true,
     "port": "/dev/ttyUSB0"
   }
   ```

3. **Si vous obtenez une erreur de connexion**
   - L'add-on n'est pas démarré
   - Le port API est incorrect
   - L'add-on n'est pas installé

## Méthode 4: Vérification depuis le plugin Python

Le plugin Python vérifie automatiquement la disponibilité de l'add-on au démarrage. Les logs affichent:

- **Succès:**
  ```
  ✅ Add-on RFXCOM Node.js Bridge connecté: port=/dev/ttyUSB0, initialisé=True
  ```

- **Erreur:**
  ```
  ❌ Impossible de se connecter à l'add-on RFXCOM Node.js Bridge
  Statut: connection_error
  Erreur: Cannot connect to host localhost:8888
  ```

## Dépannage

### L'add-on n'apparaît pas dans la liste

1. Vérifiez que l'add-on est installé dans `ha_config/local_addons/rfxcom-nodejs-bridge`
2. Vérifiez que le fichier `config.json` est présent
3. Redémarrez Home Assistant

### L'add-on est arrêté et ne démarre pas

1. Consultez les logs de l'add-on pour voir l'erreur
2. Vérifiez que le port série est correctement configuré
3. Vérifiez que le port série existe: `ls -la /dev/ttyUSB0` (ou le port configuré)

### L'add-on démarre mais le plugin ne peut pas se connecter

1. Vérifiez que le port API est correct (par défaut: 8888)
2. Vérifiez que le port n'est pas bloqué par un firewall
3. Testez manuellement avec `curl http://localhost:8888/health`

### Erreur "Cannot connect to host"

1. Vérifiez que l'add-on est bien démarré
2. Vérifiez que le port API dans l'add-on correspond à celui utilisé par le plugin (8888 par défaut)
3. Si vous utilisez Docker, vérifiez que le port est bien exposé

## Commandes utiles

### Vérifier si l'add-on répond
```bash
curl http://localhost:8888/health
```

### Voir les logs de l'add-on
```bash
# Depuis Home Assistant
docker compose logs homeassistant | grep -i "rfxcom\|addon"

# Ou depuis l'interface Home Assistant
# Paramètres > Modules complémentaires > RFXCOM Node.js Bridge > Logs
```

### Vérifier les fichiers de l'add-on
```bash
ls -la ha_config/local_addons/rfxcom-nodejs-bridge/
```

### Tester une commande via l'API
```bash
curl -X POST http://localhost:8888/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "AC",
    "device_id": "02382C82",
    "unit_code": 1,
    "command": "on"
  }'
```


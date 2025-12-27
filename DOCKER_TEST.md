# Test de l'intégration RFXCOM avec Docker

Ce guide explique comment tester l'intégration RFXCOM dans Home Assistant en utilisant Docker.

## Prérequis

- Docker installé
- docker-compose installé (ou Docker Compose V2)

## Démarrage rapide

### Méthode 1: Script automatique (recommandé)

```bash
./docker-test.sh
```

Le script va :
1. Vérifier que Docker est installé
2. Créer le répertoire de configuration
3. Créer un lien symbolique vers les custom_components
4. Démarrer Home Assistant
5. Attendre que Home Assistant soit prêt

### Méthode 2: Docker Compose manuel

```bash
# Créer le répertoire de configuration
mkdir -p ha_config

# Créer le lien symbolique pour les custom_components
mkdir -p ha_config/custom_components
ln -sfn "$(pwd)/custom_components/rfxcom" ha_config/custom_components/rfxcom

# Démarrer Home Assistant
docker-compose up -d

# Voir les logs
docker-compose logs -f
```

## Accès à Home Assistant

Une fois démarré, Home Assistant est accessible sur :
- **URL**: http://localhost:8123
- **Configuration**: `./ha_config`

## Commandes utiles

### Voir les logs
```bash
docker-compose logs -f
```

### Arrêter Home Assistant
```bash
docker-compose down
```

### Redémarrer Home Assistant
```bash
docker-compose restart
```

### Accéder au shell du conteneur
```bash
docker exec -it homeassistant-test bash
```

### Vérifier que l'intégration est chargée
```bash
docker-compose logs | grep -i rfxcom
```

## Configuration de l'intégration

1. Ouvrez http://localhost:8123 dans votre navigateur
2. Créez un compte administrateur (première fois)
3. Allez dans **Configuration > Intégrations**
4. Cliquez sur **Ajouter une intégration**
5. Recherchez **RFXCOM**
6. Configurez votre port série ou connexion réseau

## Test sans matériel RFXCOM

Pour tester sans matériel réel, vous pouvez :
1. Utiliser un port série virtuel (socat, etc.)
2. Tester uniquement l'interface de configuration
3. Utiliser les tests unitaires : `pytest tests/`

## Dépannage

### Le port 8123 est déjà utilisé
Modifiez le port dans `docker-compose.yml` :
```yaml
ports:
  - "8124:8123"  # Utilisez le port 8124 au lieu de 8123
```

### Les custom_components ne sont pas détectés
Vérifiez que le lien symbolique existe :
```bash
ls -la ha_config/custom_components/rfxcom
```

Si nécessaire, recréez-le :
```bash
rm -rf ha_config/custom_components/rfxcom
ln -sfn "$(pwd)/custom_components/rfxcom" ha_config/custom_components/rfxcom
```

### Home Assistant ne démarre pas
Vérifiez les logs :
```bash
docker-compose logs -f homeassistant
```

### Accès aux ports série
Le conteneur est configuré avec `privileged: true` et monte `/dev` pour accéder aux ports série. Si vous avez des problèmes, vérifiez les permissions :
```bash
ls -la /dev/ttyUSB*  # ou /dev/ttyACM*
```

## Nettoyage

Pour supprimer complètement l'installation Docker :
```bash
# Arrêter et supprimer le conteneur
docker-compose down

# Supprimer les volumes (⚠️ supprime la configuration)
docker-compose down -v

# Supprimer le répertoire de configuration
rm -rf ha_config
```

## Notes

- La première fois, Home Assistant télécharge l'image Docker (environ 1-2 GB)
- Le démarrage initial peut prendre plusieurs minutes
- Les données de configuration sont stockées dans `./ha_config`
- Les custom_components sont liés depuis le répertoire du projet


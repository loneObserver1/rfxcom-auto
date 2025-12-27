# Guide de test pour l'intégration RFXCOM

## Tests unitaires

### Installation des dépendances de test

```bash
pip install -r requirements-test.txt
```

### Exécution des tests

```bash
# Tous les tests
pytest

# Tests avec couverture
pytest --cov=custom_components/rfxcom --cov-report=html

# Tests spécifiques
pytest tests/test_coordinator.py
pytest tests/test_config_flow.py
pytest tests/test_switch.py
```

### Structure des tests

- `tests/test_coordinator.py` - Tests du coordinateur RFXCOM
- `tests/test_config_flow.py` - Tests du flux de configuration
- `tests/test_switch.py` - Tests des entités switch
- `tests/test_integration.py` - Tests d'intégration

## Tests manuels dans Home Assistant

### 1. Validation de la structure

```bash
python validate.py
```

### 2. Installation dans Home Assistant

1. Copiez le dossier `custom_components/rfxcom` dans votre Home Assistant
2. Redémarrez Home Assistant
3. Vérifiez les logs pour les erreurs

### 3. Configuration initiale

1. Allez dans **Configuration > Intégrations**
2. Cliquez sur **Ajouter une intégration**
3. Recherchez **RFXCOM**
4. Vous devriez voir l'intégration apparaître

### 4. Test de configuration USB

1. Sélectionnez **USB** comme type de connexion
2. Entrez le port série (ex: `/dev/ttyUSB0` ou `COM3`)
3. Sélectionnez la vitesse (38400 par défaut)
4. Validez

### 5. Test de configuration réseau

1. Sélectionnez **Réseau** comme type de connexion
2. Entrez l'adresse IP (ex: `192.168.1.100`)
3. Entrez le port (10001 par défaut)
4. Validez

### 6. Test d'ajout d'appareil

1. Allez dans **Configuration > Intégrations**
2. Cliquez sur votre intégration RFXCOM
3. Cliquez sur **Options**
4. Sélectionnez **Ajouter un appareil**
5. Remplissez:
   - Nom: "Test Switch"
   - Protocole: ARC
   - Code maison: A
   - Code unité: 1
6. Validez

### 7. Test de modification d'appareil

1. Dans les options, sélectionnez **Modifier: Test Switch**
2. Modifiez le nom ou les paramètres
3. Validez

### 8. Test de suppression d'appareil

1. Dans les options, sélectionnez **Supprimer: Test Switch**
2. Confirmez la suppression
3. Vérifiez que l'appareil a disparu

### 9. Test d'envoi de commande

1. L'appareil devrait apparaître comme un interrupteur
2. Testez ON/OFF depuis l'interface
3. Vérifiez les logs RFXCOM pour confirmer l'envoi

## Format des commandes RFXCOM

### Protocole ARC (Lighting1)

Format attendu: `07 10 01 62 41 01 01 00`

- `07` - Longueur
- `10` - Lighting1
- `01` - Subtype ARC
- `62` - Sequence number
- `41` - House code (A = 0x41)
- `01` - Unit code
- `01` - Command (ON=0x01, OFF=0x00)
- `00` - Signal level

### Vérification dans les logs

Les commandes envoyées sont loggées avec le format hexadécimal:
```
Commande envoyée: protocole=ARC, device=A/1, commande=ON, bytes=0710016241010100
```

## Dépannage

### Les tests échouent

- Vérifiez que toutes les dépendances sont installées
- Vérifiez que Python 3.9+ est utilisé
- Vérifiez les imports dans les fichiers de test

### L'intégration n'apparaît pas

- Vérifiez que le dossier est dans `custom_components/rfxcom`
- Vérifiez le fichier `manifest.json`
- Redémarrez Home Assistant
- Vérifiez les logs Home Assistant

### Les commandes ne fonctionnent pas

- Vérifiez la connexion USB/réseau
- Vérifiez les logs pour les erreurs
- Vérifiez le format des commandes dans les logs
- Testez avec un outil externe (minicom, telnet)


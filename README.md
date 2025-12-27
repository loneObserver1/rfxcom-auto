# Intégration RFXCOM pour Home Assistant

Intégration Home Assistant pour contrôler des appareils RFXCOM via les protocoles AC et ARC.

## Fonctionnalités

- Support des protocoles AC et ARC
- Gestion des interrupteurs ON/OFF
- Mode appairage pour ajouter facilement de nouveaux appareils
- Compatible avec HACS

## Installation

### Via HACS (recommandé)

1. Assurez-vous que [HACS](https://hacs.xyz) est installé
2. Allez dans HACS > Intégrations
3. Cliquez sur "Explorer et télécharger des dépôts"
4. Recherchez "RFXCOM"
5. Cliquez sur "Télécharger"
6. Redémarrez Home Assistant

### Installation manuelle

1. Copiez le dossier `custom_components/rfxcom` dans votre répertoire `custom_components` de Home Assistant
2. Redémarrez Home Assistant
3. Allez dans Configuration > Intégrations
4. Cliquez sur "Ajouter une intégration"
5. Recherchez "RFXCOM"

## Configuration

### Configuration initiale

1. Allez dans Configuration > Intégrations
2. Cliquez sur "Ajouter une intégration"
3. Recherchez "RFXCOM"
4. Entrez le port série (par exemple `/dev/ttyUSB0` ou `COM3`)
5. Sélectionnez la vitesse de transmission (par défaut: 38400)

### Ajouter un appareil

#### Méthode 1: Via le service d'appairage

1. Mettez votre interrupteur en mode appairage (suivez les instructions du fabricant)
2. Allez dans Configuration > Automatisations et scènes > Services
3. Recherchez le service `rfxcom.pair_device`
4. Remplissez les champs:
   - **Protocole**: AC ou ARC
   - **ID de l'appareil** (pour AC): L'ID de l'appareil (format hexadécimal)
   - **Code maison** (pour ARC): Le code maison (format hexadécimal)
   - **Code unité** (pour ARC): Le code unité (format hexadécimal)
   - **Nom**: Le nom de l'appareil dans Home Assistant
5. Appelez le service

#### Méthode 2: Via l'interface d'options

1. Allez dans Configuration > Intégrations
2. Cliquez sur votre intégration RFXCOM
3. Cliquez sur "Options"
4. Ajoutez un nouvel appareil avec les informations nécessaires

## Protocoles supportés

### Protocole AC
- Utilisé pour les appareils avec un ID unique (8 bytes)
- Format de l'ID: hexadécimal (ex: `01 02 03 04 05 06 07 08`)

### Protocole ARC
- Utilisé pour les appareils avec code maison et code unité
- Format: code maison (1 byte) + code unité (1 byte)
- Exemple: House code `0x01`, Unit code `0x02`

## Utilisation

Une fois configurés, vos appareils RFXCOM apparaîtront comme des interrupteurs dans Home Assistant. Vous pouvez les contrôler via:
- L'interface utilisateur
- Les automatisations
- Les scripts
- L'API

## Gestion des appareils

### Ajouter un appareil

1. Allez dans **Configuration > Intégrations**
2. Cliquez sur votre intégration RFXCOM
3. Cliquez sur **Options**
4. Sélectionnez **Ajouter un appareil**
5. Remplissez les informations selon le protocole:
   - **ARC**: Code maison (A-P) et Code unité (1-16)
   - **AC**: ID de l'appareil (format hexadécimal)

### Voir la liste des appareils

1. Allez dans **Configuration > Intégrations**
2. Cliquez sur votre intégration RFXCOM
3. Cliquez sur **Options**
4. La liste des appareils configurés s'affiche

### Modifier un appareil

1. Dans les options, sélectionnez **Modifier: [Nom de l'appareil]**
2. Modifiez les paramètres souhaités
3. Validez

### Supprimer un appareil

1. Dans les options, sélectionnez **Supprimer: [Nom de l'appareil]**
2. Confirmez la suppression

## Tests

Consultez [TESTING.md](TESTING.md) pour les instructions complètes de test.

### Tests unitaires

```bash
pip install -r requirements-test.txt
pytest
```

### Validation de la structure

```bash
python validate.py
```

## Dépannage

### Le port série n'est pas détecté

- Vérifiez que le port série est correct (Linux: `/dev/ttyUSB0`, Windows: `COM3`)
- Vérifiez les permissions du port série
- Assurez-vous que l'interface RFXCOM est bien connectée

### La connexion réseau ne fonctionne pas

- Vérifiez que l'adresse IP et le port sont corrects
- Vérifiez que le pare-feu autorise la connexion
- Testez la connexion avec `telnet` ou `nc`

### Les commandes ne fonctionnent pas

- Vérifiez que l'ID de l'appareil est correct
- Vérifiez que le protocole sélectionné correspond à votre appareil
- Vérifiez les logs Home Assistant pour plus d'informations
- Vérifiez le format des commandes dans les logs (format hexadécimal)

## Support

Pour signaler un problème ou proposer une amélioration, veuillez ouvrir une issue sur GitHub.

## Licence

MIT


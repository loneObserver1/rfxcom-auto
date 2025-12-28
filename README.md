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

## Guide des Protocoles

### Protocoles Lighting1 (House Code + Unit Code)

Ces protocoles utilisent un **Code Maison** (A-P) et un **Code Unité** (1-16) pour identifier les appareils.

| Protocole | Description | Type d'appareil | Champs requis |
|-----------|------------|-----------------|---------------|
| **ARC** | Atelier Radio Control | Switch, Cover | House Code (A-P), Unit Code (1-16) |
| **X10** | X10 Standard | Switch | House Code (A-P), Unit Code (1-16) |
| **ABICOD** | AbiCode | Switch | House Code (A-P), Unit Code (1-16) |
| **WAVEMAN** | WaveMan | Switch | House Code (A-P), Unit Code (1-16) |
| **EMW100** | EMW100 | Switch | House Code (A-P), Unit Code (1-16) |
| **IMPULS** | Impuls | Switch | House Code (A-P), Unit Code (1-16) |
| **RISINGSUN** | RisingSun | Switch | House Code (A-P), Unit Code (1-16) |
| **PHILIPS** | Philips | Switch | House Code (A-P), Unit Code (1-16) |
| **ENERGENIE** | Energenie | Switch | House Code (A-P), Unit Code (1-16) |
| **ENERGENIE_5** | Energenie 5 | Switch | House Code (A-P), Unit Code (1-16) |
| **COCOSTICK** | CocoStick | Switch | House Code (A-P), Unit Code (1-16) |

**Exemple ARC** :
- **House Code** : A
- **Unit Code** : 1
- **Usage** : Interrupteurs, prises, volets roulants

### Protocoles Lighting2 (Device ID)

Ces protocoles utilisent un **ID d'appareil** (hexadécimal) pour identifier les appareils.

| Protocole | Description | Type d'appareil | Champs requis |
|-----------|------------|-----------------|---------------|
| **AC** | AC (Lighting2) | Switch | Device ID (hex, ex: 02382C82), Unit Code (optionnel, défaut: 1) |
| **HOMEEASY_EU** | HomeEasy EU | Switch | Device ID (hex), Unit Code (optionnel) |
| **ANSLUT** | ANSLUT | Switch | Device ID (hex), Unit Code (optionnel) |
| **KAMBROOK** | Kambrook | Switch | Device ID (hex), Unit Code (optionnel) |

**Exemple AC** :
- **Device ID** : 02382C82 (ou 2382C82, le 0 sera ajouté automatiquement)
- **Unit Code** : 1 (par défaut) ou 2, 3, etc.
- **Usage** : Prises connectées, interrupteurs

### Protocoles Lighting3-6 (Device ID)

| Protocole | Description | Type d'appareil | Champs requis |
|-----------|------------|-----------------|---------------|
| **IKEA_KOPPLA** | IKEA Koppla (Lighting3) | Switch | Device ID (hex) |
| **PT2262** | PT2262 (Lighting4) | Switch | Device ID (hex) |
| **LIGHTWAVERF** | LightwaveRF (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **EMW100_GDO** | EMW100 GDO (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **BBSB** | BBSB (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **RSL** | RSL (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **LIVOLO** | Livolo (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **TRC02** | TRC02 (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **AOKE** | AOKE (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **RGB_TRC02** | RGB TRC02 (Lighting5) | Switch | Device ID (hex), Unit Code (optionnel) |
| **BLYSS** | Blyss (Lighting6) | Switch | Device ID (hex) |

### Protocoles Capteurs

| Protocole | Description | Type d'appareil | Champs requis | Détection |
|-----------|------------|-----------------|---------------|-----------|
| **TEMP_HUM** | Température/Humidité (TH13) | Sensor | Device ID (décimal ou hex) | Automatique (pas d'appairage nécessaire) |

**Exemple TEMP_HUM** :
- **Device ID** : 26627 (décimal) ou 6803 (hex)
- **Usage** : Capteurs de température/humidité (ex: Alecto WS1700)
- **Note** : Les sondes envoient leurs données automatiquement, pas besoin d'appairage

### Guide de Sélection

#### Pour un Interrupteur ou une Prise
1. Si votre appareil utilise un **Code Maison** (A-P) et un **Code Unité** (1-16) → **ARC** ou autre protocole Lighting1
2. Si votre appareil a un **ID unique** (hexadécimal) → **AC** ou autre protocole Lighting2-6

#### Pour un Volet Roulant
- Utilisez généralement le protocole **ARC** avec House Code + Unit Code
- Même si vous voyez une trame AC, le contrôle se fait souvent en ARC

#### Pour une Sonde Température/Humidité
- Utilisez le protocole **TEMP_HUM**
- Activez l'auto-registry → la sonde sera détectée automatiquement
- Ou ajoutez-la manuellement avec l'ID de l'appareil

### Appairage

#### Appairage Automatique (ARC)
- Génère automatiquement des codes non utilisés
- Fonctionne uniquement pour les switches et covers
- Nécessite de mettre l'appareil en mode appairage

#### Détection Automatique (TEMP_HUM)
- Les sondes sont détectées automatiquement quand elles envoient leurs données
- Pas besoin d'appairage
- Nécessite que l'auto-registry soit activé

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

Pour signaler un problème ou proposer une amélioration, veuillez ouvrir une issue sur [GitHub](https://github.com/loneObserver1/rfxcom-auto/issues).

## Licence

MIT


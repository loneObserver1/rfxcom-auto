# Table de Correspondance des Protocoles RFXCOM

Ce document liste les protocoles RFXCOM supportés et les types d'appareils associés.

## Protocoles Lighting1 (House Code + Unit Code)

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

### Exemple ARC
- **House Code** : A
- **Unit Code** : 1
- **Usage** : Interrupteurs, prises, volets roulants

## Protocoles Lighting2 (Device ID)

Ces protocoles utilisent un **ID d'appareil** (hexadécimal) pour identifier les appareils.

| Protocole | Description | Type d'appareil | Champs requis |
|-----------|------------|-----------------|---------------|
| **AC** | AC (Lighting2) | Switch | Device ID (hex, ex: 02382C82), Unit Code (optionnel, défaut: 1) |
| **HOMEEASY_EU** | HomeEasy EU | Switch | Device ID (hex), Unit Code (optionnel) |
| **ANSLUT** | ANSLUT | Switch | Device ID (hex), Unit Code (optionnel) |
| **KAMBROOK** | Kambrook | Switch | Device ID (hex), Unit Code (optionnel) |

### Exemple AC
- **Device ID** : 02382C82 (ou 2382C82, le 0 sera ajouté automatiquement)
- **Unit Code** : 1 (par défaut) ou 2, 3, etc.
- **Usage** : Prises connectées, interrupteurs

## Protocoles Lighting3-6 (Device ID)

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

## Protocoles Capteurs

| Protocole | Description | Type d'appareil | Champs requis | Détection |
|-----------|------------|-----------------|---------------|-----------|
| **TEMP_HUM** | Température/Humidité (TH13) | Sensor | Device ID (décimal ou hex) | Automatique (pas d'appairage nécessaire) |

### Exemple TEMP_HUM
- **Device ID** : 26627 (décimal) ou 6803 (hex)
- **Usage** : Capteurs de température/humidité (ex: Alecto WS1700)
- **Note** : Les sondes envoient leurs données automatiquement, pas besoin d'appairage

## Guide de Sélection

### Pour un Interrupteur ou une Prise
1. Si votre appareil utilise un **Code Maison** (A-P) et un **Code Unité** (1-16) → **ARC** ou autre protocole Lighting1
2. Si votre appareil a un **ID unique** (hexadécimal) → **AC** ou autre protocole Lighting2-6

### Pour un Volet Roulant
- Utilisez généralement le protocole **ARC** avec House Code + Unit Code
- Même si vous voyez une trame AC, le contrôle se fait souvent en ARC

### Pour une Sonde Température/Humidité
- Utilisez le protocole **TEMP_HUM**
- Activez l'auto-registry → la sonde sera détectée automatiquement
- Ou ajoutez-la manuellement avec l'ID de l'appareil

## Appairage

### Appairage Automatique (ARC)
- Génère automatiquement des codes non utilisés
- Fonctionne uniquement pour les switches et covers
- Nécessite de mettre l'appareil en mode appairage

### Détection Automatique (TEMP_HUM)
- Les sondes sont détectées automatiquement quand elles envoient leurs données
- Pas besoin d'appairage
- Nécessite que l'auto-registry soit activé

## Support

Pour plus d'informations, consultez la [documentation RFXCOM](https://www.rfxcom.com/).


# Support des Capteurs Température/Humidité RFXCOM

## Format du Paquet TEMP_HUM

### Exemple de Paquet
```
0A520D35680300D4270289
```

### Structure du Paquet

| Byte | Valeur | Description |
|------|--------|-------------|
| 0 | `0x0A` | Longueur (10 bytes) |
| 1 | `0x52` | Type: TEMP_HUM |
| 2 | `0x0D` | Subtype: TH13 (Alecto WS1700) |
| 3 | `0x35` | Sequence number (53) |
| 4-5 | `0x6803` | ID de l'appareil (26627 en décimal) |
| 6-7 | `0x00D4` | Température (212 = 21.2°C) |
| 8 | `0x27` | Humidité (39%) |
| 9 | `0x02` | Status (Dry) |
| 10 | `0x89` | Signal level (8) + Battery (OK=0x09) |

### Décodage

- **ID**: Big-endian sur 2 bytes
- **Température**: Big-endian sur 2 bytes, en dixièmes de degré (212 = 21.2°C)
- **Humidité**: 1 byte (0-100%)
- **Status**: 
  - `0x00` = Normal
  - `0x01` = Comfort
  - `0x02` = Dry
  - `0x03` = Wet
- **Signal/Battery**: 
  - Nibble haut (bits 7-4) = Signal level (0-15)
  - Nibble bas (bits 3-0) = Battery (0x09 = OK, autres = LOW)

## Fonctionnalités

### Réception Automatique

L'intégration reçoit automatiquement les paquets TEMP_HUM quand :
- L'auto-registry est activé
- Le coordinateur écoute les messages RFXCOM

### Parsing

Le coordinateur parse automatiquement :
- ID de l'appareil
- Température (°C)
- Humidité (%)
- Status
- Signal level
- État de la batterie

### Entités Créées

Pour chaque capteur TEMP_HUM détecté, deux entités sont créées :
1. **Capteur de température** (`sensor.rfxcom_xxx_temperature`)
2. **Capteur d'humidité** (`sensor.rfxcom_xxx_humidity`)

### Mise à Jour Automatique

Les valeurs sont mises à jour automatiquement quand :
- Un nouveau paquet est reçu pour le capteur
- Le coordinateur met à jour les données
- Les entités sont notifiées du changement

## Utilisation

### Auto-Registry

1. Activez l'auto-registry dans les options
2. Le capteur envoie ses données
3. Le capteur est automatiquement détecté et enregistré
4. Les entités température et humidité sont créées

### Ajout Manuel

1. Allez dans Configuration > Intégrations > RFXCOM > Options
2. Ajoutez un appareil
3. Sélectionnez le protocole **TEMP_HUM**
4. Entrez l'ID de l'appareil (ex: `26627`)
5. Les entités seront créées

### Service d'Appairage

```yaml
service: rfxcom.pair_device
data:
  protocol: TEMP_HUM
  device_id: "26627"
  name: "Capteur Salon"
```

## Logs de Debug

Quand un paquet TEMP_HUM est reçu :

```
DEBUG: Paquet complet reçu: 10 bytes, hex=0a520d35680300d4270289
DEBUG: Parsing du paquet: 0a520d35680300d4270289
DEBUG: Type de paquet: 0x52
DEBUG: TEMP_HUM subtype: 0x0D
DEBUG: TEMP_HUM paquet: device_id=26627, temp=21.2°C, hum=39%, status=Dry, signal=8, battery=OK
DEBUG: TEMP_HUM appareil détecté: {'protocol': 'TEMP_HUM', 'device_id': '26627', ...}
DEBUG: Appareil déjà connu, mise à jour des données: TEMP_HUM_26627
DEBUG: Température mise à jour: RFXCOM Temp/Hum 26627 Temperature = 21.2°C
DEBUG: Humidité mise à jour: RFXCOM Temp/Hum 26627 Humidity = 39%
```

## Exemple de Paquet Reçu

D'après vos logs :
```
27/12/2025 06:31:34:194= 0A520D35680300D4270289
Packettype    = TEMP_HUM
subtype       = TH13 - Alecto WS1700 and compatibles
channel 3
Sequence nbr  = 53
ID            = 6803 decimal:26627
Temperature   = 21,2 °C
Humidity      = 39
Status        = Dry
Signal level  = 8  -56dBm
Battery       = OK
```

Ce paquet sera automatiquement parsé et les valeurs seront disponibles dans Home Assistant !


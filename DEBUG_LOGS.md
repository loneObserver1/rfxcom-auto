# Guide des Logs de Debug - RFXCOM

## Activation des Logs de Debug

Pour activer les logs de debug dans Home Assistant, ajoutez dans `configuration.yaml` :

```yaml
logger:
  default: info
  logs:
    custom_components.rfxcom: debug
    custom_components.rfxcom.coordinator: debug
    custom_components.rfxcom.switch: debug
    custom_components.rfxcom.services: debug
```

## Types de Logs

### Niveau INFO
- Événements importants (connexion, déconnexion, détection d'appareils)
- Erreurs critiques
- Actions utilisateur (appairage, enregistrement)

### Niveau DEBUG
- Détails de configuration
- Paquets RFXCOM reçus/envoyés
- Parsing de paquets
- États internes
- Flux de données

## Logs par Composant

### Coordinator (`coordinator.py`)

#### Configuration
- `Configuration connexion USB: port=..., baudrate=...`
- `Configuration connexion réseau: host=..., port=...`
- `Port série configuré: timeout=1s, write_timeout=1s`
- `Socket réseau connectée avec succès`
- `Auto-registry activé, démarrage de la boucle de réception`
- `Auto-registry désactivé, pas de réception de messages`

#### Envoi de Commandes
- `Envoi commande: protocole=..., device_id=..., command=..., house_code=..., unit_code=...`
- `Port série vérifié: ouvert=...`
- `Socket réseau vérifiée: présente=...`
- `Construction commande AC: device_id=...`
- `Construction commande ARC: house_code=..., unit_code=...`
- `Commande construite: X bytes, hex=...`
- `ARC command: house_code=..., unit_code=..., command=..., sequence=X->Y`

#### Réception de Messages
- `Démarrage de la réception des messages RFXCOM`
- `Type de connexion: ...`
- `Paquet reçu: longueur=...`
- `Paquet complet reçu: X bytes, hex=...`
- `Parsing du paquet: ...`
- `Type de paquet: 0xXX`
- `Subtype: 0xXX`
- `ARC paquet: house_code_byte=0xXX, unit_code=..., command=0xXX`
- `AC paquet: device_id=..., command=0xXX`
- `ARC appareil détecté: ...`
- `AC appareil détecté: ...`
- `Paquet non reconnu ou ignoré`

#### Auto-Registry
- `Identifiant unique généré: ...`
- `Appareil déjà connu, ignoré: ...`
- `Appareil ajouté au cache: ...`
- `Auto-registry activé, enregistrement automatique...`
- `Auto-registry désactivé, appareil non enregistré automatiquement`
- `Début auto-enregistrement: ...`
- `Appareils existants: X`
- `Appareil ARC déjà enregistré: ...`
- `Appareil AC déjà enregistré: ...`
- `Configuration auto-enregistrée: ...`
- `Mise à jour des options avec X appareils`
- `Rechargement de l'intégration pour créer la nouvelle entité`

### Switch (`switch.py`)

#### Configuration
- `Configuration de X appareils RFXCOM`
- `Création entité X: ... (protocol=...)`
- `Création de X entités switch RFXCOM`

#### Commandes
- `Turn ON: ... (protocol=..., device_id=..., house_code=..., unit_code=...)`
- `Turn OFF: ... (protocol=..., device_id=..., house_code=..., unit_code=...)`
- `État mis à jour: ON pour ...`
- `État mis à jour: OFF pour ...`

### Services (`services.py`)

#### Appairage
- `Service pair_device appelé: ...`
- `Paramètres: protocol=..., name=..., device_id=..., house_code=..., unit_code=...`
- `Intégrations RFXCOM trouvées: X`
- `Utilisation de l'entrée: ...`
- `Appareils existants: X`
- `Configuration appareil créée: ...`
- `Mise à jour des options avec X appareils`
- `Rechargement de l'intégration pour créer la nouvelle entité`

### Initialisation (`__init__.py`)

#### Setup
- `Configuration de l'intégration RFXCOM au niveau du composant`
- `Services RFXCOM configurés`
- `Configuration de l'entrée RFXCOM: ...`
- `Données de configuration: ...`
- `Options: ...`
- `Initialisation du coordinateur...`
- `Coordinateur initialisé avec succès`
- `Coordinateur enregistré dans hass.data`
- `Configuration des plateformes: ...`
- `Intégration RFXCOM configurée avec succès`

#### Unload
- `Déchargement de l'entrée RFXCOM: ...`
- `Plateformes déchargées: ...`
- `Arrêt du coordinateur...`
- `Coordinateur retiré de hass.data`
- `Dernière entrée, déchargement des services`
- `Autres entrées présentes, services conservés`
- `Intégration RFXCOM déchargée: ...`

## Exemples de Logs

### Connexion USB
```
DEBUG: Configuration connexion USB: port=/dev/ttyUSB0, baudrate=38400
INFO: Connexion RFXCOM USB établie sur /dev/ttyUSB0
DEBUG: Port série configuré: timeout=1s, write_timeout=1s
DEBUG: Auto-registry activé, démarrage de la boucle de réception
INFO: Mode auto-registry activé - Détection automatique des appareils
```

### Envoi de Commande ARC
```
DEBUG: Turn ON: Interrupteur Salon (protocol=ARC, device_id=None, house_code=A, unit_code=1)
DEBUG: Envoi commande: protocole=ARC, device_id=, command=ON, house_code=A, unit_code=1
DEBUG: Port série vérifié: ouvert=True
DEBUG: Construction commande ARC: house_code=A, unit_code=1
DEBUG: ARC command: house_code=A, unit_code=1, command=ON, sequence=0->1
DEBUG: Commande construite: 8 bytes, hex=0710010141010100
DEBUG: Commande envoyée: protocole=ARC, device=A/1, commande=ON, bytes=0710010141010100
DEBUG: État mis à jour: ON pour Interrupteur Salon
```

### Réception et Auto-Registry
```
DEBUG: Paquet reçu: longueur=8
DEBUG: Paquet complet reçu: 8 bytes, hex=0710016241010100
DEBUG: Parsing du paquet: 0710016241010100
DEBUG: Type de paquet: 0x10
DEBUG: Subtype: 0x01
DEBUG: ARC paquet: house_code_byte=0x41, unit_code=1, command=0x01
DEBUG: ARC appareil détecté: {'protocol': 'ARC', 'house_code': 'A', 'unit_code': '1', ...}
DEBUG: Identifiant unique généré: ARC_A_1
DEBUG: Appareil ajouté au cache: ARC_A_1
INFO: Nouvel appareil détecté: ARC - A_1
DEBUG: Auto-registry activé, enregistrement automatique...
DEBUG: Début auto-enregistrement: ARC_A_1
DEBUG: Appareils existants: 0
DEBUG: Configuration auto-enregistrée: {'name': 'RFXCOM ARC A_1', ...}
DEBUG: Mise à jour des options avec 1 appareils
INFO: Appareil auto-enregistré: RFXCOM ARC A_1
DEBUG: Rechargement de l'intégration pour créer la nouvelle entité
```

## Dépannage avec les Logs

### Problème de Connexion
Cherchez :
- `Configuration connexion USB: ...` ou `Configuration connexion réseau: ...`
- `Connexion RFXCOM USB établie` ou `Connexion RFXCOM réseau établie`
- Erreurs de connexion

### Problème d'Envoi de Commande
Cherchez :
- `Envoi commande: ...`
- `Commande construite: ...`
- `Commande envoyée: ...`
- Erreurs d'envoi

### Problème d'Auto-Registry
Cherchez :
- `Démarrage de la réception des messages RFXCOM`
- `Paquet reçu: ...`
- `Appareil détecté: ...`
- `Auto-enregistrement: ...`

### Problème de Parsing
Cherchez :
- `Parsing du paquet: ...`
- `Type de paquet: ...`
- `Paquet non reconnu ou ignoré`
- `Longueur invalide, ignoré: ...`


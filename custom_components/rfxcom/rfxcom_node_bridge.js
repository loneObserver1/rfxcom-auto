#!/usr/bin/env node
/**
 * Bridge Node.js pour RFXCOM
 * Écoute les commandes via stdin et envoie les réponses via stdout
 * Format JSON pour la communication avec Python
 * 
 * Usage:
 *   echo '{"action":"send","protocol":"AC","device_id":"02382C82","unit_code":2,"command":"on"}' | node rfxcom_node_bridge.js
 */

const rfxcom = require('rfxcom');
const readline = require('readline');

// Interface pour lire stdin ligne par ligne
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Trouver le port USB automatiquement
function findUSBPort() {
    const fs = require('fs');
    const os = require('os');
    const platform = os.platform();
    
    if (platform === 'darwin') {
        try {
            const devDir = '/dev';
            const files = fs.readdirSync(devDir);
            const usbPorts = files.filter(f => 
                f.startsWith('cu.usbserial-') || 
                f.startsWith('cu.usbmodem')
            );
            
            if (usbPorts.length > 0) {
                const cuPort = usbPorts.find(p => p.startsWith('cu.'));
                if (cuPort) {
                    return `/dev/${cuPort}`;
                }
                return `/dev/${usbPorts[0]}`;
            }
        } catch (err) {}
        return '/dev/cu.usbserial-A11DA9X2';
    } else if (platform === 'linux') {
        try {
            const devDir = '/dev';
            const files = fs.readdirSync(devDir);
            const usbPorts = files.filter(f => f.startsWith('ttyUSB') || f.startsWith('ttyACM'));
            if (usbPorts.length > 0) {
                return `/dev/${usbPorts[0]}`;
            }
        } catch (err) {}
        return '/dev/ttyUSB0';
    } else {
        return 'COM3';
    }
}

let rfxtrx = null;
let lighting1 = null;
let lighting2 = null;
let lighting3 = null;
let lighting4 = null;
let lighting5 = null;
let lighting6 = null;
let isReady = false;
let port = null;

// Mapping des protocoles vers les types Lighting
const PROTOCOL_TO_LIGHTING = {
    // Lighting1
    'X10': { type: 1, subtype: rfxcom.lighting1.X10 },
    'ARC': { type: 1, subtype: rfxcom.lighting1.ARC },
    'ABICOD': { type: 1, subtype: rfxcom.lighting1.ABICOD },
    'WAVEMAN': { type: 1, subtype: rfxcom.lighting1.WAVEMAN },
    'EMW100': { type: 1, subtype: rfxcom.lighting1.EMW100 },
    'IMPULS': { type: 1, subtype: rfxcom.lighting1.IMPULS },
    'RISINGSUN': { type: 1, subtype: rfxcom.lighting1.RISINGSUN },
    'PHILIPS': { type: 1, subtype: rfxcom.lighting1.PHILIPS },
    'ENERGENIE': { type: 1, subtype: rfxcom.lighting1.ENERGENIE },
    'ENERGENIE_5': { type: 1, subtype: rfxcom.lighting1.ENERGENIE_5 },
    'COCOSTICK': { type: 1, subtype: rfxcom.lighting1.COCOSTICK },
    // Lighting2
    'AC': { type: 2, subtype: rfxcom.lighting2.AC },
    'HOMEEASY_EU': { type: 2, subtype: rfxcom.lighting2.HOMEEASY_EU },
    'ANSLUT': { type: 2, subtype: rfxcom.lighting2.ANSLUT },
    'KAMBROOK': { type: 2, subtype: rfxcom.lighting2.KAMBROOK },
    // Lighting3
    'IKEA_KOPPLA': { type: 3, subtype: null },
    // Lighting4
    'PT2262': { type: 4, subtype: null },
    // Lighting5
    'LIGHTWAVERF': { type: 5, subtype: rfxcom.lighting5.LIGHTWAVERF },
    'EMW100_GDO': { type: 5, subtype: rfxcom.lighting5.EMW100_GDO },
    'BBSB': { type: 5, subtype: rfxcom.lighting5.BBSB },
    'RSL': { type: 5, subtype: rfxcom.lighting5.RSL },
    'LIVOLO': { type: 5, subtype: rfxcom.lighting5.LIVOLO },
    'TRC02': { type: 5, subtype: rfxcom.lighting5.TRC02 },
    'AOKE': { type: 5, subtype: rfxcom.lighting5.AOKE },
    'RGB_TRC02': { type: 5, subtype: rfxcom.lighting5.RGB_TRC02 },
    // Lighting6
    'BLYSS': { type: 6, subtype: null },
};

// Fonction pour initialiser la connexion RFXCOM
function initRFXCOM(customPort) {
    return new Promise((resolve, reject) => {
        port = customPort || findUSBPort();
        
        rfxtrx = new rfxcom.RfxCom(port, {
            debug: false,
        });
        
        rfxtrx.on('connectfailed', () => {
            reject(new Error(`Échec de connexion au RFXCOM sur ${port}`));
        });
        
        rfxtrx.on('disconnect', () => {
            isReady = false;
        });
        
        rfxtrx.on('error', (err) => {
            console.error(JSON.stringify({error: err.message}));
        });
        
        rfxtrx.on('ready', () => {
            isReady = true;
            // Initialiser tous les handlers Lighting
            lighting1 = new rfxcom.Lighting1(rfxtrx, rfxcom.lighting1.ARC);
            lighting2 = new rfxcom.Lighting2(rfxtrx, rfxcom.lighting2.AC);
            lighting3 = new rfxcom.Lighting3(rfxtrx, rfxcom.lighting3.IKEA_KOPPLA);
            lighting4 = new rfxcom.Lighting4(rfxtrx, rfxcom.lighting4.PT2262);
            lighting5 = new rfxcom.Lighting5(rfxtrx, rfxcom.lighting5.LIGHTWAVERF);
            lighting6 = new rfxcom.Lighting6(rfxtrx, rfxcom.lighting6.BLYSS);
            resolve();
        });
        
        rfxtrx.initialise(() => {});
        
        // Timeout de 10 secondes
        setTimeout(() => {
            if (!isReady) {
                reject(new Error('Timeout lors de l\'initialisation'));
            }
        }, 10000);
    });
}

// Fonction pour envoyer une commande
function sendCommand(protocol, deviceId, houseCode, unitCode, command) {
    return new Promise((resolve, reject) => {
        if (!isReady) {
            reject(new Error('RFXCOM non prêt'));
            return;
        }
        
        const protocolInfo = PROTOCOL_TO_LIGHTING[protocol];
        if (!protocolInfo) {
            reject(new Error(`Protocole non supporté: ${protocol}`));
            return;
        }
        
        const callback = (err) => {
            if (err) {
                reject(err);
            } else {
                resolve();
            }
        };
        
        const lightingType = protocolInfo.type;
        
        // Lighting1: utilise houseCode + unitCode (ex: "A1")
        if (lightingType === 1) {
            if (!lighting1) {
                reject(new Error('Lighting1 non initialisé'));
                return;
            }
            if (!houseCode) {
                reject(new Error('house_code requis pour Lighting1'));
                return;
            }
            // Créer un handler spécifique pour ce protocole
            const handler = new rfxcom.Lighting1(rfxtrx, protocolInfo.subtype);
            const deviceIdFormatted = `${houseCode}${unitCode}`;
            if (command === 'on') {
                handler.switchOn(deviceIdFormatted, callback);
            } else if (command === 'off') {
                handler.switchOff(deviceIdFormatted, callback);
            } else {
                reject(new Error(`Commande inconnue: ${command}`));
            }
        }
        // Lighting2: utilise deviceId + unitCode (ex: "0x02382C82/1")
        else if (lightingType === 2) {
            if (!lighting2) {
                reject(new Error('Lighting2 non initialisé'));
                return;
            }
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting2'));
                return;
            }
            // Créer un handler spécifique pour ce protocole
            const handler = new rfxcom.Lighting2(rfxtrx, protocolInfo.subtype);
            const deviceIdFormatted = `0x${deviceId.toUpperCase()}/${unitCode}`;
            if (command === 'on') {
                handler.switchOn(deviceIdFormatted, callback);
            } else if (command === 'off') {
                handler.switchOff(deviceIdFormatted, callback);
            } else {
                reject(new Error(`Commande inconnue: ${command}`));
            }
        }
        // Lighting3: utilise deviceId + unitCode
        else if (lightingType === 3) {
            if (!lighting3) {
                reject(new Error('Lighting3 non initialisé'));
                return;
            }
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting3'));
                return;
            }
            const handler = new rfxcom.Lighting3(rfxtrx, rfxcom.lighting3.IKEA_KOPPLA);
            const deviceIdFormatted = `0x${deviceId.toUpperCase()}/${unitCode}`;
            if (command === 'on') {
                handler.switchOn(deviceIdFormatted, callback);
            } else if (command === 'off') {
                handler.switchOff(deviceIdFormatted, callback);
            } else {
                reject(new Error(`Commande inconnue: ${command}`));
            }
        }
        // Lighting4: utilise deviceId (3 bytes)
        else if (lightingType === 4) {
            if (!lighting4) {
                reject(new Error('Lighting4 non initialisé'));
                return;
            }
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting4'));
                return;
            }
            const handler = new rfxcom.Lighting4(rfxtrx, rfxcom.lighting4.PT2262);
            const deviceIdFormatted = `0x${deviceId.toUpperCase()}`;
            if (command === 'on') {
                handler.switchOn(deviceIdFormatted, callback);
            } else if (command === 'off') {
                handler.switchOff(deviceIdFormatted, callback);
            } else {
                reject(new Error(`Commande inconnue: ${command}`));
            }
        }
        // Lighting5: utilise deviceId + unitCode
        else if (lightingType === 5) {
            if (!lighting5) {
                reject(new Error('Lighting5 non initialisé'));
                return;
            }
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting5'));
                return;
            }
            const handler = new rfxcom.Lighting5(rfxtrx, protocolInfo.subtype);
            const deviceIdFormatted = `0x${deviceId.toUpperCase()}/${unitCode}`;
            if (command === 'on') {
                handler.switchOn(deviceIdFormatted, callback);
            } else if (command === 'off') {
                handler.switchOff(deviceIdFormatted, callback);
            } else {
                reject(new Error(`Commande inconnue: ${command}`));
            }
        }
        // Lighting6: utilise deviceId
        else if (lightingType === 6) {
            if (!lighting6) {
                reject(new Error('Lighting6 non initialisé'));
                return;
            }
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting6'));
                return;
            }
            const handler = new rfxcom.Lighting6(rfxtrx, rfxcom.lighting6.BLYSS);
            const deviceIdFormatted = `0x${deviceId.toUpperCase()}`;
            if (command === 'on') {
                handler.switchOn(deviceIdFormatted, callback);
            } else if (command === 'off') {
                handler.switchOff(deviceIdFormatted, callback);
            } else {
                reject(new Error(`Commande inconnue: ${command}`));
            }
        }
        else {
            reject(new Error(`Type de protocole non supporté: ${lightingType}`));
        }
    });
}

// Fonction pour appairer (envoi rapide)
function pairDevice(protocol, deviceId, houseCode, unitCode) {
    return new Promise((resolve, reject) => {
        if (!isReady) {
            reject(new Error('RFXCOM non prêt'));
            return;
        }
        
        const protocolInfo = PROTOCOL_TO_LIGHTING[protocol];
        if (!protocolInfo) {
            reject(new Error(`Protocole non supporté: ${protocol}`));
            return;
        }
        
        const lightingType = protocolInfo.type;
        let handler;
        let deviceIdFormatted;
        
        // Créer le handler approprié
        if (lightingType === 1) {
            if (!houseCode) {
                reject(new Error('house_code requis pour Lighting1'));
                return;
            }
            handler = new rfxcom.Lighting1(rfxtrx, protocolInfo.subtype);
            deviceIdFormatted = `${houseCode}${unitCode}`;
        } else if (lightingType === 2) {
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting2'));
                return;
            }
            handler = new rfxcom.Lighting2(rfxtrx, protocolInfo.subtype);
            deviceIdFormatted = `0x${deviceId.toUpperCase()}/${unitCode}`;
        } else if (lightingType === 3) {
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting3'));
                return;
            }
            handler = new rfxcom.Lighting3(rfxtrx, rfxcom.lighting3.IKEA_KOPPLA);
            deviceIdFormatted = `0x${deviceId.toUpperCase()}/${unitCode}`;
        } else if (lightingType === 4) {
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting4'));
                return;
            }
            handler = new rfxcom.Lighting4(rfxtrx, rfxcom.lighting4.PT2262);
            deviceIdFormatted = `0x${deviceId.toUpperCase()}`;
        } else if (lightingType === 5) {
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting5'));
                return;
            }
            handler = new rfxcom.Lighting5(rfxtrx, protocolInfo.subtype);
            deviceIdFormatted = `0x${deviceId.toUpperCase()}/${unitCode}`;
        } else if (lightingType === 6) {
            if (!deviceId) {
                reject(new Error('device_id requis pour Lighting6'));
                return;
            }
            handler = new rfxcom.Lighting6(rfxtrx, rfxcom.lighting6.BLYSS);
            deviceIdFormatted = `0x${deviceId.toUpperCase()}`;
        } else {
            reject(new Error(`Type de protocole non supporté: ${lightingType}`));
            return;
        }
        
        const startTime = Date.now();
        let sentCount = 0;
        let errorCount = 0;
        let pendingCount = 0;
        
        const sendPairCommand = () => {
            pendingCount++;
            handler.switchOn(deviceIdFormatted, (err) => {
                pendingCount--;
                if (err) {
                    errorCount++;
                } else {
                    sentCount++;
                }
            });
        };
        
        const interval = setInterval(() => {
            const elapsed = (Date.now() - startTime) / 1000;
            
            if (elapsed >= 3.5) {
                clearInterval(interval);
                
                const waitForPending = setInterval(() => {
                    if (pendingCount === 0) {
                        clearInterval(waitForPending);
                        if (errorCount > sentCount / 2) {
                            reject(new Error(`${errorCount} erreurs sur ${sentCount} envois`));
                        } else {
                            resolve({sent: sentCount, errors: errorCount});
                        }
                    }
                }, 50);
            } else {
                sendPairCommand();
            }
        }, 15);
    });
}

// Traiter les commandes reçues via stdin
rl.on('line', async (line) => {
    try {
        const command = JSON.parse(line);
        
        if (command.action === 'init') {
            // Initialiser la connexion
            try {
                await initRFXCOM(command.port);
                console.log(JSON.stringify({status: 'ready', port: port}));
            } catch (err) {
                console.log(JSON.stringify({status: 'error', error: err.message}));
            }
        } else if (command.action === 'send') {
            // Envoyer une commande
            try {
                await sendCommand(
                    command.protocol,
                    command.device_id || '',
                    command.house_code || '',
                    command.unit_code || 1,
                    command.command
                );
                console.log(JSON.stringify({status: 'success'}));
            } catch (err) {
                console.log(JSON.stringify({status: 'error', error: err.message}));
            }
        } else if (command.action === 'pair') {
            // Appairer
            try {
                const result = await pairDevice(
                    command.protocol,
                    command.device_id || '',
                    command.house_code || '',
                    command.unit_code || 1
                );
                console.log(JSON.stringify({status: 'success', result: result}));
            } catch (err) {
                console.log(JSON.stringify({status: 'error', error: err.message}));
            }
        } else if (command.action === 'close') {
            // Fermer la connexion
            if (rfxtrx) {
                rfxtrx.close();
            }
            console.log(JSON.stringify({status: 'closed'}));
            process.exit(0);
        } else {
            console.log(JSON.stringify({status: 'error', error: 'Action inconnue'}));
        }
    } catch (err) {
        console.log(JSON.stringify({status: 'error', error: err.message}));
    }
});

// Gestion de la fermeture
process.on('SIGINT', () => {
    if (rfxtrx) {
        rfxtrx.close();
    }
    process.exit(0);
});

process.on('unhandledRejection', (err) => {
    console.log(JSON.stringify({status: 'error', error: err.message}));
});


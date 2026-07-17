const STORAGE_KEYS = {
    ttsEngine: 'maia_tts_engine',
    ttsVoice: 'maia_tts_voice',
    ttsSpeed: 'maia_tts_speed',
    ttsVolume: 'maia_tts_volume',
    ttsAutoRead: 'maia_tts_auto_read',
    hermesProfile: 'maia_hermes_profile'
};

/**
 * Charge les réglages depuis le LocalStorage
 * @returns {Object} Les réglages sauvegardés
 */
function loadFromLocalStorage() {
    const settings = {};
    for (const key in STORAGE_KEYS) {
        const value = localStorage.getItem(STORAGE_KEYS[key]);
        if (value !== null) {
            if (key === 'ttsSpeed' || key === 'ttsVolume') {
                settings[key] = parseFloat(value);
            } else if (key === 'ttsAutoRead') {
                settings[key] = value === 'true';
            } else {
                settings[key] = value;
            }
        }
    }
    return settings;
}

/**
 * Remplit les éléments Select avec les données du backend
 * @param {Object} data - Le JSON reçu de /settings/data
 */
function populateSelects(data) {
    // Remplir les moteurs TTS
    const engineSelect = document.getElementById('tts-engine');
    if (engineSelect && data.engines) {
        engineSelect.innerHTML = ''; // Clear "Chargement..."
        data.engines.forEach(engine => {
            const option = document.createElement('option');
            option.value = engine.id;
            option.textContent = engine.name;
            engineSelect.appendChild(option);
        });
    }

    // Remplir les voix TTS
    const voiceSelect = document.getElementById('tts-voice');
    if (voiceSelect && data.voices) {
        voiceSelect.innerHTML = ''; // Clear "Chargement..."
        data.voices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            voiceSelect.appendChild(option);
        });
    }

    // Remplir les profils Hermès
    const profileSelect = document.getElementById('hermes-profile');
    if (profileSelect && data.profiles) {
        profileSelect.innerHTML = ''; // Clear "Chargement..."
        data.profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.id;
            option.textContent = profile.name;
            profileSelect.appendChild(option);
        });
    }
}

/**
 * Applique les réglages sauvegardés sur les éléments du DOM
 * @param {Object} settings 
 */
function applySettings(settings) {
    // TTS Engine
    const engineSelect = document.getElementById('tts-engine');
    if (engineSelect && settings.ttsEngine) {
        engineSelect.value = settings.ttsEngine;
    }

    // TTS Voice
    const voiceSelect = document.getElementById('tts-voice');
    if (voiceSelect && settings.ttsVoice) {
        voiceSelect.value = settings.ttsVoice;
    }

    // TTS Speed
    const speedInput = document.getElementById('tts-speed');
    if (speedInput && settings.ttsSpeed !== undefined) {
        speedInput.value = settings.ttsSpeed;
        document.getElementById('speed-value').innerText = settings.ttsSpeed + 'x';
    }

    // TTS Volume
    const volumeInput = document.getElementById('tts-volume');
    if (volumeInput && settings.ttsVolume !== undefined) {
        volumeInput.value = settings.ttsVolume;
        document.getElementById('volume-value').innerText = settings.ttsVolume + '%';
    }

    // TTS Auto Read
    const autoReadCheck = document.getElementById('tts-auto-read');
    if (autoReadCheck && settings.ttsAutoRead !== undefined) {
        autoReadCheck.checked = settings.ttsAutoRead;
    }

    // Hermes Profile
    const profileSelect = document.getElementById('hermes-profile');
    if (profileSelect && settings.hermesProfile) {
        profileSelect.value = settings.hermesProfile;
    }
}

/**
 * Sauvegarde les réglages actuels dans le LocalStorage
 */
function saveSettings() {
    const settings = {
        ttsEngine: document.getElementById('tts-engine').value,
        ttsVoice: document.getElementById('tts-voice').value,
        ttsSpeed: document.getElementById('tts-speed').value,
        ttsVolume: document.getElementById('tts-volume').value,
        ttsAutoRead: document.getElementById('tts-auto-read').checked,
        hermesProfile: document.getElementById('hermes-profile').value
    };

    for (const key in STORAGE_KEYS) {
        localStorage.setItem(STORAGE_KEYS[key], String(settings[key]));
    }

    alert('Réglages sauvegardés !');
}

// Initialisation
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 1. Récupérer les données du backend
        const response = await fetch('/settings/data');
        if (!response.ok) throw new Error('Erreur lors de la récupération des données');
        const data = await response.json();

        // 2. Remplir les listes déroulantes
        populateSelects(data);

        // 3. Charger les préférences du LocalStorage
        const savedSettings = loadFromLocalStorage();

        // 4. Appliquer les préférences sur les listes maintenant peuplées
        applySettings(savedSettings);

    } catch (error) {
        console.error('Erreur d\'initialisation des paramètres:', error);
        // Optionnel: afficher une erreur à l'utilisateur
    }

    const saveBtn = document.getElementById('save-settings');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveSettings);
    }
});

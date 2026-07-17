const STORAGE_KEYS = {
    ttsEngine: 'maia_tts_engine',
    ttsVoice: 'maia_tts_voice',
    ttsSpeed: 'maia_tts_speed',
    ttsVolume: 'maia_tts_volume',
    ttsAutoRead: 'maia_tts_auto_read',
    hermesProfile: 'maia_hermes_profile'
};

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

function populateSelects(data) {
    fillSelect(document.getElementById('tts-engine'), data.engines);
    fillSelect(document.getElementById('tts-voice'), data.voices);
    fillSelect(document.getElementById('hermes-profile'), data.profiles);
}

function fillSelect(select, dataMap) {
    if (select && dataMap) {
        select.innerHTML = '';
        dataMap.forEach(data => {
            const option = document.createElement('option');
            option.value = data.id;
            option.textContent = data.name;
            select.appendChild(option);
        });
    }
}

function applySettings(settings) {

    for (const key in STORAGE_KEYS) {
        if (settings[key] === undefined)
            continue;
        const elemId = camelToKebab(key);
        const elem = document.getElementById(elemId);

        if (elem.tagName === 'INPUT' && elem.type === 'checkbox')
            elem.checked = settings[key];
        else
            elem.value = settings[key];

        //Update range span
        if (key === 'ttsSpeed')
            document.getElementById(elemId + '-value').innerText = elem.value + 'x';
        else if (key === 'ttsVolume')
            document.getElementById(elemId + '-value').innerText = elem.value + '%';
    }
}

function saveSettings() {

    for (const key in STORAGE_KEYS) {
        const elemId = camelToKebab(key);
        const elem = document.getElementById(elemId);
        const value = elem.tagName === 'INPUT' && elem.type === 'checkbox' ? elem.checked : elem.value;
        localStorage.setItem(STORAGE_KEYS[key], String(value));
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 1. Get data from backend
        const response = await fetch('/settings');
        if (!response.ok) throw new Error('Error getting settings data');
        const data = await response.json();

        // 2. Fill selects
        populateSelects(data);

        // 3. Load saved settings
        const savedSettings = loadFromLocalStorage();

        // 4. Apply them
        applySettings(savedSettings);

    } catch (error) {
        console.error('Erreur d\'initialisation des paramètres:', error);
    }
});

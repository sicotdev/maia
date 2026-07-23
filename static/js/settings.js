const STORAGE_KEYS = {
    ttsEngine: 'maia_tts_engine',
    ttsVoice: 'maia_tts_voice',
    ttsSpeed: 'maia_tts_speed',
    ttsVolume: 'maia_tts_volume',
    ttsAutoRead: 'maia_tts_auto_read',
    llmEndpoint: 'maia_llm_endpoint',
    hermesProfile: 'maia_hermes_profile'
};
const DEFAULT_VALUES = {
    ttsEngine: 0,
    ttsVoice: 0,
    ttsSpeed: 1.0,
    ttsVolume: 100,
    ttsAutoRead: false,
    llmEndpoint: 0,
    hermesProfile: 0
};
const settings = {};

let settings_config = {};

function get_setting(key) {
    return settings[key];
}

function set_settings_cookie() {
    document.cookie = `llmEndpoint=${get_setting('llmEndpoint')};hermesProfile=${get_setting('hermesProfile')}; path=/; SameSite=Lax;`;
}

function loadFromLocalStorage() {
    
    for (const key in STORAGE_KEYS) {
        let value = localStorage.getItem(STORAGE_KEYS[key]);
        if (value !== null) {

            if (key === 'ttsSpeed' || key === 'ttsVolume') {
                settings[key] = parseFloat(value);
            } else if (key === 'ttsAutoRead') {
                settings[key] = value === 'true';
            } else {
                settings[key] = value;
            }

            console.log(key + "=" + settings[key]);
        }
        else
            settings[key] = DEFAULT_VALUES[key];
    }

    //Set cookie
    set_settings_cookie();
}

function populateSelects() {
    fillSelect(document.getElementById('tts-engine'), settings_config.engines);
    fillSelect(document.getElementById('tts-voice'), settings_config.voices);
    fillSelect(document.getElementById('llm-endpoint'), settings_config.llmEndpoints);
    fillSelect(document.getElementById('hermes-profile'), settings_config.profiles);
}

function fillSelect(select, dataMap) {
    if (select && dataMap) {
        select.innerHTML = '';
        dataMap.forEach((data, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = data.name;
            select.appendChild(option);
        });
    }
}

function applySettings() {

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
            elem.nextElementSibling.textContent = elem.value + 'x';
        else if (key === 'ttsVolume')
            elem.nextElementSibling.textContent = elem.value + '%';
    }
}

function saveSettings() {

    const oldProfile = get_setting('hermesProfile');
    const oldEndPoint = get_setting('llmEndpoint');

    for (const key in STORAGE_KEYS) {
        const elemId = camelToKebab(key);
        const elem = document.getElementById(elemId);
        const value = elem.tagName === 'INPUT' && elem.type === 'checkbox' ? elem.checked : elem.value;
        localStorage.setItem(STORAGE_KEYS[key], String(value));
        settings[key] = value;
    }

    //Apply llm/profile change
    const newProfile = get_setting('hermesProfile');
    const newEndPoint = get_setting('llmEndpoint');
    if (oldProfile != newProfile || oldEndPoint != newEndPoint) {

        //Save new cookie
        set_settings_cookie();

        //Clear sessions immediatly
        document.getElementById('conversation-list').innerHTML = '<span class="spinner"></span>';

        //Clic new session to clear chat (call showPanel('chat') internally)
        sessionNewBtnClick();

        //Load sessions from the new profile
        htmx.trigger('#conversation-list', 'profileChange');
        return;
    }

    //Apply audio settings to existing audios
    document.querySelectorAll('audio').forEach((audio) => {
        audio.volume = get_setting('ttsVolume') / 100;
        audio.playbackRate = get_setting('ttsSpeed');
    });

    //Show chat panel to close parameters
    showPanel('chat');
}

document.addEventListener('DOMContentLoaded', async () => {
    
    try {
        // 1. Get data from backend
        const response = await fetch('/settings');
        if (!response.ok) throw new Error('Error getting settings data');
        settings_config = await response.json();

        // 2. Fill selects
        populateSelects();

        // 3. Load saved settings
        loadFromLocalStorage();

        // 4. Apply them
        applySettings();

        //Bind events
        document.getElementById('tts-speed').addEventListener("input", () => {event.target.nextElementSibling.textContent = event.target.value + 'x'})
        document.getElementById('tts-volume').addEventListener("input", () => {event.target.nextElementSibling.textContent = event.target.value + '%'})
    } catch (error) {
        console.error('Erreur d\'initialisation des paramètres:', error);
    }

    const selectLLM = document.getElementById('llm-endpoint');
    selectLLM.addEventListener('change', () => onLLMSelectChange(selectLLM));
    onLLMSelectChange(selectLLM);
});

function onLLMSelectChange(selectLLM) {
    const selectProfile = document.getElementById('hermes-profile-container');
    console.log('change');
    if (selectLLM.value != 0)
        selectProfile.style.visibility = 'hidden';
    else
        selectProfile.style.visibility = 'visible';
}
const SILENCE_THRESHOLD = 15;
const MAX_SILENCE_MS = 1000;

let voiceCallActive = false;
let isRecording = false;

//Voice call button
function initVoiceCallButton() {
    const voiceButtons = document.querySelectorAll('.voice-call-btn');
    voiceButtons.forEach((elem) => {
        elem.addEventListener('click', async () => {
            if (voiceCallActive) {
                voiceCallActive = false;
                return;
            }
            voiceCallActive = true;
            startVoiceCall();
        }); 
    });
}


async function startVoiceCall() {
    const voiceButtons = document.querySelectorAll('.voice-call-btn');
    voiceButtons.forEach((elem) => {elem.classList.add('active');} );

    const chatForm = document.getElementById('chat-form');
    chatForm.classList.add('hidden');
    chatForm.querySelector('#is_voicecall').value = "true";

    document.getElementById('user-input').value = '';

    const voiceCallContainer = document.getElementById('voice-call-active');
    voiceCallContainer.classList.add('visible');

    const startVoiceCallBtn = document.getElementById('start-voice-btn');
    const voiceCallMessage = document.getElementById('voice-call-message');

    startVoiceCallBtn.innerHTML = "Parlez pour commencer";
    voiceCallMessage.innerHTML = "Appuyez sur le bouton pour arrêter l'appel.";

    const inputField = document.getElementById('user-input');
    while (voiceCallActive) {
        
        try {
            //User talk
            console.log('start talking');
            await waitUserMessage();

            showPanel('chat');

            //No input detected
            if (inputField.value == '')
                continue;

            //Shortcut if user cancel the call
            if (!voiceCallActive) break;
            
            //Auto send form
            chatForm.requestSubmit();

            //Ai message
            await waitAIMessage();

            console.log('AI start talking');

            //Ai audio talk
            await waitAITalking();

            console.log('AI end talking');
        }
        catch(e) {
            voiceCallActive = false;
        }
    }

    // prevent sendingToWhisper
    isRecording = false;

    voiceCallContainer.classList.remove('visible');
    chatForm.classList.remove('hidden');
    chatForm.querySelector('#is_voicecall').value = "false";
    voiceButtons.forEach((elem) => {elem.classList.remove('active');} );

    startVoiceCallBtn.innerHTML = "Démarrer l'appel";
    voiceCallMessage.innerHTML = "Appuyez sur le bouton pour commencer l'appel.";
}

async function waitUserMessage() {
    return new Promise(async (resolve, reject) => {
        let stopped = false;

        try {
            const mediaRecorder = await startRecording(() => {
                resolve();
                stopped = true;
            })

            while (voiceCallActive && !stopped)
                await sleep(100);
            
            if (!stopped) {
                isRecording = false;
                mediaRecorder.stop();
                resolve();
            }
        }
        catch (e) {
            reject(e);
        }
    });
}

async function waitAIMessage() {
    return new Promise(async (resolve) => {
        
        //User input become active when AI message is done
        const userInput = document.getElementById('user-input')
        while (userInput.disabled)
            await sleep(100);
        resolve();
    })
}

async function waitAITalking() {
    return new Promise(async (resolve) => {
        while (isTTSPlaying())
            await sleep(100);
        resolve();
    })
}


async function startRecording(endCallBack) {
    
    isRecording = true;
    const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false
        }
    });
    console.log('start recording')
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
        //Avoid recording while playing AI voice
        if (!isTTSPlaying())
            audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        console.log('stoppped recording')
        if (isRecording) {
            if (audioChunks.length > 0) {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                sendAudioToWhisper(audioBlob, endCallBack);
            }
            else
                endCallBack();
        }
        // Stop all tracks to release the microphone
        stream.getTracks().forEach(track => track.stop());
        isRecording = false;
    };

    mediaRecorder.start();
    
    // Init AudioContext for silence detection
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    const microphone = audioContext.createMediaStreamSource(stream);
    microphone.connect(analyser);
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    let silenceStart = 0;
    let recordStarted = false;
    let silenceStarted = false;

    function checkSilence() {
        if (!isRecording) return;

        if (!isTTSPlaying()) {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
            }
            let average = sum / dataArray.length;

            if (average > SILENCE_THRESHOLD) {
                recordStarted = true;
                silenceStarted = false;
            }
            else {
                if (recordStarted && !silenceStarted) {
                    silenceStarted = true;
                    silenceStart = new Date().getTime();
                }
            }

            //console.log(average, silenceStarted);
            //if (silenceStarted)
            //    console.log(new Date().getTime() - silenceStart)

            if (silenceStarted && new Date().getTime() - silenceStart > MAX_SILENCE_MS) {
                mediaRecorder.stop();
            }
        }

        requestAnimationFrame(checkSilence);
    }
    requestAnimationFrame(checkSilence);

    return mediaRecorder;
}

async function sendAudioToWhisper(blob, endCallBack) {
    const formData = new FormData();
    formData.append('file', blob, 'audio.wav');

    try {
        const response = await fetch('/v1/voice/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Erreur lors de la transcription');

        const data = await response.json();
        const inputField = document.getElementById('user-input');
        if (inputField) {
            inputField.value += data.text;
            // Trigger any input events if necessary
            inputField.dispatchEvent(new Event('input'));
            endCallBack();
        }
    } catch (err) {
        console.error('Transcription error:', err);
        endCallBack();
    }
}

// Speech-to-text button
function initSTTButton() {
    const sttBtn = document.getElementById('stt-btn');
    const startVoiceCallBtn = document.getElementById('start-voice-btn');

    let mediaRecorder;

    // Handle the button click
    sttBtn.addEventListener('click', async () => {

        console.log('click');

        if (sttBtn.disabled) return;
        sttBtn.disabled = true;

        if (!isRecording) {
            sttBtn.classList.add('active');
            startVoiceCallBtn.disabled = true;
            isRecording = true;
            try {
                mediaRecorder = await startRecording(() => {
                    sttBtn.classList.remove('active');
                    isRecording = false;
                    sttBtn.disabled = false;
                    startVoiceCallBtn.disabled = false;
                });
            }
            catch (e) {
                sttBtn.classList.remove('active');
                isRecording = false;
                sttBtn.disabled = false;
                startVoiceCallBtn.disabled = false;
            }
                
        } else if (mediaRecorder){
            mediaRecorder.stop();
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    
    initSTTButton();
    initVoiceCallButton();
});

// Speech-to-text functionality using Whisper via backend
function initSTT() {
    const sttBtn = document.getElementById('stt-btn');
    if (!sttBtn) return;

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let silenceTimer = null;
    let audioContext;
    let analyser;
    let microphone;
    let dataArray;
    let framesOfSilence = 0;
    const SILENCE_THRESHOLD = 30;
    const MAX_SILENCE_FRAMES = 240;
    let stream;

    // Handle the button click
    sttBtn.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    sendAudioToWhisper(audioBlob);
                    
                    // Stop all tracks to release the microphone
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                sttBtn.classList.add('active');
                isRecording = true;

                // Init AudioContext for silence detection
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioContext.createAnalyser();
                analyser.fftSize = 256;
                microphone = audioContext.createMediaStreamSource(stream);
                microphone.connect(analyser);
                dataArray = new Uint8Array(analyser.frequencyBinCount);

                framesOfSilence = 0;
                recordStarted = false;

                function checkSilence() {
                    if (!isRecording) return;
                    analyser.getByteFrequencyData(dataArray);
                    let sum = 0;
                    for (let i = 0; i < dataArray.length; i++) {
                        sum += dataArray[i];
                    }
                    let average = sum / dataArray.length;

                    if (average < SILENCE_THRESHOLD) {
                        if (recordStarted)
                            framesOfSilence++;
                    } else {
                        framesOfSilence = 0;
                        recordStarted = true;
                    }

                    if (framesOfSilence > MAX_SILENCE_FRAMES) {
                        mediaRecorder.stop();
                        sttBtn.classList.remove('active');
                        isRecording = false;
                        // Stop tracks to release mic
                        stream.getTracks().forEach(track => track.stop());
                    }

                    requestAnimationFrame(checkSilence);
                }
                requestAnimationFrame(checkSilence);
            } catch (err) {
                console.error('Error accessing microphone:', err);
                alert('Erreur d\'accès au microphone.');
            }
        } else {
            mediaRecorder.stop();
            sttBtn.classList.remove('active');
            isRecording = false;
        }
    });

    async function sendAudioToWhisper(blob) {
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
            }
        } catch (err) {
            console.error('Transcription error:', err);
            alert('Erreur de transcription.');
        }
    }
}


//TTS streamed from backend
const queue = [];
let playing = false;

function enqueueAudio(url) {
    queue.push(url);
    if (!playing) playNext();
}

function playNext() {
    if (queue.length === 0) { playing = false; return; }
    playing = true;
    const url = queue.shift();
    const audio = new Audio(url);
    audio.play();
    audio.onended = playNext;
}

function startAudioGeneration(button, messageId) {
    if (playing) return;

    button.disabled = true;
    button.innerHTML = "<span class='spinner'></span>";

    const text = document.getElementById(`message-text-${messageId}`).innerText;

    const url = `/v1/voice/generate?message_id=${messageId}&text=${encodeURIComponent(text)}`;
    const evtSource = new EventSource(url);

    let chunkReceived = false;
    evtSource.addEventListener('chunk', (event) => {
        chunkReceived = true;
        enqueueAudio(event.data);
    });

    evtSource.addEventListener('done', () => {
        const finalAudioUrl = event.data;
        const autoplay = !chunkReceived; // meaning we already have the final wav
        button.remove();
        showFinalAudioPlayer(messageId, finalAudioUrl, autoplay);
        evtSource.close();
    });

    evtSource.onerror = (err) => {
        console.error('SSE error:', err);
        evtSource.close();
    };

    return evtSource;
}

function showFinalAudioPlayer(messageId, url, autoplay = false) {
    const audio = document.getElementById(`audio-player-${messageId}`);
    audio.setAttribute('src', url);
    audio.classList.add('visible');
    if (autoplay)
        audio.play();
}
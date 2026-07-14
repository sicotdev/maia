
// Speech-to-text functionality using Whisper via backend
function initSTT() {
    const sttBtn = document.getElementById('stt-btn');
    if (!sttBtn) return;

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

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
                inputField.value = data.text;
                // Trigger any input events if necessary
                inputField.dispatchEvent(new Event('input'));
            }
        } catch (err) {
            console.error('Transcription error:', err);
            alert('Erreur de transcription.');
        }
    }
}

document.addEventListener('DOMContentLoaded', initSTT);

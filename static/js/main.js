document.addEventListener('DOMContentLoaded', () => {
    const sttBtn = document.getElementById('stt-btn');
    let recognition;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'fr-FR';

        recognition.onstart = () => {
            sttBtn.classList.add('active');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById('user-input').value = transcript;
            sttBtn.classList.remove('active');
        };

        recognition.onerror = () => {
            sttBtn.classList.remove('active');
        };

        recognition.onend = () => {
            sttBtn.classList.remove('active');
        };
    } else {
        sttBtn.style.display = 'none';
    }

    if (sttBtn) {
        sttBtn.addEventListener('click', () => {
            recognition.start();
        });
    }
});

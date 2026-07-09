
function handleChatBeforeRequest(event) {
    const container = document.getElementById('chat-container');
    const userBubble = document.createElement('div');
    userBubble.className = 'message user-message';
    userBubble.textContent = document.getElementById('user-input').value;
    container.appendChild(userBubble);

    document.getElementById('user-input').value = '';
}

function handleChatAfterRequest(event) {
    const container = document.getElementById('chat-container');
    const data = JSON.parse(event.detail.xhr.responseText);
    console.log('Response data:', data);  // Log the response data for debugging
    
    const chat_line = document.createElement('div');
    chat_line.innerHTML = marked.parse(data.content);
    chat_line.className = 'message ' + (data.error ? 'error-message' : 'ai-message');

    container.appendChild(chat_line);
}

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
        sttBtn.disabled = true;
    }

    if (sttBtn) {
        sttBtn.addEventListener('click', () => {
            recognition.start();
        });
    }
});

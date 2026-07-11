//User new message
function handleChatBeforeRequest(event) {
    appendChatLine(document.getElementById('user-input').value, 'role-user');
    console.log('User message:', document.getElementById('user-input').value);  // Log the user message for debugging

    document.getElementById('user-input').value = '';
}
//AI new message
function handleChatAfterRequest(event) {
    const data = JSON.parse(event.detail.xhr.responseText);
    
    console.log('Response data:', data);  // Log the response data for debugging

    appendChatLine(data.content, data.error ? 'role-error' : 'role-assistant');
    if (data.response_id) {
        document.getElementById('previous_response_id').value = data.response_id;
    }
}

//Parse new chat line with markdown and append to chat container
//TODO: use SSE 
function appendChatLine(message, className) {
    const container = document.getElementById('chat-container');
    const chat_line = document.createElement('div');
    chat_line.className = 'message ' + className;
    chat_line.innerHTML = marked.parse(message, { breaks: true, gfm: true });
    container.appendChild(chat_line);
}

//New line on Shift+Enter, submit on Enter
const textarea = document.querySelector('#user-input');
textarea.addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    document.querySelector('form').requestSubmit();
    textarea.style.height = textarea.style.minHeight; // reset height after submission
  }
  // Shift+Enter: do nothing, let the textarea insert a newline naturally
});
//Auto resize the textarea based on content
textarea.addEventListener('input', function (e) {
    textarea.style.height = 'auto'; // reset height to recalculate
    textarea.style.height = textarea.scrollHeight + 'px';
});


//Speech-to-text functionality
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

//User new message
function handleChatBeforeRequest(event) {

    console.log(event.target);
    
    //Disable buttons
    document.querySelectorAll('#chat-form button').forEach(button => button.disabled = true);

    //Add user message to chat container
    //appendChatLine(document.getElementById('user-input').value, 'role-user');
    document.getElementById('user-input').value = '';
}

function onChatStreamEnd(container) {
    //Re-enable buttons
    document.querySelectorAll('#chat-form button').forEach(button => button.disabled = false);

    console.log(container);
    //TODO: remove message_raw
    //.answer-raw

    //TODO
    //formatTimestamps(chatContainer);
}


//Parse new chat line with markdown and append to chat container
//TODO: call onChatLoad like other messages
/*
function appendChatLine(message, className) {
    const container = document.getElementById('chat-container');
    const chat_line = document.createElement('div');
    chat_line.className = 'message ' + className;
    chat_line.innerHTML = marked.parse(message, { breaks: true, gfm: true });
    container.appendChild(chat_line);
}
    */

function onChatLoad(chatContainer, event) {
    //console.trace('htmx:load fired', event.target)

    chatContainer.querySelectorAll('.message-text:not([data-rendered]), .reasoning .details-body:not([data-rendered])').forEach(text => {
      text.innerHTML = DOMPurify.sanitize(
        marked.parse(text.textContent, { breaks: true, gfm: true })
      );
      text.setAttribute('data-rendered', 'true');
    });

    formatTimestamps(chatContainer);
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

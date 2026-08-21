//User new message
function userInputBeforeRequest(event) {

    const form = event.target;
    
    //Disable buttons & textarea
    form.querySelectorAll('button, textarea').forEach(elem => elem.disabled = true);

    //Reset input
    const textarea = form.querySelector('#user-input');
    textarea.value = '';
    resizeTextarea(textarea);
}

function userInputAfterRequest(event) {

    //Get message added
    const container = document.getElementById('chat-container');
    const userMessages = container.querySelectorAll('.role-user');
    const newMessage = userMessages[userMessages.length-1];

    //Parse message
    parseMd(newMessage.querySelector('.message-text'));
    formatTimestamps(newMessage);
    scrollDown(container);

    //Check if we're streaming ai response or not
    const aiMessage = newMessage.nextElementSibling;
    if (!aiMessage.classList.contains('message-stream')) {
        
        //Not streaming, we can process the answer
        formatTimestamps(aiMessage);
        const aiText = aiMessage.querySelector('.message-text');
        parseMd(aiText, aiText.textContent);

        //Audio
        const messageId = aiText.id.substring("message-text-".length);
        const audioContainer = aiMessage.querySelector(".audio-container");
        if (get_setting('ttsAutoRead'))
            startAudioGeneration(audioContainer.querySelector('button'), messageId);
        
        audioContainer.classList.add("visible");

        //Re-enable buttons and textarea
        document.querySelectorAll('#chat-form button, #chat-form textarea').forEach(elem => elem.disabled = false);

        updateSessionAfterMessage();
    }
}

function onChatSettle(container, event) {
 
    //console.log(container);
    //console.log(event.target);

    scrollDown(container);
}

function onChatStreamDelta(rawAnswer, messageId) {
    const cleanAnswer = document.getElementById(`message-text-${messageId}`).firstElementChild;
    if (rawAnswer && cleanAnswer) {
        parseMd(cleanAnswer, rawAnswer.textContent);
        
        if (get_setting('ttsAutoRead'))
            updateAutoAudioGeneration(cleanAnswer, messageId);
    }
}

function onToolUsed(container) {
    applyDeveloperMode(container);
}

function onChatStreamEnd(message, tmp_id) {

    //Make sure the function is called once (solve bug when the chat is cleared)
    if (message.dataset.streamEnded) return;
        message.dataset.streamEnded = 'true';

    //console.log('chat stream end with: ', message)
    
    //Re-enable buttons and textarea
    document.querySelectorAll('#chat-form button, #chat-form textarea').forEach(elem => elem.disabled = false);
    
    //Remove streamed answer-raw and spinner
    const answerRaw = message.querySelector('.answer-raw');
    if (!answerRaw)
        return; // it means we changed tab and removed the node
    answerRaw.remove();
    const spinner = message.querySelector('.spinner')
    if (!spinner)
        return; // it means we changed tab and removed the node
    spinner.remove();
    
    //Regroup tool calls
    const toolContainer = message.querySelector('.tools-container');
    const toolElems = [...toolContainer.childNodes]; //Convert to array to avoid a dynamic child list since we move them
    if (toolElems.length > 0) {

        const toolCount = toolContainer.querySelectorAll('.tool-info').length;

        const stepContainer = document.createElement("details");
        stepContainer.className = "tool-steps";
        
        const summary = document.createElement("summary");
        summary.textContent = `Outils utilisés (${toolCount})`;
        
        stepContainer.appendChild(summary);
        toolElems.forEach((toolElem) => stepContainer.appendChild(toolElem));
        
        toolContainer.appendChild(stepContainer);
    }

    //Update message id
    const inputMessageId = message.querySelector('#real_message_id');
    const messageId = inputMessageId.value; 
    document.getElementById(`message-text-${tmp_id}`).id = `message-text-${messageId}`;
    inputMessageId.remove();

    //Update previous_response_id
    const inputResponseId = message.querySelector('#response_id');
    const responseId = inputResponseId.value; 
    document.getElementById(`previous_response_id`).value = responseId;
    inputResponseId.remove();

    //Audio
    const audioContainer = message.querySelector(".audio-container");
    if (get_setting('ttsAutoRead'))
        endAudioGeneration(audioContainer.querySelector('button'), tmp_id, messageId);
    
    audioContainer.classList.add("visible");

    updateSessionAfterMessage()
}


//Init user textarea input
function initUserInput() {

    //New line on Shift+Enter, submit on Enter
    const textarea = document.getElementById('user-input');
    textarea.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.querySelector('form').requestSubmit();
            textarea.style.height = textarea.style.minHeight; // reset height after submission
        }
        // Shift+Enter: do nothing, let the textarea insert a newline naturally
    });
    //Auto resize the textarea based on content
    textarea.addEventListener('input', () => resizeTextarea(textarea));

}

function resizeTextarea(textarea) {
    textarea.style.height = 0; // reset height to recalculate
    textarea.style.height = textarea.scrollHeight + 'px';
}

function clearChat() {
    document.getElementById('chat-container').innerHTML = '';
    document.getElementById('session_id').value = '';
    document.getElementById('previous_response_id').value = '';
}

//Update session infos
function updateSessionAfterMessage() {
    const session_id = document.getElementById('session_id').value;
    if (session_id) {
        htmx.ajax('GET', '/sessions/' + session_id, {
            values: { last_active: Date.now() / 1000 },
            target: '#session-' + session_id,
            swap: 'outerHTML'
        }).then(() => {
            document.getElementById('#session-' + session_id).classList.add('selected')
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {

    //TMP because hx-on::oob-after-swap doesn't work
    document.body.addEventListener('htmx:oobAfterSwap', function(evt) {
        if (evt.detail.target.id === 'conversation-list') {
            //Select the new created session
            sessionClickBeforeRequest(evt.detail.target.querySelector('li'));
        }
    });
    
    initUserInput();
});


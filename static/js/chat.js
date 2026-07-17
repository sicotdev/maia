//User new message
function userInputBeforeRequest(event) {

    const form = event.target;
    
    //Disable buttons & textarea
    form.querySelectorAll('button, textarea').forEach(elem => elem.disabled = true);

    //Reset input
    form.querySelector('#user-input').value = '';
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

    //Select the session if a new one was created
    //TODO
}

function onChatSettle(container, event) {
 
    //console.log(container);
    //console.log(event.target);

    scrollDown(container);
}

function onChatStreamDelta(rawAnswer, cleanAnswer) {
    if (rawAnswer && cleanAnswer) {
        parseMd(cleanAnswer, rawAnswer.textContent);
        //TODO: Could start to generate voice here
        //If autoplay active
    }
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
    message.querySelector('.spinner').remove();
    
    //Regroup tool calls
    const toolContainer = message.querySelector('.tools-container');
    const toolElems = [...toolContainer.childNodes]; //Convert to array to avoid a dynamic child list
    if (toolElems.length > 0) {

        const stepContainer = document.createElement("details");
        stepContainer.className = "tool-steps";
        
        const summary = document.createElement("summary");
        summary.textContent = `tool calls (${toolElems.length})`;
        
        stepContainer.appendChild(summary);
        toolElems.forEach((toolElem) => stepContainer.appendChild(toolElem));
        
        toolContainer.appendChild(stepContainer);
    }

    //Update message id
    const input = message.querySelector('#real_message_id');
    const messageId = input.value; 
    document.getElementById(`message-text-${tmp_id}`).id = `message-text-${messageId}`;
    input.remove();

    //Show audio play
    message.querySelector(".audio-container").classList.add("visible");
}


document.addEventListener('DOMContentLoaded', () => {

    //TMP because hx-on::oob-after-swap doesn't work
    document.body.addEventListener('htmx:oobAfterSwap', function(evt) {
        if (evt.detail.target.id === 'conversation-list') {
            sessionClickBeforeRequest(evt.detail.target.querySelector('li'));
        }
    });
    
    initUserInput();
    initSTT();
});

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
    textarea.addEventListener('input', function (e) {
        textarea.style.height = 'auto'; // reset height to recalculate
        textarea.style.height = textarea.scrollHeight + 'px';
    });

}

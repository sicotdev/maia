function sessionSelectionToggle() {
    document.getElementById('conversation-list').classList.toggle('is-selection-mode');

    const button = document.getElementById('btn-delete-selected');
    console.log('disabled='+button.disabled);
    button.disabled = !button.disabled;
}

function onSessionLoaded(container) {
    // Format timestamps in the session tooltip
    formatTimestamps(container);

    // Make sure tooltip is removed when a session is loaded
    const currTooltip = document.getElementById('session_tooltip');
    if (currTooltip)
        currTooltip.remove();

    // Handle tooltip visibility on hover and focus
    handleSessionTooltip(container);
}

function onSessionDeleted(event, sessionId) {
    if (!event.detail.successful) return;
    
    if (sessionId == document.getElementById('session_id').value)
        clearChat();
}

function onSessionsDeleted(event) {
    if (!event.detail.successful) return;
    
    //console.log(event.detail);

    const rawResponse = event.detail.xhr && event.detail.xhr.responseText;
    if (!rawResponse) return;

    try {
        const response = JSON.parse(rawResponse);
        if (!response.successful) return;

        console.log("Response JSON parsed:", response);
        const idsToDelete = response.ids;

        if (!idsToDelete || !Array.isArray(idsToDelete)) return;

        const currSessionId = document.getElementById('session_id').value;
        document.querySelectorAll('.session-row').forEach(el => {
            const sessionId = el.id.substring("session-".length);
            if (idsToDelete.includes(sessionId)) {
                el.remove();
                if (sessionId == currSessionId)
                    clearChat();
            }
        });
    }
    catch (e) {
        console.error("Error parsing JSON response", e);
    }
}

//Select session on click
function sessionClickBeforeRequest(session, target) {
    document.querySelectorAll('.session-row').forEach(el => el.classList.remove('selected'));
    session.classList.add('selected');
}

function sessionClickAfterRequest() {
    const container = document.getElementById('chat-container');

    //Format timestamps and markdown in chat
    formatTimestamps(container);

    container.querySelectorAll('.reasoning .details-body, .message-text').forEach(elem => {
        parseMd(elem);
    });

    showPanel('chat');

    scrollDown(container);
}

function sessionNewBtnClick() {
    clearChat();
    document.querySelectorAll('.session-row').forEach(el => el.classList.remove('selected'));
    showPanel('chat');
}

function handleSessionTooltip(container) {
    const tooltip = container.querySelector('.tooltip');
    if (!tooltip) return;

    const clone = tooltip.cloneNode(true);
    clone.id = 'session_tooltip';
    clone.style.display = "block";

    let rowHover = false;
    let tooltipHower = false;
    let tooltipShown = false;

    const onRowHover = () => {
        rowHover = true;
        if (tooltipShown) return;
        tooltipShown = true;
        showSessionTooltip(container, clone);
    };
    const onRowLeave = () => {
        rowHover = false;
        if (tooltipHower || !tooltipShown) return;
        tooltipShown = false;
        hideSessionTooltip(clone);
    };
    const onTooltipHover = () => {
        tooltipHower = true;
        if (tooltipShown) return;
        tooltipShown = true;
        showSessionTooltip(container, clone);
    };
    const onTooltipLeave = () => {
        tooltipHower = false;
        if (rowHover || !tooltipShown) return;
        tooltipShown = false;
        hideSessionTooltip(clone);
    };

    // Show on mouseenter or focus
    container.addEventListener('mouseenter', onRowHover)
    container.addEventListener('focus', onRowHover, true); // true for capture phase

    // Hide on mouseleave or blur
    container.addEventListener('mouseleave', onRowLeave);
    container.addEventListener('blur', onRowLeave, true); // true for capture phase

    clone.addEventListener('mouseenter', onTooltipHover)
    clone.addEventListener('mouseleave', onTooltipLeave);

    //Edit button
    const editInput = clone.querySelector('.session-title-input');
    const preview = clone.querySelector('.tooltip-preview');
    clone.querySelector('.btn-edit-title').addEventListener('click', () => {
        editInput.classList.toggle('visible');
        preview.classList.toggle('hidden');
    });
}

function showSessionTooltip(container, tooltip) {
    const rect = container.getBoundingClientRect();

    // Add tooltip to body to avoid clipping issues
    document.body.appendChild(tooltip);
    htmx.process(tooltip);
    tooltip.style.position = 'fixed';

    // Check viewport bounds
    if (rect.top + tooltip.offsetHeight + 10 < window.innerHeight) {
        tooltip.style.top = `${rect.top}px`; // place below the row
        tooltip.style.bottom = 'auto'; // reset bottom
    } else {
        tooltip.style.top = 'auto'; // reset top
        tooltip.style.bottom = `${window.innerHeight - rect.bottom}px`;
    }
    tooltip.style.left = `${rect.right}px`;
    tooltip.style.visibility = 'visible';
    tooltip.style.opacity = '1';
}

function hideSessionTooltip(tooltip) {
    const editInput = tooltip.querySelector('.session-title-input');
    const preview = tooltip.querySelector('.tooltip-preview');
    editInput.classList.remove('visible');
    preview.classList.remove('hidden');
    
    tooltip.remove();
}

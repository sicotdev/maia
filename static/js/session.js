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
    document.getElementById('chat-container').innerHTML = '';
    document.getElementById('session_id').value = '';
    document.querySelectorAll('.session-row').forEach(el => el.classList.remove('selected'));
    showPanel('chat');
}


function handleSessionTooltip(container) {
    const tooltip = container.querySelector('.tooltip');
    if (!tooltip) return;

    const clone = tooltip.cloneNode(true);
    clone.id = 'session_tooltip';
    
    // Show on mouseenter or focus
    container.addEventListener('mouseenter', () => showSessionTooltip(container, clone));
    container.addEventListener('focus', () => showSessionTooltip(container, clone), true); // true for capture phase

    // Hide on mouseleave or blur
    container.addEventListener('mouseleave', () => hideSessionTooltip(clone));
    container.addEventListener('blur', () => hideSessionTooltip(clone), true); // true for capture phase
}

function showSessionTooltip(container, tooltip) {
    const rect = container.getBoundingClientRect();

    // Add tooltip to body to avoid clipping issues
    document.body.appendChild(tooltip);
    tooltip.style.position = 'fixed';

    // Check viewport bounds
    if (rect.top + tooltip.offsetHeight + 10 < window.innerHeight) {
        tooltip.style.top = `${rect.top}px`; // place below the row
        tooltip.style.bottom = 'auto'; // reset bottom
    } else {
        tooltip.style.top = 'auto'; // reset top
        tooltip.style.bottom = `${window.innerHeight - rect.bottom}px`;
    }
    tooltip.style.left = `${rect.right + 8}px`; // 8px to the right of the row
    tooltip.style.visibility = 'visible';
    tooltip.style.opacity = '1';
}

function hideSessionTooltip(tooltip) {
    tooltip.remove();
}

function onSessionLoaded(container) {
    // Format timestamps in the session tooltip
    formatTimestamps(container);

    // Handle tooltip visibility on hover and focus
    handleHistoryTooltip(container);
}

function handleHistoryTooltip(container) {
    const tooltip = container.querySelector('.tooltip');
    if (!tooltip) return;

    // Remember where it came from so we can put it back
    const originalParent = tooltip.parentNode;
    const originalNextSibling = tooltip.nextSibling;

    // Show on mouseenter or focus
    container.addEventListener('mouseenter', () => showTooltip(container, tooltip));
    container.addEventListener('focus', () => showTooltip(container, tooltip), true); // true for capture phase

    // Hide on mouseleave or blur
    container.addEventListener('mouseleave', () => hideTooltip(tooltip, originalParent, originalNextSibling));
    container.addEventListener('blur', () => hideTooltip(tooltip, originalParent, originalNextSibling), true); // true for capture phase
}

function showTooltip(container, tooltip) {
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

function hideTooltip(tooltip, originalParent, originalNextSibling) {
    tooltip.style.visibility = 'hidden';
    tooltip.style.opacity = '0';
    // put it back in its original spot in the DOM
    originalParent.insertBefore(tooltip, originalNextSibling);
}
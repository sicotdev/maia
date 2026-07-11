function onSessionLoaded(container) {
    // Format timestamps in the session tooltip
    const timestamps = container.querySelectorAll(".timestamp");
    timestamps.forEach(span => {
        const date = new Date(parseInt(span.textContent) * 1000);
        span.textContent = date.toLocaleString();
    });

    //Handle tooltip visibility on hover and focus
    handleHistoryTooltip(container);
}

function handleHistoryTooltip(container) {
    const tooltip = container.querySelector('.tooltip');
    if (!tooltip) return;

    // remember where it came from so we can put it back
    const originalParent = tooltip.parentNode;
    const originalNextSibling = tooltip.nextSibling;

    function showTooltip() {
        const rect = container.getBoundingClientRect();

        document.body.appendChild(tooltip);
        tooltip.style.position = 'fixed';
        //Check viewport bounds
        if (rect.top + tooltip.offsetHeight + 10 < window.innerHeight) {
            tooltip.style.top = `${rect.top}px`; // place below the row
            tooltip.style.bottom = 'auto'; // reset bottom
        } else {
            tooltip.style.top = 'auto'; // reset top
            tooltip.style.bottom = `${window.innerHeight - rect.bottom}px`;
        }
        //tooltip.style.bottom = `${window.innerHeight - rect.bottom}px`;
        tooltip.style.left = `${rect.right + 8}px`; // 8px to the right of the row
        tooltip.style.visibility = 'visible';
        tooltip.style.opacity = '1';
    }

    function hideTooltip() {
        tooltip.style.visibility = 'hidden';
        tooltip.style.opacity = '0';
        // put it back in its original spot in the DOM
        originalParent.insertBefore(tooltip, originalNextSibling);
    }

    // Show on mouseenter or focus
    container.addEventListener('mouseenter', showTooltip);
    container.addEventListener('focus', showTooltip, true); // true for capture phase

    // Hide on mouseleave or blur
    container.addEventListener('mouseleave', hideTooltip);
    container.addEventListener('blur', hideTooltip, true); // true for capture phase
}
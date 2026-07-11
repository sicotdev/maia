function formatTimestamps(container) {
    const timestamps = container.querySelectorAll(".timestamp");
    timestamps.forEach(span => {
        const date = new Date(parseInt(span.textContent) * 1000);
        span.textContent = date.toLocaleString();
    });
}
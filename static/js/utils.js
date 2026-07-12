function formatTimestamps(container) {
    const timestamps = container.querySelectorAll(".timestamp:not([data-converted])");
    timestamps.forEach(span => {
        //console.log("converting " + parseInt(span.textContent));
        const date = new Date(parseInt(span.textContent) * 1000);
        span.textContent = date.toLocaleDateString(undefined, { year: '2-digit', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
        span.setAttribute('data-converted', 'true');
    });
}
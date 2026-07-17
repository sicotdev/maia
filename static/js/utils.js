function formatTimestamps(container) {
    const timestamps = container.querySelectorAll(".timestamp:not([data-converted])");
    timestamps.forEach(span => {
        //console.log("converting " + parseInt(span.textContent));
        const date = new Date(parseInt(span.textContent) * 1000);
        span.textContent = date.toLocaleDateString(undefined, { year: '2-digit', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
        span.setAttribute('data-converted', 'true');
    });
}

const camelToKebab = (str) => {
  return str
    .replace(/([A-Z])/g, '-$1')  // Add a hyphen before each uppercase letter
    .toLowerCase()               // Convert everything to lowercase
    .replace(/^-/, '');          // Remove the leading hyphen if the string started with an uppercase letter
};

function scrollDown(container) {
    container.scrollTop = container.scrollHeight
}

function parseMd(target, textContent) {
    textContent = textContent !== undefined ? textContent : target.textContent;

    target.innerHTML = DOMPurify.sanitize(
        marked.parse(textContent, { breaks: true, gfm: true })
    );
}
//TTS streamed from backend
const queue = [];
let playing = false;
let loading = false;
let autoRunning = false;
let ending = false;

let chunkIndex = 0;

function enqueueAudio(url) {
    queue.push(url);
    if (!playing) playNext();
}

function playNext() {
    if (queue.length === 0) { playing = false; return; }
    playing = true;
    const url = queue.shift();
    const audio = new Audio(`${url}${DEBUG?'?t='+Date.now():''}`);
    audio.volume = get_setting('ttsVolume') / 100;
    audio.playbackRate = get_setting('ttsSpeed');
    audio.play();
    audio.onended = playNext;
}

//This is called at each text delta if auto speak is active
function updateAutoAudioGeneration(cleanAnswer, messageId) {
    if (autoRunning) return;
    autoRunning = true;

    chunkIndex = 0;
    loading = false;
    ending = false;
    
    autoRunningLoop(cleanAnswer, messageId);
}

async function autoRunningLoop(cleanAnswer, messageId) {

    while(autoRunning) {
    
        //Wait for last chunk generation
        const ended = await waitLoadingEnded();
        if (!ended) {
            console.error("Last audio generation didn't end")
            return; // something went wrong
        }

        const text = getTextWithoutCode(cleanAnswer);

        //Split ignoring empty chunk
        const chunks = text.split('\n').map(chunk => chunk.trim()).filter(chunk => chunk);

        //Wait to have the beginning of the next chunk
        if (chunks.length <= chunkIndex + 1) {
            await sleep(100)
            continue;
        }
        
        //Load chunk audio
        loading = true;
        const chunkToSpeak = chunks[chunkIndex];
        
        await requestChunk(messageId, chunkToSpeak, chunkIndex);
        chunkIndex += 1;
    }
}

async function requestChunk(messageId, chunkToSpeak, chunkIndex) {

    const qs = `engine=${get_setting('ttsEngine')}&voice=${get_setting('ttsVoice')}` 
            + `&message_id=${messageId}&text=${encodeURIComponent(chunkToSpeak)}&chunk_index=${chunkIndex}`
    const url = `/v1/voice/generate_chunk?${qs}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Error getting audio chunk');
    const data = await response.json();
    
    enqueueAudio(data.audio);
    loading = false;
}

function endAudioGeneration(button, tmp_id, messageId) {
    button.remove();
    generateAllChunks(tmp_id, messageId);
}

async function generateAllChunks(tmp_id, messageId) {

    autoRunning = false; // stop the chunk loop

    //We're still ending the previous message
    if (ending) {
        const endingDone = await waitLoadingEnded();
        if (!endingDone) {
            console.error("Last audio generation didn't end")
            return; // something went wrong
        }
    }
    ending = true;

    const text = getTextWithoutCode(document.getElementById(`message-text-${messageId}`));

    //Split ignoring empty chunk
    const chunks = text.split('\n').map(chunk => chunk.trim()).filter(chunk => chunk);

    //Empty text
    if (chunks.length == 0) {
        ending = false;
        return;
    }

    //Wait for last chunk generation
    const ended = await waitLoadingEnded();
    if (!ended) {
        console.error("Last audio generation didn't end")
        return; // something went wrong
    }
    loading = true;

    //Continue to generate the remaining chunks with tmp_id
    for (let i = chunkIndex; i < chunks.length; i++) {
        loading = true;
        await requestChunk(tmp_id, chunks[i], i)
    }
    loading = true;
    
    //Merge chunk and update message_id
    const url = `/v1/voice/merge_chunks?tmp_id=${tmp_id}&message_id=${messageId}&chunk_length=${chunks.length}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Error getting final audio');
    const data = await response.json();

    //Show final <audio>
    showFinalAudioPlayer(messageId, data.audio);

    //Reset for next audio generation
    chunkIndex = 0;
    loading = false;
    ending = false;
}

async function waitLoadingEnded() {
    let loopCount = 300; // we wait 30 sec max
    let loopIndex = 0;
    while (loading && loopIndex++ < loopCount) {
        await sleep(100);
    }
    return !loading;
}
async function waitEnding() {
    let loopCount = 300; // we wait 30 sec max
    let loopIndex = 0;
    while (ending && loopIndex++ < loopCount) {
        await sleep(100);
    }
    return !ending;
}

//Called manually with button if auto speak not active
async function startAudioGeneration(button, messageId) {
    if (button.disabled) return; // should not happen, better safe than sorry

    button.disabled = true;
    button.innerHTML = "<span class='spinner'></span>";
    button.classList.remove('error');

    //Send the entire text
    const text = getTextWithoutCode(document.getElementById(`message-text-${messageId}`));
    const qs = `engine=${get_setting('ttsEngine')}&voice=${get_setting('ttsVoice')}` 
            + `&message_id=${messageId}&text=${encodeURIComponent(text)}`
    const url = `/v1/voice/generate?${qs}`;
    const evtSource = new EventSource(url);

    let chunkReceived = false;
    evtSource.addEventListener('chunk', (event) => {
        chunkReceived = true;
        enqueueAudio(event.data);
    });

    evtSource.addEventListener('done', () => {
        const finalAudioUrl = event.data;
        const autoplay = !chunkReceived; // meaning we already had the final wav file
        button.remove();
        showFinalAudioPlayer(messageId, finalAudioUrl, autoplay);
        evtSource.close();
    });

    evtSource.onerror = (err) => {
        console.error('SSE error:', err);
        evtSource.close();
        button.disabled = false;
        button.innerHTML = "Error: Réessayer";
        button.classList.add('error');
    };

    return evtSource;
}

function showFinalAudioPlayer(messageId, url, autoplay = false) {
    const audio = document.getElementById(`audio-player-${messageId}`);
    if (!audio) // happens if we change session
        return;

    audio.setAttribute('src', `${url}${DEBUG?'?t='+Date.now():''}`);
    audio.classList.add('visible');

    audio.volume = get_setting('ttsVolume') / 100;
    audio.playbackRate = get_setting('ttsSpeed');

    if (autoplay)
        audio.play();
}

//TODO: put this elsewhere
function isCodeOnly(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return node.textContent.trim() === '';
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return true; // comments, etc. — ignore
    }
    if (node.tagName === 'CODE' || node.tagName === 'TABLE') {
        return true;
    }

    const children = Array.from(node.childNodes);
    if (children.length === 0) {
        // Empty element (e.g. <br>, <hr>, <img>) — not code, so keep it
        return false;
    }

    return children.every(isCodeOnly);
}

function stripCode(node) {
    Array.from(node.children).forEach(child => {
        if (isCodeOnly(child)) {
            if (child.tagName === 'CODE') {
                // Lone/mixed-context code element -> unwrap, keep text
                child.replaceWith(document.createTextNode(child.textContent));
            } else {
                // Container (p, li, ul, div...) that's ENTIRELY code -> drop it
                child.remove();
            }
        } else {
            // Mixed content -> recurse deeper
            stripCode(child);
        }
    });
}

function getTextWithoutCode(original) {
    const clone = original.cloneNode(true);

    stripCode(clone);

    clone.style.position = 'absolute';
    clone.style.left = '-9999px';
    clone.style.top = '0';

    document.body.appendChild(clone);
    const text = clone.innerText;
    document.body.removeChild(clone);

    return text;
}
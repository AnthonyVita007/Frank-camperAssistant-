//----------------------------------------------------------------
// JavaScript per modalità DEBUG - Log testuale
//----------------------------------------------------------------

//----------------------------------------------------------------
// Connessione Socket.IO e riferimenti DOM
//----------------------------------------------------------------
const socket = io();

const logContainer = document.getElementById('log-container');
const inputEl = document.getElementById('command-input');
const sendBtn = document.getElementById('send-button');

// Riferimenti switch AI
const aiSwitch = document.getElementById('ai-switch');
const aiToggle = document.getElementById('ai-toggle');

//----------------------------------------------------------------
// helper: append al log con autoscroll e ritorno bubble element
//----------------------------------------------------------------
function appendLog(message, origin = 'system', renderMarkdown = false) {
    //----------------------------------------------------------------
    // CREAZIONE WRAPPER CHAT E BOLLA
    //----------------------------------------------------------------
    const wrapper = document.createElement('div');
    wrapper.className = 'chat';

    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (
        origin === 'user' ? 'bubble-user' :
        origin === 'backend' ? 'bubble-backend' : 'bubble-system'
    );

    //----------------------------------------------------------------
    // RENDER CONTENUTO (MD OPZIONALE) E INSERIMENTO IN DOM
    //----------------------------------------------------------------
    if (renderMarkdown && typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        try {
            const html = marked.parse(String(message || ''));
            bubble.innerHTML = DOMPurify.sanitize(html);
        } catch (error) {
            console.warn('[Debug] Markdown rendering failed, using plain text:', error);
            bubble.textContent = String(message || '');
        }
    } else {
        bubble.textContent = String(message || '');
    }

    wrapper.appendChild(bubble);
    logContainer.appendChild(wrapper);

    //----------------------------------------------------------------
    // AUTOSCROLL E RITORNO RIFERIMENTO ALLA BOLLA
    //----------------------------------------------------------------
    logContainer.scrollTop = logContainer.scrollHeight;

    return bubble;
}

//----------------------------------------------------------------
// helper: pulisci tutto il log
//----------------------------------------------------------------
function clearLog() {
    logContainer.innerHTML = '';
}

//----------------------------------------------------------------
// helper: invio comando
//----------------------------------------------------------------
function sendCommand() {
    const text = (inputEl.value || '').trim();
    if (!text) return;

    appendLog(text, 'user');
    socket.emit('frontend_command', { data: text });

    inputEl.value = '';
    inputEl.focus();
}

//----------------------------------------------------------------
// Eventi Socket.IO - connessione e risposte
//----------------------------------------------------------------
socket.on('connect', () => {
    appendLog('Connessione al backend stabilita.', 'system');
});

socket.on('backend_response', (payload) => {
    const msg = payload && payload.data ? payload.data : '(risposta vuota)';
    const isAI = payload && payload.type === 'ai_response';
    appendLog(msg, 'backend', !!isAI);
});

socket.on('backend_action', (payload) => {
    const action = payload && payload.action;

    if (action === 'clear_log') {
        clearLog();
        return;
    }

    if (action === 'navigate') {
        const url = payload && payload.data;
        if (url) {
            appendLog(`Navigazione verso: ${url}`, 'system');
            window.location.href = url;
        }
        return;
    }
    
    if (action === 'update_ai_provider') {
        const actualProvider = payload && payload.data;
        if (actualProvider && aiSwitch) {
            // Aggiorna UI per riflettere il provider effettivamente attivo (fallback)
            setSwitchUI(actualProvider);
            appendLog(`UI aggiornata per provider: ${actualProvider === 'gemini' ? 'CLOUD (Gemini)' : 'LOCAL (llama.cpp)'}`, 'system');
        }
        return;
    }
});

//----------------------------------------------------------------
// EVENTI SOCKET.IO PER STREAMING
//----------------------------------------------------------------
let streamingBubbles = new Map();

socket.on('backend_stream_start', (payload) => {
    const requestId = payload && payload.request_id;
    if (!requestId) {
        console.warn('Ricevuto backend_stream_start senza request_id');
        return;
    }
    const streamBubble = appendLog('', 'backend', false);
    streamingBubbles.set(requestId, {
        element: streamBubble,
        content: '',
        startTime: Date.now()
    });
    console.debug(`Streaming iniziato per request ${requestId}`);
});

socket.on('backend_stream_chunk', (payload) => {
    const requestId = payload && payload.request_id;
    const delta = payload && payload.delta;
    if (!requestId || !streamingBubbles.has(requestId)) {
        console.warn('Ricevuto chunk per request_id sconosciuto:', requestId);
        return;
    }
    if (delta) {
        const streamData = streamingBubbles.get(requestId);
        streamData.content += delta;
        streamData.element.textContent = streamData.content;
        logContainer.scrollTop = logContainer.scrollHeight;
    }
});

socket.on('backend_stream_end', (payload) => {
    const requestId = payload && payload.request_id;
    const finalText = payload && payload.final;
    const metadata = payload && payload.metadata;

    if (!requestId) {
        console.warn('Ricevuto backend_stream_end senza request_id');
        return;
    }

    if (streamingBubbles.has(requestId)) {
        const streamData = streamingBubbles.get(requestId);
        const duration = Date.now() - streamData.startTime;

        if (finalText) {
            streamData.element.textContent = finalText;
        }

        streamingBubbles.delete(requestId);
        console.debug(`Streaming completato per request ${requestId} in ${duration}ms`);

        if (metadata && metadata.chunk_count) {
            console.debug(`Streaming stats: ${metadata.chunk_count} chunks, ${metadata.total_length} chars`);
        }
    }
});

//----------------------------------------------------------------
// Disconnessioni / errori
//----------------------------------------------------------------
socket.on('disconnect', () => {
    appendLog('Disconnesso dal backend.', 'system');
});

socket.on('connect_error', (err) => {
    appendLog(`Errore di connessione: ${err.message || err}`, 'system');
});

// Tool notification handlers for debug mode
socket.on('backend_tool_notification', (payload) => {
    const { tool_name, status, timestamp } = payload;
    let message = '';
    let icon = '';
    
    switch (status) {
        case 'selected':
            icon = '🔧';
            message = `Tool selezionato: ${tool_name}`;
            break;
        case 'starting':
            icon = '▶️';
            message = `Avvio tool: ${tool_name}`;
            break;
        case 'closing':
            icon = '⏹️';
            message = `Chiusura tool: ${tool_name}`;
            break;
        default:
            icon = '🔧';
            message = `${tool_name} → ${status}`;
    }
    
    appendLog(`${icon} ${message}`, 'system');
});

socket.on('backend_parameter_request', (payload) => {
    const { tool_name, missing_params, clarification_question } = payload;
    appendLog(`❓ Richiesta parametri per ${tool_name}: ${clarification_question}`, 'system');
    appendLog(`📝 Parametri mancanti: ${missing_params.join(', ')}`, 'system');
});

//----------------------------------------------------------------
// Interazione utente base (invio comandi)
//----------------------------------------------------------------
sendBtn.addEventListener('click', sendCommand);

inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        sendCommand();
    }
});

window.addEventListener('keydown', (e) => {
    const isCtrlL = (e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L');
    if (isCtrlL) {
        e.preventDefault();
        clearLog();
    }
});

window.addEventListener('load', () => {
    inputEl.focus();
});

//----------------------------------------------------------------
// SWITCH AI: gestione toggle LOCAL ↔ CLOUD (Gemini)
//----------------------------------------------------------------
function getCurrentProvider() {
    // Se aria-pressed è true → CLOUD (gemini), altrimenti LOCAL
    return aiSwitch && aiSwitch.classList.contains('on') ? 'gemini' : 'local';
}

function setSwitchUI(provider) {
    // provider: 'local' | 'gemini'
    if (!aiSwitch) return;

    const isCloud = provider === 'gemini';
    aiSwitch.classList.toggle('on', isCloud);
    aiSwitch.setAttribute('aria-pressed', isCloud ? 'true' : 'false');
    aiSwitch.dataset.provider = isCloud ? 'gemini' : 'local';
    aiSwitch.setAttribute('aria-label', isCloud ? 'Disattiva CLOUD (Gemini)' : 'Attiva CLOUD (Gemini)');
}

function emitProviderToggle(provider) {
    // Emissione evento al backend
    socket.emit('ui_ai_provider_toggle', { provider });
}

if (aiSwitch) {
    // Stato iniziale (default: LOCAL come da specifica)
    setSwitchUI('local');

    // Click → toggle UI + emit evento
    aiSwitch.addEventListener('click', () => {
        const current = getCurrentProvider();
        const next = current === 'local' ? 'gemini' : 'local';

        // Aggiorna UI subito (ottimistico)
        setSwitchUI(next);

        // Info utente
        appendLog(`Cambio provider AI → ${next === 'gemini' ? 'CLOUD (Gemini)' : 'LOCAL (llama.cpp)'}`, 'system');

        // Richiesta backend
        emitProviderToggle(next);
    });
}
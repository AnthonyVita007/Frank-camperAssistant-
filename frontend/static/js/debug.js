//----------------------------------------------------------------
// JavaScript per modalità DEBUG - Log testuale
//----------------------------------------------------------------

//connessione
const socket = io();

const logContainer = document.getElementById('log-container');

const inputEl = document.getElementById('command-input');

const sendBtn = document.getElementById('send-button');

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

    // Restituiamo la bubble così lo streaming può aggiornarla in tempo reale
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
// Eventi Socket.IO
//----------------------------------------------------------------

// connessione stabilita
//connessione
socket.on('connect', () => {
    
    appendLog('Connessione al backend stabilita.', 'system');
});

// risposta dal backend
//connessione
socket.on('backend_response', (payload) => {
    
    const msg = payload && payload.data ? payload.data : '(risposta vuota)';
    const isAI = payload && payload.type === 'ai_response';
    
    appendLog(msg, 'backend', !!isAI);
});

// azioni strutturate dal backend
//connessione
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
});

//----------------------------------------------------------------
// EVENTI SOCKET.IO PER STREAMING
//----------------------------------------------------------------

// Mappa per tenere traccia delle bubble di streaming attive
//streaming
let streamingBubbles = new Map();

// Inizio streaming - crea una bubble vuota
//streaming
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

// Chunk di streaming - appendi contenuto incrementalmente  
//streaming
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
        
        // Aggiorna il contenuto della bubble in tempo reale
        //streaming
        streamData.element.textContent = streamData.content;
        
        // Autoscroll per seguire il testo che appare
        //streaming
        logContainer.scrollTop = logContainer.scrollHeight;
        
    }
});

// Fine streaming - finalizza la bubble
//streaming  
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
        
        // Finalizza il contenuto con il testo finale
        //streaming
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

// disconnessione / errori
//connessione
socket.on('disconnect', () => {
    
    appendLog('Disconnesso dal backend.', 'system');
});
//connessione
socket.on('connect_error', (err) => {
    
    appendLog(`Errore di connessione: ${err.message || err}`, 'system');
});

//----------------------------------------------------------------
/**
 * Interazione utente
 */
//----------------------------------------------------------------

// click bottone
//connessione
sendBtn.addEventListener('click', sendCommand);

// invio con Enter
//connessione
inputEl.addEventListener('keydown', (e) => {
    
    if (e.key === 'Enter') {
        
        sendCommand();
    }
});

// scorciatoia: Ctrl+L per pulire la console localmente
//connessione
window.addEventListener('keydown', (e) => {
    
    const isCtrlL = (e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L');
    
    if (isCtrlL) {
        
        e.preventDefault();
        
        clearLog();
        
    }
});

// focus iniziale
//connessione
window.addEventListener('load', () => {
    
    inputEl.focus();
});
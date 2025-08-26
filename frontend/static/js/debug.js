//----------------------------------------------------------------
// JavaScript per modalità DEBUG - Log testuale
//----------------------------------------------------------------

//connessione
const socket = io();
//...
const logContainer = document.getElementById('log-container');
//...
const inputEl = document.getElementById('command-input');
//...
const sendBtn = document.getElementById('send-button');

// helper: append al log con autoscroll
//connessione
function appendLog(message, origin = 'system', renderMarkdown = false) {
    // Create chat wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'chat';

    // Create bubble element
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (
        origin === 'user' ? 'bubble-user' :
        origin === 'backend' ? 'bubble-backend' : 'bubble-system'
    );

    // Handle content rendering
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

    // Append to DOM
    wrapper.appendChild(bubble);
    logContainer.appendChild(wrapper);
    
    // Auto-scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}

// helper: pulisci tutto il log
//connessione
function clearLog() {
    //...
    logContainer.innerHTML = '';
    //...
}

// helper: invio comando
//connessione
function sendCommand() {
    //...
    const text = (inputEl.value || '').trim();
    //...
    if (!text) return;
    //...
    appendLog(text, 'user');
    //...
    socket.emit('frontend_command', { data: text });
    //...
    inputEl.value = '';
    //...
    inputEl.focus();
}

//----------------------------------------------------------------
// Eventi Socket.IO
//----------------------------------------------------------------

// connessione stabilita
//connessione
socket.on('connect', () => {
    //...
    appendLog('Connessione al backend stabilita.', 'system');
});

// risposta dal backend
//connessione
socket.on('backend_response', (payload) => {
    //...
    const msg = payload && payload.data ? payload.data : '(risposta vuota)';
    const isAI = payload && payload.type === 'ai_response';
    //...
    appendLog(msg, 'backend', !!isAI);
});

// azioni strutturate dal backend
//connessione
socket.on('backend_action', (payload) => {
    //...
    const action = payload && payload.action;
    //...
    if (action === 'clear_log') {
        //...
        clearLog();
        //...
        return;
    }
    //...
    if (action === 'navigate') {
        //...
        const url = payload && payload.data;
        //...
        if (url) {
            //...
            appendLog(`Navigazione verso: ${url}`, 'system');
            //...
            window.location.href = url;
        }
        //...
        return;
    }
    
    // Navigation actions (debug mode: text only)
    if (action === 'open_navigator') {
        appendLog('Navigazione richiesta - modalità debug (solo testo)', 'system');
        return;
    }
    
    if (action === 'render_route') {
        const routeData = payload && payload.data;
        if (routeData) {
            // Display navigation info as text in debug mode
            const stats = routeData.stats || {};
            const warnings = routeData.warnings || [];
            
            appendLog(`Route calcolata: ${stats.distance_km || 0} km, ${stats.duration_min || 0} min`, 'system');
            
            if (warnings.length > 0) {
                appendLog(`Avvisi (${warnings.length}):`, 'system');
                warnings.forEach(warning => {
                    appendLog(`- ${warning.type || 'Avviso'}: ${warning.message}`, 'system');
                });
            } else {
                appendLog('Nessun avviso per questo percorso', 'system');
            }
        }
        return;
    }
    
    //... eventuali altre azioni future
});

// disconnessione / errori
//connessione
socket.on('disconnect', () => {
    //...
    appendLog('Disconnesso dal backend.', 'system');
});
//connessione
socket.on('connect_error', (err) => {
    //...
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
    //...
    if (e.key === 'Enter') {
        //...
        sendCommand();
    }
});

// scorciatoia: Ctrl+L per pulire la console localmente
//connessione
window.addEventListener('keydown', (e) => {
    //...
    const isCtrlL = (e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L');
    //...
    if (isCtrlL) {
        //...
        e.preventDefault();
        //...
        clearLog();
        //...
    }
});

// focus iniziale
//connessione
window.addEventListener('load', () => {
    //...
    inputEl.focus();
});
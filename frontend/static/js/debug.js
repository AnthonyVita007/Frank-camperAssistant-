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
function appendLog(message, origin = 'system') {
    //...
    const line = document.createElement('div');
    //...
    const prefix = origin === 'user' ? 'Tu' : origin === 'backend' ? 'Frank' : 'Sistema';
    //...
    line.textContent = `[${prefix}] ${message}`;
    //...
    logContainer.appendChild(line);
    //...
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
    //...
    appendLog(msg, 'backend');
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
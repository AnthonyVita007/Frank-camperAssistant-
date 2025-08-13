//----------------------------------------------------------------
// Gestisce: connessione Socket.IO, invio comandi, rendering del log.
//----------------------------------------------------------------

//----------------------------------------------------------------
// INIZIALIZZAZIONE E UTILS
//----------------------------------------------------------------

// connessione
const socket = io();

// riferimenti DOM
const logContainer = document.getElementById('log-container');
const inputEl = document.getElementById('command-input');
const sendBtn = document.getElementById('send-button');

// helper: append al log con autoscroll
function appendLog(message, origin = 'system') {
    const line = document.createElement('div');
    // Prefisso origin per chiarezza (utente, backend, sistema)
    const prefix = origin === 'user' ? 'Tu' : origin === 'backend' ? 'Frank' : 'Sistema';
    line.textContent = `[${prefix}] ${message}`;
    logContainer.appendChild(line);
    // autoscroll
    logContainer.scrollTop = logContainer.scrollHeight;
}

//----------------------------------------------------------------
// EVENTI SOCKET.IO
//----------------------------------------------------------------

// connessione stabilita
socket.on('connect', () => {
    appendLog('Connessione al backend stabilita.', 'system');
});

// risposta dal backend (main_controller.py emette 'backend_response')
socket.on('backend_response', (payload) => {
    const msg = payload && payload.data ? payload.data : '(risposta vuota)';
    appendLog(msg, 'backend');
});

// disconnessione / errori
socket.on('disconnect', () => {
    appendLog('Disconnesso dal backend.', 'system');
});

socket.on('connect_error', (err) => {
    appendLog(`Errore di connessione: ${err.message || err}`, 'system');
});

//----------------------------------------------------------------
// INTERAZIONE UTENTE
//----------------------------------------------------------------

// invio comando
function sendCommand() {
    const text = (inputEl.value || '').trim();
    if (!text) return;
    appendLog(text, 'user');
    socket.emit('frontend_command', { data: text });
    inputEl.value = '';
    inputEl.focus();
}

// click bottone
sendBtn.addEventListener('click', sendCommand);

// invio con Enter
inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        sendCommand();
    }
});

// focus iniziale
window.addEventListener('load', () => inputEl.focus());
//----------------------------------------------------------------
// JavaScript per modalità UTENTE - Tile interattivi
//----------------------------------------------------------------

//connessione
const socket = io();
//...
const inputEl = document.getElementById('command-input');
//...
const sendBtn = document.getElementById('send-button');

// helper: invio comando
//connessione
function sendCommand() {
    //...
    const text = (inputEl.value || '').trim();
    //...
    if (!text) return;
    //...
    console.log('[User] Comando inviato:', text);
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
    console.log('[User] Connesso al backend');
});

// risposta dal backend
//connessione
socket.on('backend_response', (payload) => {
    //...
    const msg = payload && payload.data ? payload.data : '(risposta vuota)';
    //...
    console.log('[User] Risposta backend:', msg);
    //...
    // In user mode, potresti mostrare notifiche o aggiornare UI
    //...
});

// azioni strutturate dal backend
//connessione
socket.on('backend_action', (payload) => {
    //...
    const action = payload && payload.action;
    //...
    console.log('[User] Azione backend:', action, payload);
    //...
    if (action === 'navigate') {
        //...
        const url = payload && payload.data;
        //...
        if (url) {
            //...
            console.log('[User] Navigazione verso:', url);
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
    console.log('[User] Disconnesso dal backend');
});
//connessione
socket.on('connect_error', (err) => {
    //...
    console.log('[User] Errore di connessione:', err.message || err);
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

// focus iniziale
//connessione
window.addEventListener('load', () => {
    //...
    inputEl.focus();
});

//----------------------------------------------------------------
/**
 * Tile interattivi → inviano comandi al backend
 */
//----------------------------------------------------------------

//connessione
function bindTiles() {
    //...
    const tVehicle = document.getElementById('tile-vehicle');
    //...
    const tLocation = document.getElementById('tile-location');
    //...
    const tNetwork = document.getElementById('tile-network');
    //...
    const tMaint = document.getElementById('tile-maintenance');
    //...
    const tWeather = document.getElementById('tile-weather');
    //...
    const tSettings = document.getElementById('tile-settings');

    //...
    if (tVehicle) tVehicle.addEventListener('click', () => {
        //...
        console.log('[User] Click tile: Stato veicolo');
        //...
        socket.emit('frontend_command', { data: 'stato veicolo' });
    });
    //...
    if (tLocation) tLocation.addEventListener('click', () => {
        //...
        console.log('[User] Click tile: Posizione');
        //...
        socket.emit('frontend_command', { data: 'posizione' });
    });
    //...
    if (tNetwork) tNetwork.addEventListener('click', () => {
        //...
        console.log('[User] Click tile: Stato rete');
        //...
        socket.emit('frontend_command', { data: 'stato rete' });
    });
    //...
    if (tMaint) tMaint.addEventListener('click', () => {
        //...
        console.log('[User] Click tile: Manutenzione');
        //...
        socket.emit('frontend_command', { data: 'mostra manutenzione' });
    });
    //...
    if (tWeather) tWeather.addEventListener('click', () => {
        //...
        console.log('[User] Click tile: Meteo');
        //...
        socket.emit('frontend_command', { data: 'meteo' });
    });
    //...
    if (tSettings) tSettings.addEventListener('click', () => {
        //...
        console.log('[User] Click tile: Impostazioni');
        //...
        socket.emit('frontend_command', { data: 'impostazioni' });
    });
}

//connessione
window.addEventListener('load', bindTiles);
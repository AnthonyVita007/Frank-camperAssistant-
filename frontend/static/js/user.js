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

// Tool notification handlers
socket.on('backend_tool_notification', (payload) => {
    console.log('[User] Tool notification received:', payload);
    handleToolNotification(payload);
});

socket.on('backend_parameter_request', (payload) => {
    console.log('[User] Parameter request received:', payload);
    handleParameterRequest(payload);
});

//----------------------------------------------------------------
/**
 * Tool notification and visual feedback system
 */
//----------------------------------------------------------------

let currentToolNotification = null;
let toolActiveIndicator = null;

function handleToolNotification(payload) {
    const { tool_name, status, timestamp } = payload;
    
    // Remove existing notification
    if (currentToolNotification) {
        removeToolNotification();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `tool-notification ${status}`;
    
    // Set notification content based on status
    let message = '';
    switch (status) {
        case 'selected':
            message = `Tool selezionato → ${tool_name}`;
            break;
        case 'starting':
            message = `Avvio tool → ${tool_name}`;
            showToolActiveIndicator();
            break;
        case 'closing':
            message = `Chiusura tool → ${tool_name}`;
            hideToolActiveIndicator();
            break;
        default:
            message = `${tool_name} → ${status}`;
    }
    
    notification.textContent = message;
    
    // Add cancel button for selected status
    if (status === 'selected') {
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'cancel-btn';
        cancelBtn.textContent = 'Annulla';
        cancelBtn.onclick = () => {
            socket.emit('frontend_command', { data: 'annulla' });
            removeToolNotification();
        };
        notification.appendChild(cancelBtn);
    }
    
    // Add to DOM
    document.body.appendChild(notification);
    currentToolNotification = notification;
    
    // Auto-remove after delay (except for starting status)
    if (status !== 'starting') {
        setTimeout(() => {
            removeToolNotification();
        }, status === 'selected' ? 5000 : 3000);
    }
}

function handleParameterRequest(payload) {
    const { tool_name, missing_params, clarification_question } = payload;
    
    // Create parameter request notification
    const notification = document.createElement('div');
    notification.className = 'tool-notification selected';
    notification.innerHTML = `
        <div>${clarification_question}</div>
        <button class="cancel-btn" onclick="cancelParameterCollection()">Annulla</button>
    `;
    
    // Remove existing notification and add new one
    if (currentToolNotification) {
        removeToolNotification();
    }
    
    document.body.appendChild(notification);
    currentToolNotification = notification;
}

function removeToolNotification() {
    if (currentToolNotification) {
        currentToolNotification.classList.add('closing');
        setTimeout(() => {
            if (currentToolNotification && currentToolNotification.parentNode) {
                currentToolNotification.parentNode.removeChild(currentToolNotification);
            }
            currentToolNotification = null;
        }, 300);
    }
}

function showToolActiveIndicator() {
    if (!toolActiveIndicator) {
        toolActiveIndicator = document.createElement('div');
        toolActiveIndicator.className = 'tool-active-indicator';
        document.body.appendChild(toolActiveIndicator);
    }
}

function hideToolActiveIndicator() {
    if (toolActiveIndicator) {
        toolActiveIndicator.remove();
        toolActiveIndicator = null;
    }
}

function cancelParameterCollection() {
    socket.emit('frontend_command', { data: 'annulla' });
    removeToolNotification();
}

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
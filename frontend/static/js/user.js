//----------------------------------------------------------------
// JavaScript per modalità UTENTE - Tile interattivi e Navigazione
//----------------------------------------------------------------

//connessione
const socket = io();
//...
const inputEl = document.getElementById('command-input');
//...
const sendBtn = document.getElementById('send-button');

// Navigation variables
let map = null;
let routeLayer = null;
let isNavigationMode = false;

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
    
    // Navigation actions
    if (action === 'open_navigator') {
        openNavigationMode();
        return;
    }
    
    if (action === 'render_route') {
        const routeData = payload && payload.data;
        if (routeData) {
            renderRoute(routeData);
        }
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

//----------------------------------------------------------------
/**
 * Navigation Functions
 */
//----------------------------------------------------------------

function openNavigationMode() {
    console.log('[User] Opening navigation mode');
    
    const tilesGrid = document.getElementById('tiles-grid');
    const navContainer = document.getElementById('nav-container');
    
    if (tilesGrid && navContainer) {
        tilesGrid.style.display = 'none';
        navContainer.style.display = 'flex';
        isNavigationMode = true;
        
        // Initialize map if not already done
        if (!map) {
            initializeMap();
        }
    }
}

function closeNavigationMode() {
    console.log('[User] Closing navigation mode');
    
    const tilesGrid = document.getElementById('tiles-grid');
    const navContainer = document.getElementById('nav-container');
    
    if (tilesGrid && navContainer) {
        navContainer.style.display = 'none';
        tilesGrid.style.display = 'grid';
        isNavigationMode = false;
    }
}

function initializeMap() {
    console.log('[User] Initializing map');
    
    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.error('[User] Map container not found');
        return;
    }
    
    try {
        // Initialize Leaflet map
        map = L.map('map').setView([41.9028, 12.4964], 6); // Rome, Italy as default
        
        // Add OpenStreetMap tile layer (fallback for offline)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(map);
        
        console.log('[User] Map initialized successfully');
        
        // Add a placeholder message about offline tiles
        const placeholder = L.control({position: 'topright'});
        placeholder.onAdd = function() {
            const div = L.DomUtil.create('div', 'leaflet-control-offline-info');
            div.innerHTML = '<div style="background: rgba(0,0,0,0.8); color: #fff; padding: 5px; border-radius: 3px; font-size: 12px;">Online tiles (offline tiles not configured)</div>';
            return div;
        };
        placeholder.addTo(map);
        
    } catch (error) {
        console.error('[User] Failed to initialize map:', error);
        
        // Show placeholder for map error
        mapContainer.innerHTML = `
            <div class="map-placeholder">
                <div class="map-placeholder-icon">🗺️</div>
                <div>Map not available<br>Check Leaflet configuration</div>
            </div>
        `;
    }
}

function renderRoute(routeData) {
    console.log('[User] Rendering route:', routeData);
    
    if (!map) {
        console.error('[User] Map not initialized');
        return;
    }
    
    try {
        // Clear existing route
        if (routeLayer) {
            map.removeLayer(routeLayer);
        }
        
        // Add route to map
        if (routeData.route && routeData.route.features) {
            routeLayer = L.geoJSON(routeData.route, {
                style: {
                    color: '#ff0000',
                    weight: 4,
                    opacity: 0.8
                }
            }).addTo(map);
            
            // Fit map bounds to route
            map.fitBounds(routeLayer.getBounds(), { padding: [20, 20] });
        }
        
        // Display warnings
        displayWarnings(routeData.warnings || []);
        
        console.log('[User] Route rendered successfully');
        
    } catch (error) {
        console.error('[User] Failed to render route:', error);
    }
}

function displayWarnings(warnings) {
    const warningsContainer = document.getElementById('nav-warnings');
    if (!warningsContainer) {
        return;
    }
    
    if (warnings.length === 0) {
        warningsContainer.innerHTML = '<div style="color: #00ff66; text-align: center; padding: 10px;">Nessun avviso per questo percorso</div>';
        return;
    }
    
    let warningsHtml = '';
    warnings.forEach((warning, index) => {
        const severityClass = `warning-${warning.severity || 'info'}`;
        warningsHtml += `
            <div class="warning-item ${severityClass}">
                <strong>${warning.type || 'Avviso'}:</strong> ${warning.message}
            </div>
        `;
    });
    
    warningsContainer.innerHTML = warningsHtml;
}

// Add navigation close button event listener
document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.getElementById('nav-close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeNavigationMode);
    }
});
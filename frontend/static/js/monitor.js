/*
----------------------------------------------------------------------------------------------------
### JavaScript per Monitor Emozioni - Real-time Emotion Detection ###
Gestisce video streaming, canvas overlay e comunicazione con backend per analisi emozioni.
----------------------------------------------------------------------------------------------------
*/

//----------------------------------------------------------------
// VARIABILI GLOBALI E CONFIGURAZIONE
//----------------------------------------------------------------
let mediaStream = null;
let analysisInterval = null;
let isAnalysisActive = false;
let currentDriverId = null;

// Riferimenti DOM
const videoElement = document.getElementById('videoElement');
const overlayCanvas = document.getElementById('overlayCanvas');
const overlayContext = overlayCanvas.getContext('2d');
const startBtn = document.getElementById('startMonitoringBtn');
const stopBtn = document.getElementById('stopMonitoringBtn');
const analysisRateSelect = document.getElementById('analysisRate');

// Status elements
const cameraStatusValue = document.getElementById('cameraStatusValue');
const detectionStatusValue = document.getElementById('detectionStatusValue');
const currentEmotion = document.getElementById('currentEmotion');
const currentConfidence = document.getElementById('currentConfidence');
const connectionStatus = document.getElementById('connectionStatus');

// Configurazione
const CONFIG = {
    DEFAULT_FPS: 1,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    CANVAS_STROKE_WIDTH: 3,
    CANVAS_FONT_SIZE: 16,
    EMOTION_COLORS: {
        happy: '#00ff66',
        angry: '#ff0000',
        sad: '#4da6ff',
        surprise: '#ffbf00',
        fear: '#ff4d4d',
        disgust: '#ff8000',
        neutral: '#ffffff'
    }
};

//----------------------------------------------------------------
// INIZIALIZZAZIONE
//----------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    initializeMonitor();
    setupEventListeners();
});

function initializeMonitor() {
    // Estrai driver ID dall'URL
    const urlParts = window.location.pathname.split('/');
    const monitorIndex = urlParts.indexOf('monitor');
    if (monitorIndex !== -1 && monitorIndex + 1 < urlParts.length) {
        currentDriverId = urlParts[monitorIndex + 1];
        console.log(`[Monitor] Initialized for driver: ${currentDriverId}`);
    } else {
        console.error('[Monitor] Could not extract driver ID from URL');
        updateDetectionStatus('Errore configurazione', 'error');
        return;
    }
    
    updateDetectionStatus('Sistema pronto', 'ready');
    console.log('[Monitor] System initialized');
}

function setupEventListeners() {
    startBtn.addEventListener('click', startMonitoring);
    stopBtn.addEventListener('click', stopMonitoring);
    analysisRateSelect.addEventListener('change', updateAnalysisRate);
    
    // Ridimensiona canvas quando video cambia dimensioni
    videoElement.addEventListener('loadedmetadata', resizeCanvas);
    window.addEventListener('resize', resizeCanvas);
}

//----------------------------------------------------------------
// GESTIONE CAMERA E VIDEO STREAMING
//----------------------------------------------------------------
async function initializeCamera() {
    try {
        updateCameraStatus('Richiesta accesso...', 'pending');
        
        // Richiedi accesso alla webcam
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                frameRate: { ideal: 30 }
            },
            audio: false
        });
        
        // Configura il video element
        videoElement.srcObject = mediaStream;
        
        // Aspetta che il video sia pronto
        await new Promise((resolve) => {
            videoElement.addEventListener('loadeddata', resolve, { once: true });
        });
        
        updateCameraStatus('Connessa', 'connected');
        resizeCanvas();
        
        console.log('[Monitor] Camera initialized successfully');
        return true;
        
    } catch (error) {
        console.error('[Monitor] Error initializing camera:', error);
        updateCameraStatus('Errore accesso', 'error');
        
        // Mostra messaggio di errore più specifico
        if (error.name === 'NotAllowedError') {
            alert('Accesso alla camera negato. Concedi i permessi per utilizzare il monitoraggio emozioni.');
        } else if (error.name === 'NotFoundError') {
            alert('Nessuna camera trovata sul dispositivo.');
        } else {
            alert('Errore nell\'accesso alla camera: ' + error.message);
        }
        
        return false;
    }
}

function stopCamera() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
        videoElement.srcObject = null;
        updateCameraStatus('Disconnessa', 'disconnected');
        console.log('[Monitor] Camera stopped');
    }
}

function resizeCanvas() {
    if (videoElement.videoWidth && videoElement.videoHeight) {
        overlayCanvas.width = videoElement.videoWidth;
        overlayCanvas.height = videoElement.videoHeight;
        
        // Aggiorna le dimensioni CSS per mantenere l'aspect ratio
        const videoRect = videoElement.getBoundingClientRect();
        overlayCanvas.style.width = videoRect.width + 'px';
        overlayCanvas.style.height = videoRect.height + 'px';
        
        console.log(`[Monitor] Canvas resized to ${overlayCanvas.width}x${overlayCanvas.height}`);
    }
}

//----------------------------------------------------------------
// GESTIONE ANALISI EMOZIONI
//----------------------------------------------------------------
async function startMonitoring() {
    try {
        updateDetectionStatus('Inizializzazione...', 'pending');
        
        // Inizializza la camera
        const cameraReady = await initializeCamera();
        if (!cameraReady) {
            updateDetectionStatus('Errore camera', 'error');
            return;
        }
        
        // Avvia l'analisi
        startAnalysis();
        
        // Aggiorna UI
        startBtn.disabled = true;
        stopBtn.disabled = false;
        analysisRateSelect.disabled = true;
        
        updateDetectionStatus('Attivo', 'active');
        console.log('[Monitor] Monitoring started');
        
    } catch (error) {
        console.error('[Monitor] Error starting monitoring:', error);
        updateDetectionStatus('Errore avvio', 'error');
    }
}

function stopMonitoring() {
    // Ferma l'analisi
    stopAnalysis();
    
    // Ferma la camera
    stopCamera();
    
    // Pulisci overlay
    clearOverlay();
    
    // Reset UI
    startBtn.disabled = false;
    stopBtn.disabled = true;
    analysisRateSelect.disabled = false;
    
    updateDetectionStatus('Fermo', 'ready');
    updateCurrentEmotion('-', null);
    
    console.log('[Monitor] Monitoring stopped');
}

function startAnalysis() {
    if (isAnalysisActive) return;
    
    isAnalysisActive = true;
    const fps = parseFloat(analysisRateSelect.value);
    const intervalMs = 1000 / fps;
    
    analysisInterval = setInterval(captureAndAnalyzeFrame, intervalMs);
    console.log(`[Monitor] Analysis started at ${fps} FPS`);
}

function stopAnalysis() {
    if (analysisInterval) {
        clearInterval(analysisInterval);
        analysisInterval = null;
    }
    isAnalysisActive = false;
    console.log('[Monitor] Analysis stopped');
}

function updateAnalysisRate() {
    if (isAnalysisActive) {
        stopAnalysis();
        startAnalysis();
        console.log(`[Monitor] Analysis rate updated to ${analysisRateSelect.value} FPS`);
    }
}

//----------------------------------------------------------------
// CATTURA E ANALISI FRAME
//----------------------------------------------------------------
async function captureAndAnalyzeFrame() {
    try {
        // Cattura frame dal video
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        context.drawImage(videoElement, 0, 0);
        
        // Converte in base64
        const frameData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Invia al backend per analisi
        const result = await analyzeFrame(frameData);
        
        if (result.success) {
            updateOverlay(result);
            updateCurrentEmotion(result.emotion, result.confidence);
        } else {
            console.warn('[Monitor] Analysis failed:', result.error);
            updateDetectionStatus('Errore analisi', 'error');
        }
        
    } catch (error) {
        console.error('[Monitor] Error in frame analysis:', error);
        updateDetectionStatus('Errore cattura', 'error');
    }
}

async function analyzeFrame(frameData) {
    try {
        const response = await fetch(`/api/drivers/${currentDriverId}/monitor/frame`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                frame: frameData
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('[Monitor] Error calling analysis API:', error);
        return { success: false, error: error.message };
    }
}

//----------------------------------------------------------------
// GESTIONE CANVAS OVERLAY
//----------------------------------------------------------------
function updateOverlay(analysisResult) {
    clearOverlay();
    
    if (!analysisResult.bbox) {
        // Nessun volto rilevato
        return;
    }
    
    const bbox = analysisResult.bbox;
    const emotion = analysisResult.emotion;
    const confidence = analysisResult.confidence;
    
    // Calcola il fattore di scala tra video reale e canvas
    const scaleX = overlayCanvas.width / videoElement.videoWidth;
    const scaleY = overlayCanvas.height / videoElement.videoHeight;
    
    // Coordinate scalate
    const x = bbox.x * scaleX;
    const y = bbox.y * scaleY;
    const w = bbox.w * scaleX;
    const h = bbox.h * scaleY;
    
    // Disegna il riquadro del volto
    overlayContext.strokeStyle = CONFIG.EMOTION_COLORS[emotion] || CONFIG.EMOTION_COLORS.neutral;
    overlayContext.lineWidth = CONFIG.CANVAS_STROKE_WIDTH;
    overlayContext.strokeRect(x, y, w, h);
    
    // Disegna l'etichetta emozione
    if (emotion && confidence !== null) {
        const label = `${emotion.toUpperCase()} (${Math.round(confidence * 100)}%)`;
        
        overlayContext.fillStyle = CONFIG.EMOTION_COLORS[emotion] || CONFIG.EMOTION_COLORS.neutral;
        overlayContext.font = `${CONFIG.CANVAS_FONT_SIZE}px ${getComputedStyle(document.body).fontFamily}`;
        
        // Background per il testo
        const textMetrics = overlayContext.measureText(label);
        const textWidth = textMetrics.width;
        const textHeight = CONFIG.CANVAS_FONT_SIZE;
        
        overlayContext.fillStyle = 'rgba(0, 0, 0, 0.7)';
        overlayContext.fillRect(x, y - textHeight - 8, textWidth + 16, textHeight + 8);
        
        // Testo
        overlayContext.fillStyle = CONFIG.EMOTION_COLORS[emotion] || CONFIG.EMOTION_COLORS.neutral;
        overlayContext.fillText(label, x + 8, y - 8);
    }
}

function clearOverlay() {
    overlayContext.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

//----------------------------------------------------------------
// AGGIORNAMENTO UI STATUS
//----------------------------------------------------------------
function updateCameraStatus(status, type) {
    cameraStatusValue.textContent = status;
    cameraStatusValue.className = `status-value ${type}`;
}

function updateDetectionStatus(status, type) {
    detectionStatusValue.textContent = status;
    detectionStatusValue.className = `status-value ${type}`;
}

function updateCurrentEmotion(emotion, confidence) {
    if (emotion && emotion !== '-') {
        currentEmotion.textContent = emotion.toUpperCase();
        currentEmotion.className = `emotion-value ${emotion}`;
        
        if (confidence !== null) {
            currentConfidence.textContent = `(${Math.round(confidence * 100)}%)`;
        } else {
            currentConfidence.textContent = '';
        }
    } else {
        currentEmotion.textContent = '-';
        currentEmotion.className = 'emotion-value';
        currentConfidence.textContent = '';
    }
}

//----------------------------------------------------------------
// GESTIONE ERRORI E CLEANUP
//----------------------------------------------------------------
window.addEventListener('beforeunload', function() {
    if (isAnalysisActive) {
        stopMonitoring();
    }
});

// Gestione errori video
videoElement.addEventListener('error', function(e) {
    console.error('[Monitor] Video error:', e);
    updateCameraStatus('Errore video', 'error');
    updateDetectionStatus('Errore video', 'error');
});

// Log per debug
console.log('[Monitor] JavaScript initialized');
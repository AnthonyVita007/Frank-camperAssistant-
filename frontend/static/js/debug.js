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
// TOOL FLOW STATE MACHINE
//----------------------------------------------------------------
let currentToolName = null;
let toolFlowState = 'idle'; // idle → tool_detected → clarifying → ready_to_start → running → canceled → idle
let isClarificationActive = false;
let lastClarificationRequestId = null;

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
// helper: append tool lifecycle bubble with blue styling
//----------------------------------------------------------------
function appendToolBubble(message) {
    //----------------------------------------------------------------
    // CREAZIONE WRAPPER CHAT E BOLLA TOOL
    //----------------------------------------------------------------
    const wrapper = document.createElement('div');
    wrapper.className = 'chat';

    const bubble = document.createElement('div');
    bubble.className = 'bubble bubble-tool bubble-tool-enter bubble-tool-pulse-once';
    bubble.setAttribute('role', 'status');
    bubble.setAttribute('aria-live', 'polite');
    
    // Support for bold tool names in messages like "Tool selected → [ToolName]"
    if (message.includes('→')) {
        const parts = message.split('→');
        if (parts.length === 2) {
            const beforeArrow = parts[0].trim();
            const toolName = parts[1].trim();
            bubble.innerHTML = `${beforeArrow} → <strong>${toolName}</strong>`;
        } else {
            bubble.textContent = message;
        }
    } else {
        bubble.textContent = message;
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
// DELEGATION BUBBLE HELPER (RED BUBBLES)
//----------------------------------------------------------------
function appendDelegationBubble(message, delegationType) {
    //----------------------------------------------------------------
    // CREAZIONE WRAPPER CHAT E BOLLA DELEGATION
    //----------------------------------------------------------------
    const wrapper = document.createElement('div');
    wrapper.className = 'chat';

    const bubble = document.createElement('div');
    bubble.className = 'bubble bubble-delegation bubble-delegation-enter bubble-delegation-pulse-once';
    bubble.setAttribute('role', 'status');
    bubble.setAttribute('aria-live', 'polite');
    
    // Add specific class for delegation type
    if (delegationType === 'main-to-agent') {
        bubble.classList.add('bubble-delegation-main-to-agent');
    } else if (delegationType === 'agent-to-main') {
        bubble.classList.add('bubble-delegation-agent-to-main');
    }
    
    // Support for bold system names in messages like "[LLM principale] → passa i comandi a → [ToolLifecycleAgent]"
    if (message.includes('→')) {
        const parts = message.split('→');
        if (parts.length === 3) {
            const fromSystem = parts[0].trim();
            const toSystem = parts[2].trim();
            const middlePart = parts[1].trim();
            bubble.innerHTML = `<strong>${fromSystem}</strong> → ${middlePart} → <strong>${toSystem}</strong>`;
        } else if (parts.length === 2) {
            const beforeArrow = parts[0].trim();
            const afterArrow = parts[1].trim();
            bubble.innerHTML = `<strong>${beforeArrow}</strong> → <strong>${afterArrow}</strong>`;
        } else {
            bubble.textContent = message;
        }
    } else {
        bubble.textContent = message;
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
// helper: detect cancellation phrases
//----------------------------------------------------------------
function isCancelMessage(text) {
    const t = (text || '').toLowerCase().trim();
    const keywords = ['annulla', 'stop', 'cancella', 'ferma', 'lascia perdere', 'non più', 'interrompi', 'cancel', 'abort'];
    return keywords.some(k => t === k || t.includes(k));
}

//----------------------------------------------------------------
// helper: invio comando
//----------------------------------------------------------------
function sendCommand() {
    const text = (inputEl.value || '').trim();
    if (!text) return;

    appendLog(text, 'user');

    // Check for cancellation during tool flow
    if (['tool_detected', 'clarifying', 'ready_to_start', 'running'].includes(toolFlowState) && isCancelMessage(text)) {
        appendToolBubble('Closing Tool');
        
        // Emit cancellation events
        socket.emit('frontend_action', { action: 'cancel_tool', data: { tool_name: currentToolName }});
        socket.emit('frontend_command', { data: 'annulla operazione' }); // fallback
        
        // Reset state
        toolFlowState = 'canceled';
        currentToolName = null;
        isClarificationActive = false;
        
        // Reset to idle after brief delay
        setTimeout(() => { 
            toolFlowState = 'idle'; 
        }, 100);
        
        inputEl.value = '';
        inputEl.focus();
        return;
    }

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

    // Optional heuristics for tool detection when backend doesn't emit explicit events
    if (toolFlowState === 'idle' || toolFlowState === 'tool_detected') {
        // Heuristic: detect tool selection
        if (/(tool|strumento|funzione).*selezionat[oa]|usando.*tool|avvi[ao].*tool/i.test(msg)) {
            // Try to extract tool name from message
            const toolMatch = msg.match(/(navigation|weather|maintenance|vehicle|network|settings)[\._]?[\w]*/i);
            if (toolMatch && toolFlowState === 'idle') {
                const toolName = toolMatch[0];
                currentToolName = toolName;
                toolFlowState = 'tool_detected';
                appendToolBubble(`Tool selected → ${toolName}`);
            }
        }
    }

    // Heuristic: detect clarification questions
    if ((toolFlowState === 'tool_detected' || toolFlowState === 'clarifying') && isAI) {
        if (/[?]\s*$/.test(msg) && /(parametr|mancant|specifica|chiariment|destinazione|indica|fornisci)/i.test(msg)) {
            toolFlowState = 'clarifying';
            isClarificationActive = true;
        }
    }

    // Heuristic: detect readiness to start
    if (toolFlowState === 'clarifying' && isAI) {
        if (/(tutti i parametri|posso procedere|procedo|parametri completi|avvio|inizio)/i.test(msg)) {
            toolFlowState = 'ready_to_start';
            appendToolBubble('Starting Tool');
        }
    }
});

socket.on('backend_action', (payload) => {
    const action = payload && payload.action;
    const data = payload && payload.data || {};

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

    // DELEGATION EVENTS (RED BUBBLES)
    if (action === 'delegation_main_to_agent') {
        const fromSystem = data.from || 'LLM principale';
        const toSystem = data.to || 'ToolLifecycleAgent';
        const sessionId = data.session_id || 'unknown';
        
        appendDelegationBubble(`${fromSystem} → passa i comandi a → ${toSystem}`, 'main-to-agent');
        return;
    }

    if (action === 'delegation_agent_to_main') {
        const fromSystem = data.from || 'ToolLifecycleAgent';
        const toSystem = data.to || 'LLM principale';
        const sessionId = data.session_id || 'unknown';
        
        appendDelegationBubble(`${fromSystem} → passa i comandi a → ${toSystem}`, 'agent-to-main');
        return;
    }

    // TOOL LIFECYCLE EVENTS WITH COMPREHENSIVE TRACKING
    if (action === 'tool_lifecycle_started') {
        const toolName = data.tool_name || 'unknown';
        const state = data.state || 'unknown';
        const sessionId = data.session_id || 'unknown';
        currentToolName = toolName;
        toolFlowState = state;
        appendToolBubble(`🔧 Tool Lifecycle Started: ${toolName} | State: ${state} | Session: ${sessionId}`);
        return;
    }

    if (action === 'tool_selected') {
        const toolName = data.tool_name || 'unknown';
        currentToolName = toolName;
        toolFlowState = 'tool_detected';
        appendToolBubble(`🧭 Tool selected → ${toolName}`);
        return;
    }

    if (action === 'tool_clarification') {
        isClarificationActive = true;
        toolFlowState = 'clarifying';
        const missingParams = data.missing_required || [];
        appendToolBubble(`❓ Tool clarification needed | Missing: ${missingParams.join(', ')}`);
        return;
    }

    if (action === 'tool_parameter_received') {
        const paramName = data.param_name || 'unknown';
        const paramValue = data.param_value || 'unknown';
        const stillMissing = data.missing_required || [];
        appendToolBubble(`✅ Parameter received: ${paramName} = "${paramValue}" | Still missing: ${stillMissing.join(', ')}`);
        return;
    }

    if (action === 'tool_gating_notice') {
        const toolName = data.tool_name || 'unknown';
        const state = data.state || 'unknown';
        const missing = data.missing_required || [];
        appendToolBubble(`🚫 Tool gating active: ${toolName} | State: ${state} | Accepts only: ${missing.join(', ')}`);
        return;
    }

    if (action === 'tool_ready_to_start') {
        toolFlowState = 'ready_to_start';
        const toolName = data.tool_name || currentToolName || 'unknown';
        appendToolBubble(`⏳ Tool ready to start: ${toolName}`);
        return;
    }

    if (action === 'tool_started') {
        toolFlowState = 'running';
        const toolName = data.tool_name || currentToolName || 'unknown';
        const params = data.parameters ? JSON.stringify(data.parameters) : 'none';
        appendToolBubble(`▶️ Tool started: ${toolName} | Parameters: ${params}`);
        return;
    }

    if (action === 'tool_finished') {
        const toolName = data.tool_name || currentToolName || 'unknown';
        const status = data.status || 'unknown';
        const statusIcon = status === 'success' ? '✅' : status === 'error' ? '❌' : '🏁';
        appendToolBubble(`🏁 Tool finished: ${toolName} | Status: ${status} ${statusIcon}`);
        toolFlowState = 'idle';
        currentToolName = null;
        isClarificationActive = false;
        return;
    }

    if (action === 'tool_session_canceled') {
        const toolName = data.tool_name || currentToolName || 'unknown';
        const reason = data.reason || 'unknown';
        appendToolBubble(`🛑 Tool session canceled: ${toolName} | Reason: ${reason}`);
        toolFlowState = 'canceled';
        currentToolName = null;
        isClarificationActive = false;
        setTimeout(() => { 
            toolFlowState = 'idle'; 
        }, 100);
        return;
    }

    if (action === 'tool_lifecycle_finished') {
        const toolName = data.tool_name || currentToolName || 'unknown';
        const finalState = data.final_state || 'unknown';
        const status = data.status || 'unknown';
        appendToolBubble(`🔚 Tool lifecycle finished: ${toolName} | Final state: ${finalState} | Status: ${status}`);
        toolFlowState = 'idle';
        currentToolName = null;
        isClarificationActive = false;
        return;
    }

    // Legacy tool events (kept for backward compatibility)
    if (action === 'tool_canceled') {
        appendToolBubble('🛑 Tool canceled (legacy event)');
        toolFlowState = 'canceled';
        currentToolName = null;
        isClarificationActive = false;
        setTimeout(() => { 
            toolFlowState = 'idle'; 
        }, 100);
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
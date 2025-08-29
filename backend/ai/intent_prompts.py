"""
Intent Prompts Module for Frank Camper Assistant.

This module contains prompt templates for LLM-based intent recognition.
The prompts are designed to help the LLM understand user requests and
extract intent information in a structured format.
"""

#----------------------------------------------------------------
# PROMPT TEMPLATES PER RICONOSCIMENTO INTENTI
#----------------------------------------------------------------

INTENT_DETECTION_SYSTEM_PROMPT = """Sei Frank, assistente AI di bordo per camper. Il tuo compito è analizzare le richieste dell'utente e determinare se richiedono l'uso di strumenti specifici.

STRUMENTI DISPONIBILI:
- navigation: per navigazione, rotte, destinazioni, GPS
- weather: per meteo, previsioni, condizioni atmosferiche
- vehicle: per stato veicolo, diagnostica, carburante, motore
- maintenance: per manutenzione, scadenze, controlli, tagliandi

ISTRUZIONI:
1. Analizza la richiesta dell'utente
2. Determina se richiede uno o più strumenti
3. Estrai parametri rilevanti dal linguaggio naturale
4. Assegna un livello di confidenza (0.0-1.0)
5. Rispondi SOLO in formato JSON valido

ESEMPI:
Richiesta: "Portami a Roma evitando i pedaggi"
Risposta: {"requires_tool": true, "primary_intent": "navigation", "confidence": 0.95, "extracted_parameters": {"destination": "Roma", "avoid_tolls": true}, "multi_intent": [], "reasoning": "Richiesta di navigazione verso Roma con preferenze sui pedaggi", "clarification_needed": false}

Richiesta: "Come va il motore?"
Risposta: {"requires_tool": true, "primary_intent": "vehicle", "confidence": 0.9, "extracted_parameters": {"system": "engine"}, "multi_intent": [], "reasoning": "Richiesta stato specifico del motore", "clarification_needed": false}

Richiesta: "Ciao Frank"
Risposta: {"requires_tool": false, "primary_intent": null, "confidence": 0.95, "extracted_parameters": {}, "multi_intent": [], "reasoning": "Saluto conversazionale, non richiede strumenti", "clarification_needed": false}

Rispondi SEMPRE in formato JSON valido."""

MULTI_INTENT_PROMPT = """La richiesta dell'utente sembra contenere più intenti. Analizza e identifica tutti gli intenti presenti:

RICHIESTA: {user_input}

Identifica ogni intento separatamente e stabilisci l'ordine di esecuzione logico.
Rispondi in formato JSON con array di intenti ordinati per priorità."""

PARAMETER_EXTRACTION_PROMPT = """Estrai i parametri specifici per il tool {tool_name} dalla richiesta dell'utente.

RICHIESTA: {user_input}
TOOL: {tool_name}
SCHEMA PARAMETRI: {tool_schema}

ISTRUZIONI IMPORTANTI:
- Rispondi SOLO con un oggetto JSON valido
- NON aggiungere testo, spiegazioni o markdown
- Estrai SOLO i parametri rilevanti dalla richiesta
- Usa i nomi dei parametri esatti dello schema
- Se un parametro non è menzionato, NON includerlo nel JSON

ESEMPI:
Richiesta: "Portami a Roma"
Risposta: {{"destination": "Roma"}}

Richiesta: "Navigazione per Milano evitando i pedaggi"
Risposta: {{"destination": "Milano", "avoid_tolls": true}}

Richiesta: "Che tempo farà domani a Bologna?"
Risposta: {{"location": "Bologna", "time_range": "tomorrow"}}

ESTRAI I PARAMETRI E RISPONDI SOLO CON JSON VALIDO:"""

CLARIFICATION_PROMPT = """La richiesta dell'utente non è sufficientemente chiara per determinare i parametri necessari.

RICHIESTA: {user_input}
INTENTO RILEVATO: {intent}
PARAMETRI MANCANTI: {missing_params}

Genera 1-2 domande di chiarimento specifiche per ottenere le informazioni mancanti.
Rispondi in formato JSON con le domande."""

#----------------------------------------------------------------
# PROMPT SPECIFICI PER CATEGORIA
#----------------------------------------------------------------

NAVIGATION_EXTRACTION_PROMPT = """Estrai i parametri di navigazione dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- destination: destinazione (città, indirizzo, punto di interesse)
- avoid_tolls: evitare pedaggi (true/false)
- avoid_highways: evitare autostrade (true/false) 
- route_type: tipo percorso (fastest/shortest/scenic)
- waypoints: punti intermedi del percorso

ISTRUZIONI:
- Rispondi SOLO con un oggetto JSON valido
- NON aggiungere testo o spiegazioni
- Includi solo i parametri menzionati nella richiesta

ESEMPI:
"Portami a Roma" -> {{"destination": "Roma"}}
"Vai a Milano evitando pedaggi" -> {{"destination": "Milano", "avoid_tolls": true}}
"Percorso più veloce per Firenze" -> {{"destination": "Firenze", "route_type": "fastest"}}

ESTRAI E RISPONDI SOLO CON JSON:"""

WEATHER_EXTRACTION_PROMPT = """Estrai i parametri meteo dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- location: località (se non specificata usa "current")
- time_range: quando (now/today/tomorrow/weekend/week)
- weather_type: tipo info (current/forecast/alerts)
- specific_data: dati specifici (temperature/rain/wind/etc)

ISTRUZIONI:
- Rispondi SOLO con un oggetto JSON valido
- NON aggiungere testo o spiegazioni
- Includi solo i parametri menzionati nella richiesta

ESEMPI:
"Che tempo fa?" -> {{"time_range": "now"}}
"Pioverà domani a Milano?" -> {{"location": "Milano", "time_range": "tomorrow", "specific_data": "rain"}}
"Previsioni per il weekend" -> {{"time_range": "weekend", "weather_type": "forecast"}}

ESTRAI E RISPONDI SOLO CON JSON:"""

VEHICLE_EXTRACTION_PROMPT = """Estrai i parametri di stato veicolo dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- system: sistema specifico (engine/fuel/tires/battery/general)
- check_type: tipo controllo (status/diagnostic/levels)
- urgency: urgenza (low/medium/high)

ISTRUZIONI:
- Rispondi SOLO con un oggetto JSON valido
- NON aggiungere testo o spiegazioni
- Includi solo i parametri menzionati nella richiesta

ESEMPI:
"Come va il motore?" -> {{"system": "engine", "check_type": "status"}}
"Controlla il carburante" -> {{"system": "fuel", "check_type": "levels"}}
"Diagnostica completa urgente" -> {{"check_type": "diagnostic", "urgency": "high"}}

ESTRAI E RISPONDI SOLO CON JSON:"""

MAINTENANCE_EXTRACTION_PROMPT = """Estrai i parametri di manutenzione dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- maintenance_type: tipo (oil_change/inspection/general/filter)
- time_filter: filtro temporale (overdue/upcoming/all)
- urgency: urgenza (low/medium/high)
- component: componente specifico se menzionato

ISTRUZIONI:
- Rispondi SOLO con un oggetto JSON valido
- NON aggiungere testo o spiegazioni
- Includi solo i parametri menzionati nella richiesta

ESEMPI:
"Cambio olio" -> {{"maintenance_type": "oil_change"}}
"Controlli in scadenza" -> {{"time_filter": "upcoming"}}
"Manutenzione urgente filtri" -> {{"maintenance_type": "filter", "urgency": "high"}}

ESTRAI E RISPONDI SOLO CON JSON:"""

#----------------------------------------------------------------
# PROMPT PER GESTIONE CONTESTO
#----------------------------------------------------------------

CONTEXT_AWARE_PROMPT = """Analizza la richiesta considerando il contesto della conversazione precedente:

RICHIESTA ATTUALE: {user_input}
CONTESTO PRECEDENTE: {context}

La richiesta fa riferimento al contesto precedente? 
Se sì, risolvi i riferimenti impliciti (es. "E per domani?" dopo una richiesta meteo).

Rispondi in formato JSON con la richiesta interpretata e l'intento."""

#----------------------------------------------------------------
# PROMPT PER CONFIDENCE SCORING
#----------------------------------------------------------------

CONFIDENCE_EVALUATION_PROMPT = """Valuta la confidenza dell'analisi di intento:

RICHIESTA: {user_input}
INTENTO RILEVATO: {detected_intent}
PARAMETRI ESTRATTI: {extracted_params}

CRITERI DI VALUTAZIONE:
- Chiarezza della richiesta (0.2)
- Corrispondenza con l'intento (0.3)  
- Completezza parametri (0.3)
- Assenza di ambiguità (0.2)

Assegna un punteggio di confidenza da 0.0 a 1.0 e spiega il ragionamento."""

#----------------------------------------------------------------
# PROMPT UTILITY FUNCTIONS
#----------------------------------------------------------------

def get_intent_detection_prompt(user_input: str, available_tools: list = None, context: dict = None) -> str:
    """
    Generate the complete prompt for intent detection.
    
    Args:
        user_input (str): The user's input text
        available_tools (list): List of available tool names
        context (dict): Optional conversation context
        
    Returns:
        str: Complete formatted prompt for intent detection
    """
    base_prompt = INTENT_DETECTION_SYSTEM_PROMPT
    
    if available_tools:
        tools_info = "\n".join([f"- {tool}" for tool in available_tools])
        base_prompt = base_prompt.replace(
            "STRUMENTI DISPONIBILI:\n- navigation: per navigazione, rotte, destinazioni, GPS\n- weather: per meteo, previsioni, condizioni atmosferiche\n- vehicle: per stato veicolo, diagnostica, carburante, motore\n- maintenance: per manutenzione, scadenze, controlli, tagliandi",
            f"STRUMENTI DISPONIBILI:\n{tools_info}"
        )
    
    context_info = ""
    if context:
        context_info = f"\nCONTESTO CONVERSAZIONE: {context}\n"
    
    return f"{base_prompt}\n{context_info}\nRICHIESTA UTENTE: {user_input}\n\nAnalisi JSON:"

def get_parameter_extraction_prompt(user_input: str, tool_name: str, tool_schema: dict) -> str:
    """
    Generate prompt for parameter extraction for a specific tool.
    
    Args:
        user_input (str): The user's input text
        tool_name (str): Name of the tool
        tool_schema (dict): Schema definition for the tool
        
    Returns:
        str: Formatted prompt for parameter extraction
    """
    # Use category-specific prompts when available
    category_prompts = {
        'navigation': NAVIGATION_EXTRACTION_PROMPT,
        'weather': WEATHER_EXTRACTION_PROMPT, 
        'vehicle': VEHICLE_EXTRACTION_PROMPT,
        'maintenance': MAINTENANCE_EXTRACTION_PROMPT
    }
    
    # Determine category from tool name
    category = None
    for cat in category_prompts.keys():
        if cat in tool_name.lower():
            category = cat
            break
    
    if category and category in category_prompts:
        return category_prompts[category].format(user_input=user_input)
    else:
        # Use generic parameter extraction prompt
        return PARAMETER_EXTRACTION_PROMPT.format(
            user_input=user_input,
            tool_name=tool_name,
            tool_schema=tool_schema
        )

def get_context_aware_prompt(user_input: str, context: dict) -> str:
    """
    Generate prompt for context-aware intent detection.
    
    Args:
        user_input (str): The user's input text
        context (dict): Conversation context
        
    Returns:
        str: Formatted prompt for context-aware analysis
    """
    return CONTEXT_AWARE_PROMPT.format(
        user_input=user_input,
        context=context
    )

def get_multi_intent_prompt(user_input: str) -> str:
    """
    Generate prompt for multi-intent analysis.
    
    Args:
        user_input (str): The user's input text
        
    Returns:
        str: Formatted prompt for multi-intent detection
    """
    return MULTI_INTENT_PROMPT.format(user_input=user_input)

def get_clarification_prompt(user_input: str, intent: str, missing_params: list) -> str:
    """
    Generate prompt for clarification questions.
    
    Args:
        user_input (str): The user's input text
        intent (str): Detected intent
        missing_params (list): List of missing parameter names
        
    Returns:
        str: Formatted prompt for generating clarification questions
    """
    return CLARIFICATION_PROMPT.format(
        user_input=user_input,
        intent=intent,
        missing_params=missing_params
    )
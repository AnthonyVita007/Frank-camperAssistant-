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

Estrai tutti i parametri rilevanti dal linguaggio naturale italiano.
Rispondi in formato JSON con i parametri estratti."""

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

Rispondi in formato JSON con i parametri estratti."""

WEATHER_EXTRACTION_PROMPT = """Estrai i parametri meteo dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- location: località (se non specificata usa "current")
- time_range: quando (now/today/tomorrow/weekend/week)
- weather_type: tipo info (current/forecast/alerts)
- specific_data: dati specifici (temperature/rain/wind/etc)

Rispondi in formato JSON con i parametri estratti."""

VEHICLE_EXTRACTION_PROMPT = """Estrai i parametri di stato veicolo dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- system: sistema specifico (engine/fuel/tires/battery/general)
- check_type: tipo controllo (status/diagnostic/levels)
- urgency: urgenza (low/medium/high)

Rispondi in formato JSON con i parametri estratti."""

MAINTENANCE_EXTRACTION_PROMPT = """Estrai i parametri di manutenzione dalla richiesta:

RICHIESTA: {user_input}

PARAMETRI DA ESTRARRE:
- maintenance_type: tipo (oil_change/inspection/general/filter)
- time_filter: filtro temporale (overdue/upcoming/all)
- urgency: urgenza (low/medium/high)
- component: componente specifico se menzionato

Rispondi in formato JSON con i parametri estratti."""

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

def get_cancellation_detection_prompt(user_input: str) -> str:
    """
    Generate prompt for detecting cancellation intents.
    
    Args:
        user_input (str): The user's input text
        
    Returns:
        str: Formatted prompt for cancellation detection
    """
    return CANCELLATION_DETECTION_PROMPT.format(user_input=user_input)

def get_iterative_parameter_collection_prompt(user_input: str, tool_name: str, tool_schema: dict, collected_params: dict, missing_params: list) -> str:
    """
    Generate prompt for iterative parameter collection with context.
    
    Args:
        user_input (str): The user's input text
        tool_name (str): Name of the tool
        tool_schema (dict): Tool parameter schema
        collected_params (dict): Parameters already collected
        missing_params (list): Parameters still needed
        
    Returns:
        str: Formatted prompt for iterative parameter collection
    """
    return ITERATIVE_PARAMETER_COLLECTION_PROMPT.format(
        user_input=user_input,
        tool_name=tool_name,
        tool_schema=tool_schema,
        collected_params=collected_params,
        missing_params=missing_params
    )

#----------------------------------------------------------------
# PROMPT TEMPLATES AVANZATI
#----------------------------------------------------------------

CANCELLATION_DETECTION_PROMPT = """Analizza se l'input dell'utente contiene un'intenzione di cancellazione.

INPUT UTENTE: {user_input}

FRASI DI CANCELLAZIONE RICONOSCIUTE:
- "annulla", "cancella", "stop", "basta"
- "lascia perdere", "non importa", "dimenticalo"
- "ferma", "interrompi", "abbandona"

Rispondi SOLO con un JSON:
{{"is_cancellation": true/false, "confidence": 0.0-1.0, "reasoning": "spiegazione"}}"""

ITERATIVE_PARAMETER_COLLECTION_PROMPT = """Estrai parametri per il tool {tool_name} considerando il contesto della raccolta in corso.

INPUT UTENTE: {user_input}
TOOL: {tool_name}
SCHEMA: {tool_schema}
PARAMETRI GIÀ RACCOLTI: {collected_params}
PARAMETRI MANCANTI: {missing_params}

ISTRUZIONI:
1. Estrai solo i parametri mancanti dall'input utente
2. Non sovrascrivere parametri già raccolti
3. Se l'input non contiene parametri utili, genera una domanda di chiarimento
4. Riconosci tentativi di cancellazione

Rispondi in formato JSON:
{{
  "extracted_parameters": {{}},
  "clarification_needed": true/false,
  "clarification_question": "domanda per l'utente",
  "is_cancellation": true/false,
  "collection_complete": true/false
}}"""

# Prompt specializzati per categorie di strumenti
NAVIGATION_PARAMETER_COLLECTION_PROMPT = """Estrai parametri di navigazione dall'input dell'utente.

INPUT: {user_input}

PARAMETRI NAVIGAZIONE:
- destination: destinazione (città, indirizzo, luogo)
- avoid_tolls: evitare pedaggi (true/false)
- avoid_highways: evitare autostrade (true/false)
- route_type: tipo percorso ("fastest", "shortest", "scenic")

Rispondi in JSON con i parametri trovati."""

WEATHER_PARAMETER_COLLECTION_PROMPT = """Estrai parametri meteo dall'input dell'utente.

INPUT: {user_input}

PARAMETRI METEO:
- location: posizione (città, "current" per posizione attuale)
- timeframe: periodo ("now", "today", "tomorrow", "weekend")
- weather_type: tipo info ("general", "rain", "temperature")

Rispondi in JSON con i parametri trovati."""

VEHICLE_PARAMETER_COLLECTION_PROMPT = """Estrai parametri veicolo dall'input dell'utente.

INPUT: {user_input}

PARAMETRI VEICOLO:
- system: sistema ("general", "engine", "fuel", "tires", "battery")
- check_type: tipo controllo ("status", "diagnostic", "alerts")

Rispondi in JSON con i parametri trovati."""
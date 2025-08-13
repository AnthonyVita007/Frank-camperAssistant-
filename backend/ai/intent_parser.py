"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/ai/intent_parser.py ###
Parser di intenti estremamente semplice basato su regole.
In futuro verrà sostituito/affiancato da un modello LLM locale (Ollama).
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORT ###
# --------------------------------------------------------------------------------------------------
#
import logging

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: FUNZIONI PRINCIPALI ###
# --------------------------------------------------------------------------------------------------
#
def parse_intent(text: str) -> dict:
    """
    Analizza il testo e restituisce un dizionario con:
    - name: nome dell'intento (es. 'network_status', 'greeting', 'vehicle_status', 'current_location', 'echo')
    - entities: entità estratte (per ora vuoto)
    - confidence: confidenza (stub)
    """
    if not text:
        return {"name": "unknown", "entities": {}, "confidence": 0.0}

    lower = text.strip().lower()

    # Intento: stato della rete
    if any(k in lower for k in ["rete", "online", "connessione", "internet"]):
        intent = {"name": "network_status", "entities": {}, "confidence": 0.6}

    # Intento: stato veicolo (OBD)
    elif any(k in lower for k in [
        "stato veicolo", "stato del veicolo", "obd", "motore", "giri", "rpm", "velocità", "temperatura motore"
    ]):
        intent = {"name": "vehicle_status", "entities": {}, "confidence": 0.6}

    # Intento: posizione corrente (GPS)
    elif any(k in lower for k in [
        "posizione", "dove siamo", "coordinate", "gps", "latitudine", "longitudine"
    ]):
        intent = {"name": "current_location", "entities": {}, "confidence": 0.6}

    # Intento: saluto
    elif any(k in lower for k in ["ciao", "hello", "hey", "salve"]):
        intent = {"name": "greeting", "entities": {}, "confidence": 0.5}

    # Intento: echo (fallback)
    else:
        intent = {"name": "echo", "entities": {"text": text}, "confidence": 0.4}

    logging.debug(f"[IntentParser] Intent rilevato: {intent}")
    return intent
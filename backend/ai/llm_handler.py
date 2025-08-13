"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/ai/llm_handler.py ###
Stub del generatore di risposte. In futuro orchestrerà LLM locale (Ollama)
e, se online, API cloud. Ora produce risposte deterministiche semplici.
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
def generate_response(intent: dict, context: dict | None = None) -> str:
    """
    Genera una risposta testuale in base all'intento e al contesto.
    context può contenere:
      - online: bool (stato della rete)
      - raw_command: str (comando originale)
    """
    name = (intent or {}).get("name", "unknown")
    online = (context or {}).get("online", None)
    raw = (context or {}).get("raw_command", "")

    if name == "network_status":
        if online is True:
            return "Sono online. La connessione di rete è disponibile."
        if online is False:
            return "Sono offline. Nessuna connessione di rete disponibile."
        return "Non riesco a determinare lo stato della rete in questo momento."

    if name == "greeting":
        return "Ciao! Come posso aiutarti oggi?"

    if name == "echo":
        return f"Hai detto: '{raw or intent.get('entities', {}).get('text', '')}'."

    return "Non ho capito la richiesta, ma sto imparando a riconoscere nuovi comandi."


#
# --------------------------------------------------------------------------------------------------
# ### FINE FILE ###
# --------------------------------------------------------------------------------------------------
#
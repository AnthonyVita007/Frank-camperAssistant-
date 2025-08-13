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
      - vehicle: dict (stato veicolo)
      - location: dict (posizione corrente)
    """
    name = (intent or {}).get("name", "unknown")
    online = (context or {}).get("online", None)
    raw = (context or {}).get("raw_command", "")

    #----------------------------------------------------------------
    # INTENT: STATO RETE
    #----------------------------------------------------------------
    if name == "network_status":
        if online is True:
            return "Sono online. La connessione di rete è disponibile."
        if online is False:
            return "Sono offline. Nessuna connessione di rete disponibile."
        return "Non riesco a determinare lo stato della rete in questo momento."

    #----------------------------------------------------------------
    # INTENT: STATO VEICOLO (OBD)
    #----------------------------------------------------------------
    if name == "vehicle_status":
        v = (context or {}).get("vehicle") or {}
        rpm = v.get("rpm")
        spd = v.get("speed_kmh")
        tmp = v.get("coolant_temp_c")
        if rpm is None and spd is None and tmp is None:
            return "Al momento non riesco a leggere i dati del veicolo."
        parts = []
        if rpm is not None:
            parts.append(f"giri motore {rpm} rpm")
        if spd is not None:
            parts.append(f"velocità {spd:.1f} km/h")
        if tmp is not None:
            parts.append(f"temperatura liquido {tmp:.0f} °C")
        return "Stato veicolo: " + ", ".join(parts) + "."

    #----------------------------------------------------------------
    # INTENT: POSIZIONE CORRENTE (GPS)
    #----------------------------------------------------------------
    if name == "current_location":
        loc = (context or {}).get("location") or {}
        lat = loc.get("lat")
        lon = loc.get("lon")
        if lat is None or lon is None:
            return "Non riesco a determinare la posizione in questo momento."
        # Formattazione semplice in gradi decimali
        ns = "N" if lat >= 0 else "S"
        ew = "E" if lon >= 0 else "W"
        return f"Posizione corrente: {abs(lat):.4f}° {ns}, {abs(lon):.4f}° {ew}."

    #----------------------------------------------------------------
    # INTENT: SALUTO
    #----------------------------------------------------------------
    if name == "greeting":
        return "Ciao! Come posso aiutarti oggi?"

    #----------------------------------------------------------------
    # INTENT: ECHO (FALLBACK)
    #----------------------------------------------------------------
    if name == "echo":
        return f"Hai detto: '{raw or intent.get('entities', {}).get('text', '')}'."

    #----------------------------------------------------------------
    # INTENT: SCONOSCIUTO
    #----------------------------------------------------------------
    return "Non ho capito la richiesta, ma sto imparando a riconoscere nuovi comandi."


#
# --------------------------------------------------------------------------------------------------
# ### FINE FILE ###
# --------------------------------------------------------------------------------------------------
#
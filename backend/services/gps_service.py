"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/services/gps_service.py ###
Servizio GPS (stub): fornisce la posizione corrente.
In futuro leggerà da un modulo GPS hardware.
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORT ###
# --------------------------------------------------------------------------------------------------
#
import logging
from datetime import datetime

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: FUNZIONI PRINCIPALI ###
# --------------------------------------------------------------------------------------------------
#
def get_current_location() -> dict:
    """
    Restituisce la posizione corrente (stub).
    Campi:
      - lat: float
      - lon: float
      - timestamp: ISO8601 string
    """
    #----------------------------------------------------------------
    # DATI STUB (da sostituire con letture reali GPS)
    #----------------------------------------------------------------
    location = {
        "lat": 45.4642,  # Milano (esempio)
        "lon": 9.1900,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }
    logging.debug(f"[GPSService] Posizione corrente: {location}")
    return location


#
# --------------------------------------------------------------------------------------------------
# ### FINE FILE ###
# --------------------------------------------------------------------------------------------------
#
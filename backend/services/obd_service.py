"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/services/obd_service.py ###
Servizio OBD-II (stub): fornisce dati di base del veicolo.
In futuro leggerà da adattatore OBD-II via Bluetooth.
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
def get_vehicle_status() -> dict:
    """
    Restituisce uno stato veicolo minimale (stub).
    Campi:
      - rpm: int
      - speed_kmh: float
      - coolant_temp_c: float
      - timestamp: ISO8601 string
    """
    #----------------------------------------------------------------
    # DATI STUB (da sostituire con letture reali OBD)
    #----------------------------------------------------------------
    status = {
        "rpm": 1800,               # giri/min
        "speed_kmh": 72.5,         # km/h
        "coolant_temp_c": 88.0,    # °C
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }
    logging.debug(f"[OBDService] Stato veicolo: {status}")
    return status


#
# --------------------------------------------------------------------------------------------------
# ### FINE FILE ###
# --------------------------------------------------------------------------------------------------
#
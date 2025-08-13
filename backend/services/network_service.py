"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/services/network_service.py ###
Servizio di rete: fornisce utilità per verificare lo stato della connessione.
Implementazione offline-first: usa un check leggero verso un endpoint noto.
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORT ###
# --------------------------------------------------------------------------------------------------
#
import logging
import socket

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: FUNZIONI PRINCIPALI ###
# --------------------------------------------------------------------------------------------------
#
def is_online(timeout: float = 1.5) -> bool:
    """
    Ritorna True se una connessione UDP verso un DNS pubblico va a buon fine entro il timeout.
    Non invia dati, tenta solo l'apertura di una socket.
    """
    try:
        # Prova con Cloudflare DNS (1.1.1.1:53)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(("1.1.1.1", 53))
        return True
    except Exception as e:
        logging.debug(f"[NetworkService] Offline (motivo: {e})")
        return False


def get_network_status() -> dict:
    """
    Restituisce uno stato di rete strutturato.
    """
    status = {"online": is_online()}
    logging.debug(f"[NetworkService] Stato rete: {status}")
    return status


#
# --------------------------------------------------------------------------------------------------
# ### FINE FILE ###
# --------------------------------------------------------------------------------------------------
#
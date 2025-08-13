"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/main_controller.py ###
Questo file è il "Direttore d'Orchestra" di Frank.
Riceve gli eventi dal server (app.py) e coordina le azioni dei vari servizi
(IA, hardware, database) per generare una risposta.
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORTAZIONI ###
# Importiamo le librerie necessarie, inclusi gli oggetti `socketio`.
# --------------------------------------------------------------------------------------------------
#

# Importazione del sistema di logging
import logging

# Importazione di SocketIO per poter definire i gestori di eventi
from flask_socketio import SocketIO, emit

# Import dei moduli AI/Services
from backend.ai.intent_parser import parse_intent
from backend.ai.llm_handler import generate_response
from backend.services.network_service import get_network_status

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: DEFINIZIONE DELLA FUNZIONE DI SETUP ###
# Questa è la funzione che viene chiamata da app.py per collegare gli eventi.
# --------------------------------------------------------------------------------------------------
#

def setup_socketio_events(socketio_instance: SocketIO):
    """
    Questa funzione riceve l'istanza di SocketIO creata in app.py
    e collega tutti i gestori di eventi a essa.
    Questo mantiene il nostro codice pulito e modulare.
    """
    # Usiamo l'istanza passata per registrare i nostri gestori di eventi
    # Questo è un modo avanzato ma molto pulito di strutturare applicazioni Flask.
    
    @socketio_instance.on('connect')
    def handle_connect():
        """
        Gestisce la connessione iniziale del client.
        """
        logging.info('Client connesso al controller principale!')
        # La risposta di benvenuto ora viene inviata da qui.
        emit('backend_response', {'data': 'Benvenuto! Controller di Frank attivo.'})

    @socketio_instance.on('frontend_command')
    def handle_frontend_command(json_data):
        """
        Gestisce i comandi ricevuti dal frontend.
        Pipeline minima:
        1) Parse intent
        2) Recupera stato rete
        3) Genera risposta (stub LLM)
        """
        command = (json_data or {}).get('data', '').strip()
        logging.info(f"[Controller] Comando ricevuto: '{command}'")

        # 1) Intent parsing
        intent = parse_intent(command)

        # 2) Stato rete
        net = get_network_status()

        # 3) Generazione risposta
        context = {"online": net.get("online"), "raw_command": command}
        reply = generate_response(intent, context)

        # 4) Emissione al frontend
        emit('backend_response', {'data': reply})


#
# --------------------------------------------------------------------------------------------------
# ### FINE DEL FILE main_controller.py ###
# --------------------------------------------------------------------------------------------------
#
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
from backend.services.obd_service import get_vehicle_status
from backend.services.gps_service import get_current_location

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
        #----------------------------------------------------------------
        # LOGICA DI CONNESSIONE
        #----------------------------------------------------------------
        #connessione
        logging.info('Client connesso al controller principale!')
        #...
        emit('backend_response', {'data': 'Benvenuto! Controller di Frank attivo.'})

    @socketio_instance.on('frontend_command')
    def handle_frontend_command(json_data):
        """
        Gestisce i comandi ricevuti dal frontend.
        Pipeline:
        1) Comandi speciali (/clear, navigazione pagine)
        2) Parse intent
        3) Recupera stato rete
        4) Arricchisce contesto (OBD/GPS se richiesto)
        5) Genera risposta (stub LLM)
        6) Emissione al frontend
        """
        #----------------------------------------------------------------
        # ESTRAZIONE COMANDO
        #----------------------------------------------------------------
        #connessione
        command = (json_data or {}).get('data', '').strip()
        #...
        logging.info(f"[Controller] Comando ricevuto: '{command}'")

        #----------------------------------------------------------------
        # COMANDI SPECIALI
        #----------------------------------------------------------------
        #connessione
        lower_cmd = command.lower()
        #...
        if lower_cmd.startswith('/clear'):
            #...
            emit('backend_action', {
                'action': 'clear_log',
                'data': 'Console pulita su richiesta.'
            })
            #...
            return

        # navigazione verso modalità DEBUG 
        #connessione
        if lower_cmd.startswith('/debugmode'):
            #...
            emit('backend_action', {
                'action': 'navigate',
                'data': '/debug'
            })
            #...
            return

        # navigazione verso modalità UTENTE
        #connessione
        if lower_cmd.startswith('/usermode'):
            #...
            emit('backend_action', {
                'action': 'navigate', 
                'data': '/user'
            })
            #...
            return

        #----------------------------------------------------------------
        # INTENT PARSING
        #----------------------------------------------------------------
        #connessione
        intent = parse_intent(command)
        #...
        intent_name = intent.get("name", "unknown")
        #...
        logging.debug(f"[Controller] Intent rilevato: {intent}")

        #----------------------------------------------------------------
        # STATO RETE
        #----------------------------------------------------------------
        #connessione
        net = get_network_status()

        #----------------------------------------------------------------
        # COSTRUZIONE CONTESTO DI RISPOSTA
        #----------------------------------------------------------------
        #connessione
        context = {"online": net.get("online"), "raw_command": command}
        #...
        try:
            # Se serve lo stato veicolo, leggilo dal servizio OBD (stub)
            #connessione
            if intent_name == "vehicle_status":
                #...
                vehicle = get_vehicle_status()
                #...
                context["vehicle"] = vehicle

            # Se serve la posizione, leggila dal servizio GPS (stub)
            #connessione
            if intent_name == "current_location":
                #...
                location = get_current_location()
                #...
                context["location"] = location

        except Exception as e:
            #----------------------------------------------------------------
            # GESTIONE ERRORI SERVIZI
            #----------------------------------------------------------------
            #connessione
            logging.error(f"[Controller] Errore durante la raccolta del contesto: {e}")
            #...
            # Non interrompiamo: il llm_handler gestirà campi mancanti
            #...

        #----------------------------------------------------------------
        # GENERAZIONE RISPOSTA
        #----------------------------------------------------------------
        #connessione
        reply = generate_response(intent, context)

        #----------------------------------------------------------------
        # EMISSIONE AL FRONTEND
        #----------------------------------------------------------------
        #connessione
        emit('backend_response', {'data': reply})


#
# --------------------------------------------------------------------------------------------------
# ### FINE DEL FILE main_controller.py ###
# --------------------------------------------------------------------------------------------------
#
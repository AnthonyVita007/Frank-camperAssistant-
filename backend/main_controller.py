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

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: DEFINIZIONE DELLA FUNZIONE DI SETUP ###
# Questa è la funzione che viene chiamata da app.py per collegare gli eventi.
# --------------------------------------------------------------------------------------------------
#

def setup_socketio_events(socketio_instance):
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
        Questa diventerà la funzione più importante.
        """
        command = json_data.get('data', 'Nessun dato')
        logging.info(f"Controller ha ricevuto il comando: '{command}'")

        #
        # !!! LOGICA FUTURA DEL DIRETTORE D'ORCHESTRA !!!
        # // 1. Passa il 'command' all'intent_parser per capire cosa fare.
        # // 2. Controlla lo stato della rete con network_service.
        # // 3. Chiama il servizio appropriato (db_service, obd_service, etc.).
        # // 4. Passa i risultati al llm_handler per generare una risposta.
        # // 5. Usa tts_service per convertire la risposta in audio (in futuro).
        # // 6. Invia la risposta testuale al frontend.
        #
        
        # Per ora, rispondiamo con una semplice conferma
        emit('backend_response', {'data': f"Controller ha elaborato: '{command}'"})


#
# --------------------------------------------------------------------------------------------------
# ### FINE DEL FILE main_controller.py ###
# --------------------------------------------------------------------------------------------------
#
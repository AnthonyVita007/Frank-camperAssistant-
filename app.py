"""
----------------------------------------------------------------------------------------------------
### CODICE PER app.py (Versione con routing separato user/debug) ###
Questo file funge da punto di avvio per l'intera applicazione Frank.
Il suo scopo è inizializzare il server, caricare la configurazione da config.ini,
e delegare la gestione degli eventi al controller principale.
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORTAZIONI E CONFIGURAZIONE ###
# Importiamo le librerie di base, carichiamo la configurazione e i nostri moduli custom.
# --------------------------------------------------------------------------------------------------
#

# Importazione delle librerie di sistema e Flask
import logging
import os
import configparser
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import base64
import cv2
import numpy as np

# Importazione del nostro controller principale
# // Da questo momento, tutta la logica degli eventi sarà gestita da un file separato.
from backend.main_controller import setup_socketio_events

# Importazione del sistema di rilevamento emozioni
from emotion_ai.ai.emotion_detector import analyze_frame, initialize_emotion_detector

# Configurazione del sistema di logging (livello regolabile in base al DEBUG)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#----------------------------------------------------------------
# CARICAMENTO CONFIGURAZIONE DA config.ini
#----------------------------------------------------------------
config = configparser.ConfigParser()
if os.path.exists('config.ini'):
    config.read('config.ini')
else:
    logging.warning("File config.ini non trovato: uso i valori di default.")

SECRET_KEY = config.get('flask', 'SECRET_KEY', fallback='dev-secret-insecure')
DEBUG = config.getboolean('flask', 'DEBUG', fallback=True)
HOST = config.get('flask', 'HOST', fallback='0.0.0.0')
PORT = config.getint('flask', 'PORT', fallback=5000)

# Adegua il livello di logging in base al DEBUG
if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug("Modalità DEBUG attiva.")
else:
    logging.getLogger().setLevel(logging.INFO)

# Inizializzazione dell'applicazione Flask
# // I percorsi per le cartelle 'templates' e 'static'.
app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')

# Impostazione di una chiave segreta per la sicurezza (presa da config.ini)
app.config['SECRET_KEY'] = SECRET_KEY

# Inizializzazione di SocketIO
socketio = SocketIO(app)

# Inizializzazione del sistema di rilevamento emozioni
logging.info("Inizializzazione sistema di rilevamento emozioni...")
emotion_detector_initialized = initialize_emotion_detector()
if emotion_detector_initialized:
    logging.info("Sistema di rilevamento emozioni inizializzato con successo")
else:
    logging.warning("Sistema di rilevamento emozioni non completamente disponibile")


#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: GESTIONE DELLE ROTTE HTTP ###
# Definiamo le rotte per servire le interfacce separate.
# --------------------------------------------------------------------------------------------------
#

# Rotta principale: reindirizza alla modalità utente
@app.route('/')
def index():
    """
    Rotta principale che reindirizza alla modalità utente.
    """
    logging.info("Client connesso. Reindirizzo alla modalità utente.")
    return render_template('user.html')

# Rotta modalità utente
@app.route('/user')
def user_mode():
    """
    Serve la pagina della modalità utente con tile.
    """
    logging.info("Client richiede modalità utente.")
    return render_template('user.html')

# Rotta modalità debug  
@app.route('/debug')
def debug_mode():
    """
    Serve la pagina della modalità debug con log testuale.
    """
    logging.info("Client richiede modalità debug.")
    return render_template('debug.html')

# Rotta modalità monitor
@app.route('/monitor/<driver_id>')
def monitor_mode(driver_id):
    """
    Serve la pagina di monitoraggio emozioni per un driver specifico.
    """
    logging.info(f"Client richiede modalità monitor per driver {driver_id}.")
    return render_template('monitor.html', driver_id=driver_id)

# API endpoint per analisi frame emozioni
@app.route('/api/drivers/<driver_id>/monitor/frame', methods=['POST'])
def analyze_emotion_frame(driver_id):
    """
    Analizza un frame video per rilevamento emozioni.
    """
    try:
        data = request.get_json()
        
        if not data or 'frame' not in data:
            return jsonify({'success': False, 'error': 'No frame data provided'}), 400
        
        # Decodifica il frame base64
        frame_data = data['frame']
        if frame_data.startswith('data:image'):
            frame_data = frame_data.split(',')[1]
        
        # Converte base64 in immagine
        img_bytes = base64.b64decode(frame_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'error': 'Invalid frame data'}), 400
        
        # Analizza il frame
        result = analyze_frame(frame)
        
        # Aggiungi metadata
        result['driver_id'] = driver_id
        result['timestamp'] = time.time()
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error analyzing emotion frame for driver {driver_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


#
# --------------------------------------------------------------------------------------------------
# ### PARTE 3: DELEGA DELLA LOGICA WEBSOCKET ###
# Invece di definire qui i gestori di eventi, li passiamo al nostro controller.
# --------------------------------------------------------------------------------------------------
#

# Inizializzazione degli eventi SocketIO definiti nel controller
# // Questa singola riga di codice collega tutti i gestori di eventi
# // (connect, frontend_command, etc.) che scriveremo in main_controller.py.
setup_socketio_events(socketio)


#
# --------------------------------------------------------------------------------------------------
# ### PARTE 4: BLOCCO DI AVVIO DEL SERVER ###
# Questo blocco avvia l'applicazione quando eseguiamo 'python app.py'.
# --------------------------------------------------------------------------------------------------
#

if __name__ == '__main__':

    logging.info(f"Avvio del server di Frank su http://{HOST}:{PORT} (DEBUG={DEBUG})")
    
    # Avvia il server, rendendolo accessibile sulla rete locale
    # allow_unsafe_werkzeug=True è comodo in sviluppo; in produzione usare un server WSGI/ASGI.
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=DEBUG,
        allow_unsafe_werkzeug=True if DEBUG else False
    )
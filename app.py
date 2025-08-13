"""
----------------------------------------------------------------------------------------------------
### CODICE PER app.py (Versione Strutturata con config.ini) ###
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
from flask import Flask, render_template
from flask_socketio import SocketIO

# Importazione del nostro controller principale
# // Da questo momento, tutta la logica degli eventi sarà gestita da un file separato.
from backend.main_controller import setup_socketio_events

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


#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: GESTIONE DELLA ROTTA HTTP ###
# Definiamo la rotta per servire l'interfaccia grafica.
# --------------------------------------------------------------------------------------------------
#

# Definizione della rotta principale
@app.route('/')
def index():
    """
    Serve la pagina principale index.html.
    """
    logging.info("Client connesso. Servo la pagina principale dell'interfaccia.")
    return render_template('index.html')


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
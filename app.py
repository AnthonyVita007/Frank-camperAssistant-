"""
----------------------------------------------------------------------------------------------------
### CODICE PER app.py (Versione Strutturata) ###
Questo file funge da punto di avvio per l'intera applicazione Frank.
Il suo unico scopo è inizializzare il server e delegare la gestione degli eventi
al controller principale.
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORTAZIONI E CONFIGURAZIONE ###
# Importiamo le librerie di base e i nostri moduli custom.
# --------------------------------------------------------------------------------------------------
#

# Importazione delle librerie di sistema e Flask
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO

# Importazione del nostro controller principale
# // Da questo momento, tutta la logica degli eventi sarà gestita da un file separato.
from backend.main_controller import setup_socketio_events

# Configurazione del sistema di logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inizializzazione dell'applicazione Flask
# // I percorsi per le cartelle 'templates' e 'static'.
app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')

# Impostazione di una chiave segreta per la sicurezza
app.config['SECRET_KEY'] = 'la-tua-chiave-segreta-super-sicura'

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

    logging.info("Avvio del server di Frank su http://0.0.0.0:5000")
    
    # Avvia il server, rendendolo accessibile sulla rete locale
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

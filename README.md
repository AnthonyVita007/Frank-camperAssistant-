---

# Progetto FRANK: Un Assistente di Bordo AI per Camper

[![Stato del Progetto](https://img.shields.io/badge/status-in%20sviluppo-orange)](https://github.com/tuo-username/frank-assistant)

> "Un assistente di bordo intelligente, offline-first e multimodale, con l'anima di KITT di Supercar. Progettato per essere il compagno di viaggio definitivo."

FRANK è un assistente AI all-in-one, costruito su un Raspberry Pi 5, che si integra nativamente nel cruscotto di un camper per fornire navigazione, monitoraggio del veicolo, gestione della manutenzione e molto altro, attraverso un'interfaccia vocale e touch dal design retrofuturistico.

<img width="1024" height="461" alt="FrankBanner" src="https://github.com/user-attachments/assets/aae6fdc3-11f1-4c7d-a852-6006396fdc31" />

[**CLICCA QUI PER LA DOCUMENTAZIONE COMPLETA**](https://lateral-saxophone-9f2.notion.site/Frank-camper-assistant-247521f00178803c900adc6934c3df84)

---

### Indice

1.  [Visione del Progetto](#1-visione-del-progetto)
2.  [Filosofia Architettonica](#2-filosofia-architettonica)
3.  [Blueprint del Sistema](#3-blueprint-del-sistema)
4.  [Stack Tecnologico](#4-stack-tecnologico)
5.  [Design Language: L'Estetica "KITT"](#5-design-language-lestetica-kitt)
6.  [Struttura del Codice](#6-struttura-del-codice)
7.  [Architettura MCP: come FRANK traduce richieste in azioni](#7-architettura-mcp-come-frank-traduce-richieste-in-azioni)
8.  [Sistema di Monitoraggio Emozioni](#8-sistema-di-monitoraggio-emozioni)
9.  [Configurazione e Deployment](#9-configurazione-e-deployment)

---
### 1. Visione del Progetto

L'obiettivo di FRANK è creare un assistente di bordo che sia parte integrante del veicolo, non un'applicazione accessoria. Fornisce al guidatore un controllo centralizzato e un accesso intuitivo alle informazioni critiche del viaggio e del camper, minimizzando le distrazioni e massimizzando l'efficienza.

---
### 2. Filosofia Architettonica

Il sistema è costruito su due concetti fondamentali per garantire affidabilità e usabilità in un ambiente mobile come un camper.

- Approccio Ibrido ("Offline-First"): Le funzioni critiche (navigazione, stato del veicolo, accesso ai log) sono gestite da un LLM locale e devono funzionare perfettamente senza connessione internet. Il sistema si "potenzia" quando online, utilizzando API cloud per dati in tempo reale (meteo, traffico) e per una qualità di interazione superiore.

- Interfaccia Multimodale (Voce + Touch): Voce e schermo lavorano in sinergia. La voce è il metodo di input primario per comandi rapidi, mentre il touchscreen offre un riscontro visivo dettagliato e un controllo tattile completo.

---
### 3. Blueprint del Sistema

Il flusso di dati e comandi è gestito da un controller centrale che orchestra diversi servizi specializzati.

```
+----------------+      +------------------+      +----------------+
|  INPUT (VOCE)  | ---> |   Voice Service  | ---> |                |      +----------------+      +---------------+
+----------------+      | (STT Locale/API) |      |                | ---> |   LLM Handler  | ---> |  TTS Service  | ---> AUDIO OUT
                      +------------------+      | Main Controller|      | (Locale/API)   |      | (Locale/API)  |
+----------------+      +------------------+      | (Logica Ibrida)|      +----------------+      +---------------+
| INPUT (TOUCH)  | ---> |   WebSocket      | ---> |                |
+----------------+      |    (GUI)         |      |                |      +----------------+      +---------------+
                      +------------------+      +----------------+ ---> |   Servizi      | ---> |   Hardware    |
                                                                       | (DB, OBD, GPS) |      | (GPIO, etc.)  |
                                                                       +----------------+      +---------------+
```
---
### 4. Stack Tecnologico

#### Hardware
- Unità Centrale: Raspberry Pi 5 (8GB RAM)
- Display & Input: Touchscreen DSI/USB da 7"
- Audio: Microfono USB, Altoparlanti
- Integrazione Veicolo: Adattatore OBD-II Bluetooth
- Posizionamento: Modulo GPS USB/GPIO
- Case: Enclosure custom stampato in 3D con indicatore di attività "Scanner" a LED rossi.

#### Software & Linguaggi
- Backend & Logica Principale: Python 3.x
- Framework Web & Comunicazione: Flask (per il server locale) e Flask-SocketIO (per i WebSockets).
- Interfaccia Grafica (Frontend): HTML5, CSS3, JavaScript (ES6+).
- Database: SQLite per la gestione dei log di manutenzione e dei promemoria.
- Intelligenza Artificiale:
  - Orchestrazione LLM Locale: Ollama
  - Modelli LLM Locali: Mistral 7B (primario), Llama 2, Phi-2.
  - API Cloud: Google Gemini API, Google Cloud Speech-to-Text, Google Cloud Text-to-Speech.
  - RAG (Retrieval-Augmented Generation): Gestione della conoscenza su documenti locali tramite librerie Python dedicate.

### 5. Design Language: L'Estetica "KITT"

L'identità visiva di FRANK è un omaggio funzionale all'estetica retrofuturistica anni '80.

#### Design Fisico
- Case: Nero opaco, linee squadrate, progettato per un montaggio a incasso.
- Scanner LED: Striscia di LED rossi indirizzabili che si anima durante l'attività di FRANK, simulando lo scanner di KITT.

#### Interfaccia Grafica (GUI)
- Palette Colori: Sfondo nero puro (#000000), rosso acceso (#FF0000) per elementi attivi e voce, ambra (#FFBF00) o verde (#32CD32) per il testo, e ciano (#00FFFF) per grafici e mappe.
- Tipografia: Font monospaziati e squadrati (es. VT323) per un feeling da terminale vintage.
- Elementi Visivi: Layout a griglia, bordi netti, barre di progresso orizzontali e grafici a linee. L'elemento centrale è un modulatore vocale a barre rosse che si anima in tempo reale con la voce di FRANK.
- Suoni: Feedback sonoro ("beep", "bloop") per ogni interazione touch.

#### Logo
> Logo tipografico basato sulla parola "FRANK". Il font è monospaziato e digitale, in rosso acceso su sfondo nero. La lettera "A" è un triangolo stilizzato, il cui trattino orizzontale è sostituito da una barra verticale più luminosa (la "I" di "AI") con un forte effetto "glow". L'intero logo presenta un leggero alone e deboli linee di scansione orizzontali per un effetto monitor CRT.

---
### 6. Struttura del Codice

Struttura attuale del repository:

```
./
├── app.py
├── backend/
│   ├── __init__.py
│   ├── main_controller.py
│   └── core/
│       ├── __init__.py
│       ├── command_processor.py
│       ├── communication_handler.py
│       ├── connection_manager.py
│       └── main_controller.py
├── frontend/
│   ├── templates/
│   │   ├── user.html
│   │   └── debug.html
│   └── static/
│       ├── css/
│       │   ├── user.css
│       │   └── debug.css
│       └── js/
│           ├── user.js
│           └── debug.js
└── README.md
```

---
### 7. Architettura MCP: come FRANK traduce richieste in azioni

MCP (Model Context Protocol) è un protocollo che permette a un modello linguistico di dialogare in modo ordinato con “strumenti” del sistema: servizi che sanno fare cose concrete (navigare, leggere lo stato del veicolo, mostrare il meteo, gestire promemoria, ecc.). In pratica, MCP è il ponte tra la comprensione del linguaggio naturale e l’esecuzione di azioni reali.

In parole tecniche ma semplici
- Ruoli in gioco:
  - Utente e Interfaccia: tu parli o scrivi; la GUI e la voce inviano la richiesta.
  - Orchestratore LLM: interpreta l’intento della richiesta e decide se usare uno o più strumenti.
  - Client MCP: fa da “segretario” tra l’orchestratore e gli strumenti, inoltrando richieste in un formato standard.
  - Server MCP (Strumenti): espongono capacità specifiche (es. “imposta rotta”, “recupera meteo”) con descrizioni chiare di cosa accettano e cosa restituiscono.
  - Controller di Sistema: riceve l’esito e aggiorna l’interfaccia o il veicolo con azioni visibili all’utente.

- Cosa succede quando chiedi qualcosa:
  1) Comprensione dell’intento: “Portami a Roma evitando i pedaggi” viene compreso come un obiettivo di navigazione con preferenze.
  2) Scelta dello strumento: l’orchestratore individua lo strumento “Navigatore”.
  3) Preparazione dei parametri: dal testo vengono estratti i dettagli essenziali (destinazione: Roma; evita pedaggi: sì).
  4) Richiesta allo strumento: il Client MCP invia la richiesta al tool di navigazione in forma strutturata.
  5) Esecuzione e risultato: lo strumento esegue l’azione e risponde con un esito chiaro.
  6) Aggiornamento per l’utente: FRANK conferma cosa sta facendo e, se serve, compie un’azione nell’interfaccia (per esempio, avvia la vista navigazione).

- Perché un protocollo è utile:
  - Ordine e chiarezza: ogni strumento dichiara in modo preciso cosa sa fare e quali informazioni gli servono.
  - Estendibilità: aggiungere un nuovo strumento non richiede cambiare il modo in cui “il cervello” di FRANK pensa; basta “presentarlo” tramite MCP.
  - Affidabilità: se mancano informazioni, FRANK può chiedere un chiarimento prima di procedere; se un’azione è delicata, può richiedere conferma.
  - Sicurezza e limiti: gli strumenti sono utilizzati entro confini chiari (cosa è permesso e cosa no), e possono essere monitorati nel tempo (tempi di risposta, errori, utilizzo).

- Esempi tipici di strumenti:
  - Navigatore: imposta la rotta, applica preferenze come “evita pedaggi” o “evita autostrade”.
  - Meteo: recupera condizioni attuali e previsioni per una località.
  - Stato Veicolo: riassume informazioni utili alla guida (es. autonomia stimata).
  - Manutenzione: consulta scadenze e promemoria.

- Cosa vedi tu, alla guida:
  - Conversazioni naturali: ti esprimi liberamente, FRANK capisce lo scopo.
  - Trasparenza: FRANK spiega l’azione che intende fare (“Imposto la rotta per Roma evitando i pedaggi”).
  - Continuità: se serve un dettaglio in più, te lo chiede con una domanda mirata.
  - Azioni concrete: la richiesta non resta “a parole”, ma diventa una funzione attivata nel sistema.

In sintesi: MCP consente a FRANK di essere non solo un assistente che comprende, ma un agente che agisce. Tu esprimi un obiettivo; FRANK seleziona lo strumento giusto, raccoglie i dettagli necessari, esegue e ti tiene informato passo dopo passo.

---

### 8. Sistema di Monitoraggio Emozioni

FRANK include un sistema avanzato di monitoraggio emozioni in tempo reale che utilizza la webcam per rilevare e analizzare le espressioni facciali del guidatore, fornendo feedback utile per il benessere durante la guida.

#### 8.1 Caratteristiche del Sistema

- **Rilevamento Volti Real-time**: Utilizza OpenCV con Haar Cascades per il rilevamento dei volti con fallback automatico ai modelli integrati
- **Analisi Emozioni**: Modello TensorFlow per la classificazione delle emozioni (felice, triste, arrabbiato, sorpreso, paura, disgusto, neutrale)
- **Thread Safety**: Sistema progettato per la stabilità su Windows con lock per evitare race conditions
- **UI Minimalista**: Interfaccia semplificata che mostra solo il feed video con overlay real-time delle emozioni rilevate

#### 8.2 Stabilità AI e Compatibilità Windows

Il sistema è stato progettato per massimizzare la stabilità su sistemi Windows:

- **Fallback Haar Cascade**: Se il percorso custom non è valido, il sistema fallback automaticamente alla cascade integrata in OpenCV (`cv2.data.haarcascades`)
- **Thread Safety**: Tutte le operazioni di rilevamento e inferenza sono protette da lock per evitare crash concorrenti
- **OpenCV Single Thread**: `cv2.setNumThreads(1)` per ridurre problemi di threading su Windows
- **Controllo Percorsi ASCII**: Raccomandazioni per evitare caratteri non-ASCII nei percorsi per compatibilità Windows

#### 8.3 Configurazione e Utilizzo

**Accesso al Monitor**: Naviga a `/monitor/<driver_id>` per accedere all'interfaccia di monitoraggio.

**Variabili d'Ambiente Supportate**:
```bash
# Percorsi AI
EMOTION_MODEL_PATH=models/emotion_model.keras  # Percorso al modello Keras
HAAR_CASCADE_PATH=path/to/custom/cascade.xml   # Percorso custom cascade (opzionale)

# Configurazione Server (via run.py)
FLASK_USE_RELOADER=0    # Disabilita reloader per stabilità (default: 1)
FLASK_THREADED=1        # Abilita threading (default: 1)
```

**Dipendenze Richieste**:
- OpenCV: `opencv-python==4.10.0.84`
- TensorFlow: `tensorflow==2.18.0`
- NumPy: `numpy==1.26.4`

#### 8.4 Interfaccia Utente

L'interfaccia di monitoraggio è stata semplificata per ridurre distrazioni:

- **Video Feed**: Streaming della webcam in tempo reale
- **Canvas Overlay**: Riquadro del volto rilevato con etichetta emozione e confidenza
- **Controlli Minimali**: Solo pulsanti di avvio/stop e regolazione FPS
- **Design KITT**: Estetica coerente con il resto dell'interfaccia Frank

#### 8.5 API Endpoints

- `GET /monitor/<driver_id>`: Interfaccia web per il monitoraggio
- `POST /api/drivers/<driver_id>/monitor/frame`: Analisi frame per rilevamento emozioni

#### 8.6 Raccomandazioni per l'Uso

- **Illuminazione**: Assicurarsi di avere illuminazione adeguata per il rilevamento dei volti
- **Posizionamento Camera**: Posizionare la webcam ad altezza occhi per migliori risultati
- **Performance**: Utilizzare 1 FPS per bilanciare prestazioni e accuratezza
- **Privacy**: Il sistema analizza solo in locale, nessun dato viene inviato a servizi esterni

---

### 9. Configurazione e Deployment

#### 9.1 Installazione Dipendenze

```bash
# Installa le dipendenze Python
pip install -r requirements.txt

# Per sviluppo con controllo stabilità
pip install opencv-python tensorflow numpy
```

#### 9.2 Avvio del Server

**Metodo Standard** (app.py):
```bash
python app.py
```

**Metodo Configurabile** (run.py):
```bash
# Avvio standard
python run.py

# Configurazione per stabilità massima su Windows
FLASK_USE_RELOADER=0 FLASK_THREADED=0 python run.py

# Configurazione per performance con threading controllato
FLASK_USE_RELOADER=0 FLASK_THREADED=1 python run.py
```

#### 9.3 Requisiti Sistema

- **Minimo**: Python 3.8+, 4GB RAM, webcam
- **Raccomandato**: Python 3.9+, 8GB RAM, webcam HD
- **AI Emozioni**: TensorFlow compatible GPU opzionale per performance migliori

#### 9.4 Note per Windows

- Evitare percorsi con caratteri non-ASCII per modelli AI e cascade
- Utilizzare `FLASK_USE_RELOADER=0` in produzione per stabilità
- Considerare antivirus exceptions per cartelle modelli AI

#### 9.5 Troubleshooting

**Problemi Comuni**:
- **Haar Cascade vuoto**: Controlla i log per il fallback automatico a OpenCV built-in
- **Crash threading**: Usa `FLASK_THREADED=0` per debugging
- **Performance lenta**: Riduci FPS analisi o considera GPU acceleration
- **Errori camera**: Verifica permessi webcam nel browser

**Log Utili**:
```bash
# Verifica inizializzazione sistema AI
grep "EmotionDetector" logs/app.log

# Controlla fallback Haar Cascade
grep "Haar Cascade" logs/app.log

# Monitor performance threading
grep "threading\|lock" logs/app.log
```

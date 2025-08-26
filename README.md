---

# Progetto FRANK: Un Assistente di Bordo AI per Camper

[![Stato del Progetto](https://img.shields.io/badge/status-in%20sviluppo-orange)](https://github.com/tuo-username/frank-assistant)

> "Un assistente di bordo intelligente, offline-first e multimodale, con l'anima di KITT di Supercar. Progettato per essere il compagno di viaggio definitivo."

FRANK è un assistente AI all-in-one, costruito su un Raspberry Pi 5, che si integra nativamente nel cruscotto di un camper per fornire navigazione, monitoraggio del veicolo, gestione della manutenzione e molto altro, attraverso un'interfaccia vocale e touch dal design retrofuturistico.

<img width="1024" height="461" alt="FrankBanner" src="https://github.com/user-attachments/assets/aae6fdc3-11f1-4c7d-a852-6006396fdc31" />

[**CLICCA QUI PER LA DOCUMENTAZIONE COMPLETA**](https://lateral-saxophone-9f2.notion.site/Frank-camper-assistant-247521f00178803c900adc6934c3df84)

---

### **Indice**

1.  [**Visione del Progetto**](#1-visione-del-progetto)
2.  [**Filosofia Architettonica**](#2-filosofia-architettonica)
3.  [**Blueprint del Sistema**](#3-blueprint-del-sistema)
4.  [**Stack Tecnologico**](#4-stack-tecnologico)
5.  [**Design Language: L'Estetica "KITT"**](#5-design-language-lestetica-kitt)
6.  [**Struttura del Codice**](#6-struttura-del-codice)
---

### **1. Visione del Progetto**

L'obiettivo di FRANK è creare un assistente di bordo che sia parte integrante del veicolo, non un'applicazione accessoria. Fornisce al guidatore un controllo centralizzato e un accesso intuitivo alle informazioni critiche del viaggio e del camper, minimizzando le distrazioni e massimizzando l'efficienza.

### **2. Filosofia Architettonica**

Il sistema è costruito su due concetti fondamentali per garantire affidabilità e usabilità in un ambiente mobile come un camper.

*   **Approccio Ibrido ("Offline-First"):** Le funzioni critiche (navigazione, stato del veicolo, accesso ai log) sono gestite da un LLM locale e devono funzionare perfettamente senza connessione internet. Il sistema si "potenzia" quando online, utilizzando API cloud per dati in tempo reale (meteo, traffico) e per una qualità di interazione superiore.

*   **Interfaccia Multimodale (Voce + Touch):** Voce e schermo lavorano in sinergia. La voce è il metodo di input primario per comandi rapidi, mentre il touchscreen offre un riscontro visivo dettagliato e un controllo tattile completo.

### **3. Blueprint del Sistema**

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

### **4. Stack Tecnologico**

#### **Hardware**
*   **Unità Centrale:** Raspberry Pi 5 (8GB RAM)
*   **Display & Input:** Touchscreen DSI/USB da 7"
*   **Audio:** Microfono USB, Altoparlanti
*   **Integrazione Veicolo:** Adattatore OBD-II Bluetooth
*   **Posizionamento:** Modulo GPS USB/GPIO
*   **Case:** Enclosure custom stampato in 3D con indicatore di attività "Scanner" a LED rossi.

#### **Software & Linguaggi**
*   **Backend & Logica Principale:** **Python 3.x**
*   **Framework Web & Comunicazione:** **Flask** (per il server locale) e **Flask-SocketIO** (per i WebSockets).
*   **Interfaccia Grafica (Frontend):** **HTML5, CSS3, JavaScript (ES6+)**.
*   **Database:** **SQLite** per la gestione dei log di manutenzione e dei promemoria.
*   **Intelligenza Artificiale:**
    *   **Orchestrazione LLM Locale:** **Ollama**
    *   **Modelli LLM Locali:** Mistral 7B (primario), Llama 2, Phi-2.
    *   **API Cloud:** Google Gemini API, Google Cloud Speech-to-Text, Google Cloud Text-to-Speech.
    *   **RAG (Retrieval-Augmented Generation):** Gestione della conoscenza su documenti locali tramite librerie Python dedicate.

### **5. Design Language: L'Estetica "KITT"**

L'identità visiva di FRANK è un omaggio funzionale all'estetica retrofuturistica anni '80.

#### **Design Fisico**
*   **Case:** Nero opaco, linee squadrate, progettato per un montaggio a incasso.
*   **Scanner LED:** Striscia di LED rossi indirizzabili che si anima durante l'attività di FRANK, simulando lo scanner di KITT.

#### **Interfaccia Grafica (GUI)**
*   **Palette Colori:** Sfondo nero puro (`#000000`), rosso acceso (`#FF0000`) per elementi attivi e voce, ambra (`#FFBF00`) o verde (`#32CD32`) per il testo, e ciano (`#00FFFF`) per grafici e mappe.
*   **Tipografia:** Font monospaziati e squadrati (es. `VT323`) per un feeling da terminale vintage.
*   **Elementi Visivi:** Layout a griglia, bordi netti, barre di progresso orizzontali e grafici a linee. L'elemento centrale è un **modulatore vocale** a barre rosse che si anima in tempo reale con la voce di FRANK.
*   **Suoni:** Feedback sonoro ("beep", "bloop") per ogni interazione touch.

#### **Logo**
> Logo tipografico basato sulla parola "FRANK". Il font è monospaziato e digitale, in rosso acceso su sfondo nero. La lettera "A" è un triangolo stilizzato, il cui trattino orizzontale è sostituito da una barra verticale più luminosa (la "I" di "AI") con un forte effetto "glow". L'intero logo presenta un leggero alone e deboli linee di scansione orizzontali per un effetto monitor CRT.

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

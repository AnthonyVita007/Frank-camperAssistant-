"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/services/db_service.py ###
Servizio Database (SQLite): logging degli eventi (comandi utente, risposte backend, info sistema).
Pensato per ambiente offline-first, senza dipendenze esterne.
----------------------------------------------------------------------------------------------------
"""

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 1: IMPORT ###
# --------------------------------------------------------------------------------------------------
#
import os
import sqlite3
import logging
import configparser
from datetime import datetime
from typing import List, Dict, Any

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 2: CONFIGURAZIONE E PERCORSI ###
# - Legge config.ini (se presente) per directory dati e nome DB.
# - Default: data/frank_database.db
# --------------------------------------------------------------------------------------------------
#
_config = configparser.ConfigParser()
if os.path.exists('config.ini'):
    _config.read('config.ini')

DATA_DIR = _config.get('paths', 'DATA_DIR', fallback='data')
DB_NAME = _config.get('paths', 'DB_NAME', fallback='frank_database.db')
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# Nome tabella eventi
TABLE_EVENTS = "events"

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 3: UTILITÀ BASE (connessione e bootstrap) ###
# --------------------------------------------------------------------------------------------------
#
def _ensure_data_dir() -> None:
    """
    Crea la cartella dei dati se non esiste.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        logging.error(f"[DBService] Impossibile creare la cartella dati '{DATA_DIR}': {e}")
        raise

def _get_connection() -> sqlite3.Connection:
    """
    Ritorna una connessione SQLite al database dell'app.
    check_same_thread=False per supportare thread diversi (SocketIO).
    """
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 4: INIZIALIZZAZIONE SCHEMA ###
# --------------------------------------------------------------------------------------------------
#
def init_db() -> None:
    """
    Inizializza lo schema del database se non esiste.
    Crea la tabella 'events' con:
      - id INTEGER PK
      - ts TEXT (ISO8601 UTC)
      - source TEXT ('user' | 'backend' | 'system')
      - event_type TEXT ('command' | 'response' | 'info' | altro)
      - content TEXT (messaggio)
    """
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_EVENTS} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        source TEXT NOT NULL,
        event_type TEXT NOT NULL,
        content TEXT NOT NULL
    );
    """
    try:
        with _get_connection() as conn:
            conn.execute(ddl)
            conn.commit()
        logging.debug("[DBService] Database inizializzato correttamente.")
    except Exception as e:
        logging.error(f"[DBService] Errore inizializzazione DB: {e}")
        raise

#
# --------------------------------------------------------------------------------------------------
# ### PARTE 5: OPERAZIONI DI LOG E LETTURA ###
# --------------------------------------------------------------------------------------------------
#
def log_event(source: str, event_type: str, content: str) -> int | None:
    """
    Inserisce un evento nello storico.
    Ritorna l'id dell'evento creato oppure None in caso di errore.
    """
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    sql = f"INSERT INTO {TABLE_EVENTS} (ts, source, event_type, content) VALUES (?, ?, ?, ?)"
    try:
        with _get_connection() as conn:
            cur = conn.execute(sql, (ts, source, event_type, content or ""))
            conn.commit()
            event_id = cur.lastrowid
            logging.debug(f"[DBService] Log evento #{event_id}: {source}/{event_type} - {content}")
            return event_id
    except Exception as e:
        logging.error(f"[DBService] Errore log_event: {e}")
        return None

def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Recupera gli ultimi 'limit' eventi in ordine cronologico (dal più vecchio al più recente).
    """
    limit = max(1, min(int(limit or 50), 500))
    sql = f"SELECT id, ts, source, event_type, content FROM {TABLE_EVENTS} ORDER BY id DESC LIMIT ?"
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        # inverti per cronologia crescente
        events = [dict(r) for r in reversed(rows)]
        logging.debug(f"[DBService] Recuperati {len(events)} eventi recenti.")
        return events
    except Exception as e:
        logging.error(f"[DBService] Errore get_recent_events: {e}")
        return []

def format_event_line(event: Dict[str, Any]) -> str:
    """
    Restituisce una riga testuale compatta per il log UI.
    Esempio: [2025-08-13T17:10:00Z] [user/command] Ciao
    """
    ts = event.get("ts", "----")
    src = event.get("source", "?")
    ety = event.get("event_type", "?")
    msg = event.get("content", "")
    return f"[{ts}] [{src}/{ety}] {msg}"

#
# --------------------------------------------------------------------------------------------------
# ### FINE FILE ###
# --------------------------------------------------------------------------------------------------
#
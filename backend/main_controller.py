"""
----------------------------------------------------------------------------------------------------
### CODICE PER backend/main_controller.py ###
Questo file mantiene la compatibilità con l'architettura esistente
delegando tutto alla nuova implementazione OOP nel modulo core.
----------------------------------------------------------------------------------------------------
"""

# Importazione della nuova implementazione OOP
from backend.core.main_controller import setup_socketio_events

# La funzione setup_socketio_events è ora disponibile tramite import
# e utilizza la nuova architettura Object-Oriented mantenendo
# la stessa interfaccia per compatibilità con app.py
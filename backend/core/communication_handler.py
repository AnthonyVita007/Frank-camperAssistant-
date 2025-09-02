"""
Communication Handler Module for Frank Camper Assistant.

This module manages the communication between the client and server,
handling message reception, processing, and response transmission.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE
#----------------------------------------------------------------
import logging
import uuid
import time
from typing import Dict, Any, Optional
from flask import request
from flask_socketio import SocketIO

from .command_processor import CommandProcessor, CommandResult
from ..ai.ai_handler import AIHandler
from ..ai.ai_response import AIResponse


class CommunicationHandler:
    """
    Handles communication between client and server.
    
    This class manages the bidirectional communication flow:
    - Receives messages from clients
    - Routes messages to appropriate processors (commands or AI)
    - Sends responses back to clients
    - Manages different types of communication events
    
    Attributes:
        _socketio_instance (SocketIO): The Flask-SocketIO instance
        _command_processor (CommandProcessor): Processor for handling commands
        _ai_handler (AIHandler): Handler for AI requests
    """
    
    #----------------------------------------------------------------
    # COSTRUTTORE
    #----------------------------------------------------------------
    def __init__(self, socketio_instance: SocketIO, command_processor: CommandProcessor, ai_handler: AIHandler) -> None:
        """
        Initialize the CommunicationHandler.
        
        Args:
            socketio_instance (SocketIO): The Flask-SocketIO instance
            command_processor (CommandProcessor): The command processor instance
            ai_handler (AIHandler): The AI handler instance
        """
        self._socketio_instance = socketio_instance
        self._command_processor = command_processor
        self._ai_handler = ai_handler
        self._setup_communication_handlers()
        
        logging.debug('[CommunicationHandler] Communication handler initialized')
    
    #----------------------------------------------------------------
    # REGISTRAZIONE HANDLER SOCKET.IO
    #----------------------------------------------------------------
    def _setup_communication_handlers(self) -> None:
        """
        Set up the communication event handlers.
        
        This method registers event handlers for different types of
        communication events with the SocketIO instance.
        """
        @self._socketio_instance.on('frontend_command')
        def handle_frontend_command(json_data):
            """Handle commands received from the frontend."""
            # Cattura il SID del client per risposte indirizzate
            client_sid = getattr(request, 'sid', None)
            self._handle_frontend_command(json_data, client_sid)

        #----------------------------------------------------------------
        # REGISTRAZIONE: TOGGLE PROVIDER AI (LOCAL ↔ GEMINI)
        #----------------------------------------------------------------
        @self._socketio_instance.on('ui_ai_provider_toggle')
        def handle_ui_ai_provider_toggle(json_data):
            """Handle AI provider toggle from the UI."""
            client_sid = getattr(request, 'sid', None)
            self._handle_ai_provider_toggle(json_data, client_sid)

        #----------------------------------------------------------------
        # REGISTRAZIONE: FRONTEND ACTIONS (es. cancel_tool)
        #----------------------------------------------------------------
        @self._socketio_instance.on('frontend_action')
        def handle_frontend_action(json_data):
            """Handle frontend actions like tool cancellation."""
            client_sid = getattr(request, 'sid', None)
            self._handle_frontend_action(json_data, client_sid)
    
    #----------------------------------------------------------------
    # INSTRADAMENTO RICHIESTE DAL FRONTEND
    #----------------------------------------------------------------
    def _handle_frontend_command(self, json_data: Optional[Dict[str, Any]], sid: Optional[str] = None) -> None:
        """
        Handle a request received from the frontend with rigorous tool session gating.

        This method processes both commands and AI requests sent by the frontend client,
        validates the input, routes to appropriate processor, and sends responses.

        During active tool sessions, ALL input is routed to tool handling except cancellation.
        """
        try:
            # Estrazione e validazione input
            user_input = self._extract_command(json_data)
            if user_input is None:
                self._send_error_response('Richiesta non valida o vuota', sid)
                return

            logging.info(f'[CommunicationHandler] Received input: "{user_input}"')

            # 1) Gestisci SEMPRE i comandi prima di qualsiasi routing verso LLM/delegation
            if self._is_command(user_input):
                result, is_recognized = self._command_processor.process_command(user_input)
                if is_recognized:
                    self._send_command_response(result, sid)
                else:
                    self._send_error_response(result.data, sid)
                return

            # 2) Delegation-aware routing (solo se NON è un comando)
            session_id = sid or 'default'

            if hasattr(self._ai_handler, 'route_user_message'):
                logging.debug(f'[CommunicationHandler] Using delegation-aware routing for {session_id}')
                ai_response = self._ai_handler.route_user_message(session_id, user_input)
                self._send_ai_response(ai_response, sid)
                return

            # 3) Legacy fallback per tool sessions
            elif hasattr(self._ai_handler, 'is_tool_session_active') and self._ai_handler.is_tool_session_active(session_id):
                logging.debug(f'[CommunicationHandler] Active tool session detected for {session_id} - routing to tool handler')
                ai_response = self._ai_handler.continue_tool_clarification(session_id, user_input)
                self._send_ai_response(ai_response, sid)
                return

            # 4) Fallback: richiesta AI normale (streaming)
            request_id = str(uuid.uuid4())
            logging.debug(f'[CommunicationHandler] Starting AI request with ID: {request_id}')
            self._socketio_instance.start_background_task(
                self._handle_ai_streaming_request,
                user_input,
                request_id,
                sid
            )

        except Exception as e:
            logging.error(f'[CommunicationHandler] Error handling frontend request: {e}')
            self._send_error_response('Errore interno del server', sid)

    #----------------------------------------------------------------
    # GESTIONE: TOGGLE PROVIDER AI (LOCAL ↔ GEMINI)
    #----------------------------------------------------------------
    def _handle_ai_provider_toggle(self, json_data: Optional[Dict[str, Any]], sid: Optional[str] = None) -> None:
        """
        Handle the UI toggle to switch AI provider and reset the session.
        
        Expected payload:
          { "provider": "local" | "gemini" }
        """
        try:
            # Validazione payload
            if not json_data or not isinstance(json_data, dict):
                logging.warning('[CommunicationHandler] Invalid payload for ui_ai_provider_toggle')
                self._send_error_response('Payload non valido per cambio provider', sid)
                return
            
            provider_str = str(json_data.get('provider', '')).strip().lower()
            if provider_str not in ('local', 'gemini'):
                logging.warning(f'[CommunicationHandler] Unknown provider requested: "{provider_str}"')
                self._send_error_response('Provider richiesto non valido (usa "local" o "gemini")', sid)
                return
            
            # Verifica che l'AI handler supporti lo switch
            if not hasattr(self._ai_handler, 'set_ai_provider'):
                logging.warning('[CommunicationHandler] AIHandler does not support provider switching')
                self._send_error_response('Cambio provider non supportato in questa configurazione', sid)
                return
            
            # Prova a usare l'Enum se disponibile, altrimenti fallback a stringhe
            success = False
            try:
                from ..ai.ai_processor import AIProvider  # Enum disponibile con dual-provider
                target = AIProvider.GEMINI if provider_str == 'gemini' else AIProvider.LOCAL
                success = self._ai_handler.set_ai_provider(target)  # type: ignore
            except Exception:
                # Fallback: passiamo la stringa (supportato dalla versione aggiornata dell’AIHandler)
                success = self._ai_handler.set_ai_provider(provider_str)  # type: ignore
            
            if not success:
                logging.warning('[CommunicationHandler] AI provider switch failed')
                self._send_error_response('Impossibile cambiare provider AI (verifica disponibilità)', sid)
                return
            
            #----------------------------------------------------------------
            # VERIFICA PROVIDER ATTUALE DOPO SWITCH (GESTIONE FALLBACK)
            #----------------------------------------------------------------
            # Controlla quale provider è effettivamente attivo ora
            current_provider = None
            if hasattr(self._ai_handler, 'get_current_ai_provider'):
                try:
                    current_provider_obj = self._ai_handler.get_current_ai_provider()
                    if current_provider_obj:
                        if hasattr(current_provider_obj, 'value'):
                            current_provider = current_provider_obj.value
                        else:
                            current_provider = str(current_provider_obj).lower()
                except Exception as e:
                    logging.debug(f'[CommunicationHandler] Could not get current provider: {e}')
            
            # Se non riusciamo a determinare il provider, assumiamo il successo
            if not current_provider:
                current_provider = provider_str
            
            #----------------------------------------------------------------
            # RESET: CLEAR LOG + MESSAGGIO DI STATO
            #----------------------------------------------------------------
            # Clear log sul client corrente
            self._socketio_instance.emit('backend_action', {
                'action': 'clear_log',
                'data': 'Console pulita dopo cambio provider.'
            }, to=sid)
            
            # Messaggio di conferma o fallback
            if current_provider == provider_str:
                # Switch avvenuto come richiesto
                human_label = 'LOCAL (llama.cpp)' if current_provider == 'local' else 'CLOUD (Gemini)'
                self._socketio_instance.emit('backend_response', {
                    'data': f'Provider AI impostato: {human_label}',
                    'type': 'system'
                }, to=sid)
                logging.info(f'[CommunicationHandler] AI provider switched to: {current_provider}')
            else:
                # Fallback automatico è avvenuto
                requested_label = 'LOCAL (llama.cpp)' if provider_str == 'local' else 'CLOUD (Gemini)'
                actual_label = 'LOCAL (llama.cpp)' if current_provider == 'local' else 'CLOUD (Gemini)'
                self._socketio_instance.emit('backend_response', {
                    'data': f'Fallback automatico: {requested_label} non disponibile, attivato {actual_label}',
                    'type': 'system'
                }, to=sid)
                logging.info(f'[CommunicationHandler] AI provider fallback: requested {provider_str}, got {current_provider}')
                
                # Aggiorna UI per riflettere il provider effettivamente attivo
                self._socketio_instance.emit('backend_action', {
                    'action': 'update_ai_provider',
                    'data': current_provider
                }, to=sid)
            
            #----------------------------------------------------------------
            # WARMUP NON BLOCCANTE DEL NUOVO PROVIDER
            #----------------------------------------------------------------
            def _do_warmup():
                try:
                    if hasattr(self._ai_handler, '_ai_processor') and self._ai_handler._ai_processor:
                        self._ai_handler._ai_processor.warmup()
                except Exception as warm_err:
                    logging.debug(f'[CommunicationHandler] Warmup after switch failed (non-critical): {warm_err}')
            
            self._socketio_instance.start_background_task(_do_warmup)
        
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error handling AI provider toggle: {e}')
            self._send_error_response('Errore durante il cambio provider', sid)
    
    #----------------------------------------------------------------
    # GESTIONE: FRONTEND ACTIONS (es. cancel_tool)
    #----------------------------------------------------------------
    def _handle_frontend_action(self, json_data: Optional[Dict[str, Any]], sid: Optional[str] = None) -> None:
        """
        Handle frontend actions like tool cancellation.
        
        Expected payload:
          { "action": "cancel_tool" }
        """
        try:
            # Validazione payload
            if not json_data or not isinstance(json_data, dict):
                logging.warning('[CommunicationHandler] Invalid payload for frontend_action')
                self._send_error_response('Payload non valido per azione frontend', sid)
                return
            
            action = json_data.get('action', '').strip()
            if not action:
                logging.warning('[CommunicationHandler] No action specified in frontend_action')
                self._send_error_response('Nessuna azione specificata', sid)
                return
            
            if action == 'cancel_tool':
                # Handle tool cancellation with delegation support
                session_id = sid or 'default'
                
                # Check if delegation is active and route to agent
                if hasattr(self._ai_handler, 'has_active_delegation') and self._ai_handler.has_active_delegation(session_id):
                    if hasattr(self._ai_handler, '_tool_lifecycle_agent') and self._ai_handler._tool_lifecycle_agent:
                        ai_response = self._ai_handler._tool_lifecycle_agent.cancel(session_id, "user_cancel")
                        self._send_ai_response(ai_response, sid)
                        logging.info(f'[CommunicationHandler] Tool session canceled via agent for session {session_id}')
                    else:
                        ai_response = AIResponse(
                            text="Errore: agente tool non disponibile.",
                            success=False,
                            response_type="error"
                        )
                        self._send_ai_response(ai_response, sid)
                # Legacy tool session handling
                elif hasattr(self._ai_handler, 'has_pending_tool_session') and self._ai_handler.has_pending_tool_session(session_id):
                    ai_response = self._ai_handler.cancel_tool_session(session_id)
                    self._send_ai_response(ai_response, sid)
                    logging.info(f'[CommunicationHandler] Tool session canceled for session {session_id}')
                else:
                    # No pending session - just send a confirmation
                    ai_response = AIResponse(
                        text="Nessuna operazione da annullare.",
                        success=True,
                        response_type="conversational"
                    )
                    self._send_ai_response(ai_response, sid)
            else:
                logging.warning(f'[CommunicationHandler] Unknown frontend action: {action}')
                self._send_error_response(f'Azione non riconosciuta: {action}', sid)
        
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error handling frontend action: {e}')
            self._send_error_response('Errore durante l\'esecuzione dell\'azione', sid)
    
    #----------------------------------------------------------------
    # UTILITÀ: ESTRARRE COMANDO
    #----------------------------------------------------------------
    def _extract_command(self, json_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Extract the command string from the received JSON data.
        
        Args:
            json_data (Optional[Dict[str, Any]]): The JSON data from frontend
            
        Returns:
            Optional[str]: The extracted command string, or None if invalid
        """
        if not json_data or not isinstance(json_data, dict):
            logging.warning('[CommunicationHandler] Received invalid JSON data')
            return None
        
        command = json_data.get('data', '').strip()
        if not command:
            logging.warning('[CommunicationHandler] Received empty command')
            return None
        
        return command
    
    #----------------------------------------------------------------
    # INVIO RISPOSTE COMANDI
    #----------------------------------------------------------------
    def _send_command_response(self, result: CommandResult, sid: Optional[str] = None) -> None:
        """
        Send a response for a successfully processed command.
        
        Args:
            result (CommandResult): The result of command processing
            sid (Optional[str]): The Socket.IO session id of the client
        """
        try:
            if result.action == 'clear_log':
                # Azione di pulizia log mirata al client (se SID presente)
                self._socketio_instance.emit('backend_action', {
                    'action': result.action,
                    'data': result.data
                }, to=sid)
                logging.debug('[CommunicationHandler] Sent clear log action')
                
            elif result.action == 'navigate':
                # Azione di navigazione mirata al client (se SID presente)
                self._socketio_instance.emit('backend_action', {
                    'action': result.action,
                    'data': result.data
                }, to=sid)
                logging.debug(f'[CommunicationHandler] Sent navigation action to: {result.data}')
                
            else:
                # Risposta generica comando
                self._socketio_instance.emit('backend_response', {
                    'data': result.data
                }, to=sid)
                logging.debug('[CommunicationHandler] Sent generic response')
                
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error sending command response: {e}')
            self._send_error_response('Errore nell\'invio della risposta', sid)
    
    #----------------------------------------------------------------
    # INVIO RISPOSTE DI ERRORE
    #----------------------------------------------------------------
    def _send_error_response(self, error_message: str, sid: Optional[str] = None) -> None:
        """
        Send an error response to the client.
        
        Args:
            error_message (str): The error message to send
            sid (Optional[str]): The Socket.IO session id of the client
        """
        try:
            self._socketio_instance.emit('backend_response', {
                'data': f'Errore: {error_message}'
            }, to=sid)
            logging.debug(f'[CommunicationHandler] Sent error response: {error_message}')
        except Exception as e:
            logging.error(f'[CommunicationHandler] Failed to send error response: {e}')
    
    #----------------------------------------------------------------
    # RICONOSCIMENTO COMANDI
    #----------------------------------------------------------------
    def _is_command(self, user_input: str) -> bool:
        """
        Determine if the user input is a command or an AI request.
        
        Commands are identified by starting with '/' character.
        
        Args:
            user_input (str): The user input to check
            
        Returns:
            bool: True if this is a command, False if it's an AI request
        """
        if not user_input or not isinstance(user_input, str):
            return False
        
        return user_input.strip().startswith('/')
    
    #----------------------------------------------------------------
    # INVIO RISPOSTE AI (NON-STREAMING)
    #----------------------------------------------------------------
    def _send_ai_response(self, ai_response: AIResponse, sid: Optional[str] = None) -> None:
        """
        Send an AI response to the client.
        
        Args:
            ai_response (AIResponse): The AI response to send
            sid (Optional[str]): The Socket.IO session id of the client
        """
        try:
            if ai_response.success:
                # Risposta AI con successo
                self._socketio_instance.emit('backend_response', {
                    'data': ai_response.text,
                    'type': 'ai_response',
                    'response_type': ai_response.response_type,
                    'metadata': ai_response.metadata,
                    'suggested_actions': ai_response.suggested_actions
                }, to=sid)
                logging.debug(f'[CommunicationHandler] Sent AI response: {ai_response.text[:100]}...')
            else:
                # Risposta AI di errore
                self._socketio_instance.emit('backend_response', {
                    'data': ai_response.text,
                    'type': 'ai_error',
                    'response_type': ai_response.response_type
                }, to=sid)
                logging.debug(f'[CommunicationHandler] Sent AI error response: {ai_response.text}')
                
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error sending AI response: {e}')
            self._send_error_response('Errore nell\'invio della risposta AI', sid)
    
    #----------------------------------------------------------------
    # STREAMING: GESTIONE RICHIESTA IN BACKGROUND
    #----------------------------------------------------------------
    def _handle_ai_streaming_request(self, user_input: str, request_id: str, sid: Optional[str] = None) -> None:
        """
        Handle an AI request with streaming support in a background task.
        
        This method processes AI requests using streaming to reduce perceived latency
        and provides fallback to non-streaming if streaming fails.
        
        Args:
            user_input (str): The user input to process
            request_id (str): Unique identifier for this request
            sid (Optional[str]): The Socket.IO session id of the client
        """
        try:
            logging.debug(f'[CommunicationHandler] Processing streaming AI request {request_id}')
            
            # Avvio streaming (evento iniziale)
            metadata = {
                'timestamp': time.time(),
                'request_id': request_id,
                'streaming': True
            }
            
            self._socketio_instance.emit('backend_stream_start', {
                'request_id': request_id,
                'metadata': metadata
            }, to=sid)
            
            # Elaborazione streaming con chunk
            accumulated_text = ""
            chunk_count = 0
            
            try:
                for chunk in self._ai_handler.handle_ai_stream(user_input, context={'session_id': sid}):
                    if chunk:
                        accumulated_text += chunk
                        chunk_count += 1
                        
                        self._socketio_instance.emit('backend_stream_chunk', {
                            'request_id': request_id,
                            'delta': chunk
                        }, to=sid)
                
                # Finalizzazione streaming
                final_metadata = {
                    'timestamp': time.time(),
                    'request_id': request_id,
                    'streaming': True,
                    'chunk_count': chunk_count,
                    'total_length': len(accumulated_text),
                    'response_type': 'conversational'
                }
                
                self._socketio_instance.emit('backend_stream_end', {
                    'request_id': request_id,
                    'final': accumulated_text,
                    'metadata': final_metadata
                }, to=sid)
                
                logging.info(f'[CommunicationHandler] Streaming completed for request {request_id}: {chunk_count} chunks')
                
            except Exception as streaming_error:
                logging.warning(f'[CommunicationHandler] Streaming failed for request {request_id}: {streaming_error}')
                
                # Fallback a non-streaming
                try:
                    logging.info(f'[CommunicationHandler] Falling back to non-streaming for request {request_id}')
                    ai_response = self._ai_handler.handle_ai_request(user_input, context={'session_id': sid})
                    
                    # Invio risposta fallback
                    self._send_ai_response(ai_response, sid)
                    
                    # Chiudi lo stato di streaming sul frontend
                    self._socketio_instance.emit('backend_stream_end', {
                        'request_id': request_id,
                        'final': ai_response.text if ai_response.success else "",
                        'metadata': {
                            'timestamp': time.time(),
                            'request_id': request_id,
                            'streaming': False,
                            'fallback': True,
                            'error': str(streaming_error)
                        }
                    }, to=sid)
                    
                except Exception as fallback_error:
                    logging.error(f'[CommunicationHandler] Both streaming and fallback failed for request {request_id}: {fallback_error}')
                    self._send_error_response('Errore nel processare la richiesta AI', sid)
                    
                    # Notifica di chiusura con errore
                    self._socketio_instance.emit('backend_stream_end', {
                        'request_id': request_id,
                        'final': "",
                        'metadata': {
                            'timestamp': time.time(),
                            'request_id': request_id,
                            'streaming': False,
                            'error': True,
                            'error_message': str(fallback_error)
                        }
                    }, to=sid)
        
        except Exception as e:
            logging.error(f'[CommunicationHandler] Unexpected error in streaming handler for request {request_id}: {e}')
            self._send_error_response('Errore interno del server durante lo streaming', sid)
    
    #----------------------------------------------------------------
    # API PUBBLICHE DI EMISSIONE EVENTI
    #----------------------------------------------------------------
    def send_message_to_client(self, event: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to the client.
        
        This method provides a public interface for sending messages
        to the connected client(s).
        
        Args:
            event (str): The event name to emit
            data (Dict[str, Any]): The data to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            # Emissione sicura anche fuori dal contesto richiesta (broadcast)
            self._socketio_instance.emit(event, data)
            logging.debug(f'[CommunicationHandler] Message sent - Event: {event}')
            return True
        except Exception as e:
            logging.error(f'[CommunicationHandler] Failed to send message: {e}')
            return False
    
    def broadcast_message(self, event: str, data: Dict[str, Any]) -> bool:
        """
        Broadcast a message to all connected clients.
        
        Args:
            event (str): The event name to emit
            data (Dict[str, Any]): The data to broadcast
            
        Returns:
            bool: True if broadcast was successful, False otherwise
        """
        try:
            self._socketio_instance.emit(event, data)
            logging.debug(f'[CommunicationHandler] Broadcast sent - Event: {event}')
            return True
        except Exception as e:
            logging.error(f'[CommunicationHandler] Failed to broadcast message: {e}')
            return False
    
    #----------------------------------------------------------------
    # METADATA EVENTI DISPONIBILI
    #----------------------------------------------------------------
    def get_available_events(self) -> Dict[str, str]:
        """
        Get a dictionary of available communication events.
        
        Returns:
            Dict[str, str]: Dictionary mapping event names to descriptions
        """
        return {
            'frontend_command': 'Comando inviato dal frontend',
            'backend_response': 'Risposta generale dal backend',
            'backend_action': 'Azione specifica dal backend (navigazione, clear, etc.)',
            'ui_ai_provider_toggle': 'Toggle provider AI dalla UI (local ↔ gemini)'
        }
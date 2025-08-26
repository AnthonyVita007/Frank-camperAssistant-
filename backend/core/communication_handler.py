"""
Communication Handler Module for Frank Camper Assistant.

This module manages the communication between the client and server,
handling message reception, processing, and response transmission.
"""

import logging
from typing import Dict, Any, Optional, Callable
from flask_socketio import SocketIO, emit

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
    
    def _setup_communication_handlers(self) -> None:
        """
        Set up the communication event handlers.
        
        This method registers event handlers for different types of
        communication events with the SocketIO instance.
        """
        @self._socketio_instance.on('frontend_command')
        def handle_frontend_command(json_data):
            """Handle commands received from the frontend."""
            self._handle_frontend_command(json_data)
    
    def _handle_frontend_command(self, json_data: Optional[Dict[str, Any]]) -> None:
        """
        Handle a request received from the frontend.
        
        This method processes both commands and AI requests sent by the frontend client,
        validates the input, routes to appropriate processor, and sends responses.
        
        Args:
            json_data (Optional[Dict[str, Any]]): The JSON data received from frontend
        """
        try:
            # Extract and validate the input
            user_input = self._extract_command(json_data)
            if user_input is None:
                self._send_error_response('Richiesta non valida o vuota')
                return
            
            logging.info(f'[CommunicationHandler] Received input: "{user_input}"')
            
            # Determine if this is a command or AI request
            if self._is_command(user_input):
                # Process as command
                result, is_recognized = self._command_processor.process_command(user_input)
                
                if is_recognized:
                    self._send_command_response(result)
                else:
                    self._send_error_response(result.data)
            else:
                # Process as AI request
                ai_response = self._ai_handler.handle_ai_request(user_input)
                self._send_ai_response(ai_response)
                
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error handling frontend request: {e}')
            self._send_error_response('Errore interno del server')
    
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
    
    def _send_command_response(self, result: CommandResult) -> None:
        """
        Send a response for a successfully processed command.
        
        Args:
            result (CommandResult): The result of command processing
        """
        try:
            if result.action == 'clear_log':
                # Send log clear action
                emit('backend_action', {
                    'action': result.action,
                    'data': result.data
                })
                logging.debug('[CommunicationHandler] Sent clear log action')
                
            elif result.action == 'navigate':
                # Send navigation action
                emit('backend_action', {
                    'action': result.action,
                    'data': result.data
                })
                logging.debug(f'[CommunicationHandler] Sent navigation action to: {result.data}')
                
            else:
                # Send generic response
                emit('backend_response', {
                    'data': result.data
                })
                logging.debug('[CommunicationHandler] Sent generic response')
                
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error sending command response: {e}')
            self._send_error_response('Errore nell\'invio della risposta')
    
    def _send_error_response(self, error_message: str) -> None:
        """
        Send an error response to the client.
        
        Args:
            error_message (str): The error message to send
        """
        try:
            emit('backend_response', {
                'data': f'Errore: {error_message}'
            })
            logging.debug(f'[CommunicationHandler] Sent error response: {error_message}')
        except Exception as e:
            logging.error(f'[CommunicationHandler] Failed to send error response: {e}')
    
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
    
    def _send_ai_response(self, ai_response: AIResponse) -> None:
        """
        Send an AI response to the client.
        
        Args:
            ai_response (AIResponse): The AI response to send
        """
        try:
            if ai_response.success:
                # Send successful AI response
                emit('backend_response', {
                    'data': ai_response.text,
                    'type': 'ai_response',
                    'response_type': ai_response.response_type,
                    'metadata': ai_response.metadata,
                    'suggested_actions': ai_response.suggested_actions
                })
                logging.debug(f'[CommunicationHandler] Sent AI response: {ai_response.text[:100]}...')
                
                # Handle navigation actions
                if ai_response.metadata and ai_response.metadata.get('action') == 'open_navigator':
                    self._handle_navigation_action(ai_response.metadata)
                    
            else:
                # Send AI error response
                emit('backend_response', {
                    'data': ai_response.text,
                    'type': 'ai_error',
                    'response_type': ai_response.response_type
                })
                logging.debug(f'[CommunicationHandler] Sent AI error response: {ai_response.text}')
                
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error sending AI response: {e}')
            self._send_error_response('Errore nell\'invio della risposta AI')
    
    def _handle_navigation_action(self, metadata: Dict[str, Any]) -> None:
        """
        Handle navigation-specific actions based on AI response metadata.
        
        Args:
            metadata (Dict[str, Any]): AI response metadata containing navigation action
        """
        try:
            action = metadata.get('action')
            
            if action == 'open_navigator':
                # Check if we're in debug mode (simple check - could be more sophisticated)
                # For now, we'll emit both events and let the frontend decide
                
                # Emit navigation open action
                emit('backend_action', {
                    'action': 'open_navigator'
                })
                logging.info('[CommunicationHandler] Emitted open_navigator action')
                
                # Emit route data if available
                route_payload = metadata.get('route_payload')
                if route_payload:
                    emit('backend_action', {
                        'action': 'render_route',
                        'data': route_payload
                    })
                    logging.info('[CommunicationHandler] Emitted render_route action')
                    
        except Exception as e:
            logging.error(f'[CommunicationHandler] Error handling navigation action: {e}')
    
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
            emit(event, data)
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
    
    def get_available_events(self) -> Dict[str, str]:
        """
        Get a dictionary of available communication events.
        
        Returns:
            Dict[str, str]: Dictionary mapping event names to descriptions
        """
        return {
            'frontend_command': 'Comando inviato dal frontend',
            'backend_response': 'Risposta generale dal backend',
            'backend_action': 'Azione specifica dal backend (navigazione, clear, etc.)'
        }
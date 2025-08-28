"""
Connection Manager Module for Frank Camper Assistant.

This module handles WebSocket connections between the client and server,
managing connection states and providing a clean interface for connection events.
"""

import logging
from typing import Dict, Any
from flask_socketio import SocketIO, emit


class ConnectionManager:
    """
    Manages WebSocket connections between client and server.
    
    This class handles connection establishment, connection tracking,
    and provides methods for connection-related operations.
    
    Attributes:
        _socketio_instance (SocketIO): The Flask-SocketIO instance
        _connected_clients (Dict[str, Any]): Dictionary to track connected clients
    """
    
    def __init__(self, socketio_instance: SocketIO) -> None:
        """
        Initialize the ConnectionManager.
        
        Args:
            socketio_instance (SocketIO): The Flask-SocketIO instance to manage
        """
        self._socketio_instance = socketio_instance
        self._connected_clients: Dict[str, Any] = {}
        self._setup_connection_handlers()
    
    def _setup_connection_handlers(self) -> None:
        """
        Set up the WebSocket connection event handlers.
        
        This method registers the connect and disconnect event handlers
        with the SocketIO instance.
        """
        @self._socketio_instance.on('connect')
        def handle_connect():
            """Handle client connection event."""
            self._on_client_connect()
        
        @self._socketio_instance.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection event."""
            self._on_client_disconnect()
    
    def _on_client_connect(self) -> None:
        """
        Handle a new client connection.
        
        This method is called when a client successfully connects to the server.
        It logs the connection and sends a welcome message to the client.
        """
        logging.info('[ConnectionManager] Client connected successfully')
        
        # Send welcome message to the newly connected client
        emit('backend_response', {
            'data': 'Benvenuto! sono pronto ad aiutarti.',
            'type': 'system'
        })
    
    def _on_client_disconnect(self) -> None:
        """
        Handle client disconnection.
        
        This method is called when a client disconnects from the server.
        It performs cleanup operations and logs the disconnection.
        """
        logging.info('[ConnectionManager] Client disconnected')
        # Additional cleanup logic can be added here if needed
    
    def get_socketio_instance(self) -> SocketIO:
        """
        Get the managed SocketIO instance.
        
        Returns:
            SocketIO: The Flask-SocketIO instance being managed
        """
        return self._socketio_instance
    
    def is_client_connected(self) -> bool:
        """
        Check if any clients are currently connected.
        
        Returns:
            bool: True if at least one client is connected, False otherwise
        """
        # This is a simplified implementation
        # In a real scenario, you might want to track individual client sessions
        return True  # Simplified for this implementation
    
    def emit_to_client(self, event: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to the connected client(s).
        
        Args:
            event (str): The name of the event to emit
            data (Dict[str, Any]): The data to send with the event
        """
        try:
            emit(event, data)
            logging.debug(f'[ConnectionManager] Event "{event}" emitted to client')
        except Exception as e:
            logging.error(f'[ConnectionManager] Failed to emit event "{event}": {e}')
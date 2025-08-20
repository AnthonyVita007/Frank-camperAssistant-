"""
Main Controller Module for Frank Camper Assistant.

This module contains the main controller that orchestrates all backend components,
providing a clean and organized entry point for the application's core functionality.
"""

import logging
from flask_socketio import SocketIO

from .connection_manager import ConnectionManager
from .command_processor import CommandProcessor  
from .communication_handler import CommunicationHandler


class MainController:
    """
    Main controller that orchestrates all backend components.
    
    This class serves as the central coordinator for the Frank Camper Assistant
    backend system. It initializes and manages all core components:
    - Connection management
    - Command processing
    - Communication handling
    
    The controller follows the Single Responsibility Principle by delegating
    specific tasks to specialized components while maintaining overall coordination.
    
    Attributes:
        _socketio_instance (SocketIO): The Flask-SocketIO instance
        _connection_manager (ConnectionManager): Manages WebSocket connections
        _command_processor (CommandProcessor): Processes user commands
        _communication_handler (CommunicationHandler): Handles client-server communication
    """
    
    def __init__(self, socketio_instance: SocketIO) -> None:
        """
        Initialize the MainController.
        
        This method sets up all the core components and establishes the
        connections between them to create a fully functional backend system.
        
        Args:
            socketio_instance (SocketIO): The Flask-SocketIO instance to manage
        """
        self._socketio_instance = socketio_instance
        
        # Initialize core components
        self._initialize_components()
        
        logging.info('[MainController] Main controller initialized successfully')
        logging.info('[MainController] Available commands: /clear, /debugmode, /usermode')
    
    def _initialize_components(self) -> None:
        """
        Initialize all core backend components.
        
        This method creates instances of all required components and
        sets up their interconnections. The order of initialization
        is important to ensure proper dependency resolution.
        """
        try:
            # Initialize command processor (no dependencies)
            self._command_processor = CommandProcessor()
            logging.debug('[MainController] Command processor initialized')
            
            # Initialize connection manager (depends on SocketIO)
            self._connection_manager = ConnectionManager(self._socketio_instance)
            logging.debug('[MainController] Connection manager initialized')
            
            # Initialize communication handler (depends on SocketIO and CommandProcessor)
            self._communication_handler = CommunicationHandler(
                self._socketio_instance, 
                self._command_processor
            )
            logging.debug('[MainController] Communication handler initialized')
            
        except Exception as e:
            logging.error(f'[MainController] Failed to initialize components: {e}')
            raise
    
    def get_connection_manager(self) -> ConnectionManager:
        """
        Get the connection manager instance.
        
        Returns:
            ConnectionManager: The connection manager managing WebSocket connections
        """
        return self._connection_manager
    
    def get_command_processor(self) -> CommandProcessor:
        """
        Get the command processor instance.
        
        Returns:
            CommandProcessor: The command processor handling user commands
        """
        return self._command_processor
    
    def get_communication_handler(self) -> CommunicationHandler:
        """
        Get the communication handler instance.
        
        Returns:
            CommunicationHandler: The communication handler managing client-server communication
        """
        return self._communication_handler
    
    def get_system_status(self) -> dict:
        """
        Get the current status of all system components.
        
        Returns:
            dict: Dictionary containing status information for all components
        """
        try:
            status = {
                'controller_status': 'active',
                'connection_manager': {
                    'status': 'active',
                    'clients_connected': self._connection_manager.is_client_connected()
                },
                'command_processor': {
                    'status': 'active',
                    'available_commands': list(self._command_processor.get_available_commands().keys())
                },
                'communication_handler': {
                    'status': 'active',
                    'available_events': list(self._communication_handler.get_available_events().keys())
                }
            }
            return status
        except Exception as e:
            logging.error(f'[MainController] Error getting system status: {e}')
            return {'error': str(e)}
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown the main controller and all its components.
        
        This method performs cleanup operations for all components
        before the application terminates.
        """
        try:
            logging.info('[MainController] Shutting down main controller...')
            
            # Additional cleanup operations can be added here for each component
            # For now, we just log the shutdown
            
            logging.info('[MainController] Main controller shutdown completed')
            
        except Exception as e:
            logging.error(f'[MainController] Error during shutdown: {e}')
    
    def restart_components(self) -> bool:
        """
        Restart all backend components.
        
        This method can be used to reinitialize components if needed
        during runtime (useful for error recovery scenarios).
        
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            logging.info('[MainController] Restarting backend components...')
            
            # Reinitialize all components
            self._initialize_components()
            
            logging.info('[MainController] Components restarted successfully')
            return True
            
        except Exception as e:
            logging.error(f'[MainController] Failed to restart components: {e}')
            return False


def setup_socketio_events(socketio_instance: SocketIO) -> MainController:
    """
    Set up SocketIO events using the new OOP architecture.
    
    This function serves as the entry point for initializing the backend
    system with the new Object-Oriented architecture. It replaces the
    previous procedural setup_socketio_events function.
    
    Args:
        socketio_instance (SocketIO): The Flask-SocketIO instance from app.py
        
    Returns:
        MainController: The initialized main controller instance
    """
    try:
        # Create and initialize the main controller
        controller = MainController(socketio_instance)
        
        logging.info('[Setup] Frank Camper Assistant backend initialized with OOP architecture')
        logging.info('[Setup] System ready to handle /clear, /debugmode, and /usermode commands')
        
        return controller
        
    except Exception as e:
        logging.error(f'[Setup] Failed to initialize backend system: {e}')
        raise
"""
Main Controller Module for Frank Camper Assistant.

This module contains the main controller that orchestrates all backend components,
providing a clean and organized entry point for the application's core functionality.
"""

#----------------------------------------------------------------
# IMPORT E DIPENDENZE
#----------------------------------------------------------------
import logging
from flask_socketio import SocketIO

from .connection_manager import ConnectionManager
from .command_processor import CommandProcessor  
from .communication_handler import CommunicationHandler
from ..ai.ai_handler import AIHandler


class MainController:
    """
    Main controller that orchestrates all backend components.
    
    This class serves as the central coordinator for the Frank Camper Assistant
    backend system. It initializes and manages all core components:
    - Connection management
    - Command processing
    - AI request handling with MCP tool integration
    - Communication handling
    
    The controller follows the Single Responsibility Principle by delegating
    specific tasks to specialized components while maintaining overall coordination.
    
    Attributes:
        _socketio_instance (SocketIO): The Flask-SocketIO instance
        _connection_manager (ConnectionManager): Manages WebSocket connections
        _command_processor (CommandProcessor): Processes user commands
        _ai_handler (AIHandler): Handles AI requests with MCP integration
        _communication_handler (CommunicationHandler): Handles client-server communication
        _mcp_handler (Optional): MCP handler for tool-based interactions
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE CONTROLLER CON SUPPORTO MCP
    #----------------------------------------------------------------
    def __init__(self, socketio_instance: SocketIO) -> None:
        """
        Initialize the MainController with MCP support.
        
        This method sets up all the core components and establishes the
        connections between them to create a fully functional backend system
        with MCP tool integration capabilities.
        
        Args:
            socketio_instance (SocketIO): The Flask-SocketIO instance to manage
        """
        self._socketio_instance = socketio_instance
        self._mcp_handler = None
        
        # Initialize core components with MCP integration
        self._initialize_components()
        
        logging.info('[MainController] Main controller initialized successfully with MCP support')
        logging.info('[MainController] Available commands: /clear, /debugmode, /usermode')
        
        # Log MCP status
        if self._mcp_handler:
            logging.info('[MainController] MCP tool system enabled and ready')
        else:
            logging.info('[MainController] MCP tool system disabled (no tools available)')
    
    def _initialize_components(self) -> None:
        """
        Initialize all core backend components with MCP integration.
        
        This method creates instances of all required components and
        sets up their interconnections. The order of initialization
        is important to ensure proper dependency resolution.
        """
        try:
            #----------------------------------------------------------------
            # INIZIALIZZAZIONE SISTEMA MCP
            #----------------------------------------------------------------
            # Initialize MCP system first (optional dependency)
            self._mcp_handler = self._initialize_mcp_system()
            
            #----------------------------------------------------------------
            # INIZIALIZZAZIONE COMPONENTI CORE
            #----------------------------------------------------------------
            # Initialize command processor (no dependencies)
            self._command_processor = CommandProcessor()
            logging.debug('[MainController] Command processor initialized')
            
            # Initialize AI handler with MCP integration (depends on MCP handler)
            self._ai_handler = AIHandler(mcp_handler=self._mcp_handler)
            logging.debug('[MainController] AI handler initialized with MCP support')
            
            # Initialize connection manager (depends on SocketIO)
            self._connection_manager = ConnectionManager(self._socketio_instance)
            logging.debug('[MainController] Connection manager initialized')
            
            # Initialize communication handler (depends on SocketIO, CommandProcessor, and AIHandler)
            self._communication_handler = CommunicationHandler(
                self._socketio_instance, 
                self._command_processor,
                self._ai_handler
            )
            logging.debug('[MainController] Communication handler initialized')
            
            #----------------------------------------------------------------
            # REGISTRAZIONE TOOL MCP DI ESEMPIO
            #----------------------------------------------------------------
            # Register sample tools if MCP is available
            if self._mcp_handler:
                self._register_sample_tools()
            
            # Note: AI warmup removed from automatic startup to avoid test prompts
            # Warmup will happen on demand when providers are first used
            
        except Exception as e:
            logging.error(f'[MainController] Failed to initialize components: {e}')
            raise
    
    def _initialize_mcp_system(self):
        """
        Initialize the MCP (Model Context Protocol) system.
        
        This method sets up the MCP infrastructure for tool-based interactions,
        creating the necessary handlers and registries.
        
        Returns:
            Optional: MCP handler if successful, None if MCP is not available
        """
        try:
            #----------------------------------------------------------------
            # IMPORT DINAMICO MODULI MCP
            #----------------------------------------------------------------
            # Dynamic import to handle cases where MCP modules might not be available
            from ..mcp.mcp_handler import MCPHandler
            from ..mcp.tool_registry import ToolRegistry
            
            # Create tool registry
            tool_registry = ToolRegistry()
            logging.debug('[MainController] MCP tool registry created')
            
            # Create MCP handler
            mcp_handler = MCPHandler(tool_registry)
            logging.debug('[MainController] MCP handler created')
            
            # Validate MCP system
            validation_result = mcp_handler.validate_system()
            if validation_result['overall_status'] in ['healthy', 'degraded']:
                logging.info('[MainController] MCP system initialized successfully')
                return mcp_handler
            else:
                logging.warning(f'[MainController] MCP system validation failed: {validation_result["overall_status"]}')
                return None
                
        except ImportError as e:
            logging.warning(f'[MainController] MCP modules not available: {e}')
            return None
        except Exception as e:
            logging.error(f'[MainController] Failed to initialize MCP system: {e}')
            return None
    
    def _register_sample_tools(self) -> None:
        """
        Register sample MCP tools for testing and demonstration.
        
        This method creates and registers basic tools that demonstrate
        the MCP system capabilities.
        """
        try:
            #----------------------------------------------------------------
            # IMPORT TOOL DI ESEMPIO
            #----------------------------------------------------------------
            from ..mcp.mcp_tool import MCPTool, ToolResult, ToolResultStatus
            
            #----------------------------------------------------------------
            # TOOL NAVIGAZIONE SEMPLICE
            #----------------------------------------------------------------
            class SampleNavigationTool(MCPTool):
                def __init__(self):
                    super().__init__(
                        name="set_route_sample",
                        description="Imposta una rotta di navigazione (simulazione)",
                        category="navigation"
                    )
                
                @property
                def parameters_schema(self):
                    return {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "description": "Destinazione del viaggio"
                            },
                            "preferences": {
                                "type": "object",
                                "properties": {
                                    "avoid_tolls": {"type": "boolean"},
                                    "avoid_highways": {"type": "boolean"}
                                }
                            }
                        },
                        "required": ["destination"]
                    }
                
                def execute(self, parameters):
                    destination = parameters.get('destination', 'destinazione sconosciuta')
                    preferences = parameters.get('preferences', {})
                    
                    response_parts = [f"Rotta impostata per: {destination}"]
                    
                    if preferences.get('avoid_tolls'):
                        response_parts.append("Evitando pedaggi")
                    if preferences.get('avoid_highways'):
                        response_parts.append("Evitando autostrade")
                    
                    response_text = ". ".join(response_parts) + "."
                    
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        data=response_text,
                        message="Navigazione configurata con successo"
                    )
            
            #----------------------------------------------------------------
            # TOOL METEO SEMPLICE
            #----------------------------------------------------------------
            class SampleWeatherTool(MCPTool):
                def __init__(self):
                    super().__init__(
                        name="get_weather_sample",
                        description="Recupera informazioni meteo (simulazione)",
                        category="weather"
                    )
                
                @property
                def parameters_schema(self):
                    return {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Località per le previsioni meteo"
                            }
                        },
                        "required": ["location"]
                    }
                
                def execute(self, parameters):
                    location = parameters.get('location', 'posizione attuale')
                    
                    # Simulazione dati meteo
                    weather_conditions = ["Soleggiato", "Nuvoloso", "Pioggia leggera", "Sereno"]
                    import random
                    condition = random.choice(weather_conditions)
                    temp = random.randint(15, 30)
                    
                    response_text = f"Meteo per {location}: {condition}, {temp}°C"
                    
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        data=response_text,
                        message="Informazioni meteo recuperate"
                    )
            
            #----------------------------------------------------------------
            # TOOL STATO VEICOLO SEMPLICE
            #----------------------------------------------------------------
            class SampleVehicleTool(MCPTool):
                def __init__(self):
                    super().__init__(
                        name="get_vehicle_status_sample",
                        description="Recupera stato del veicolo (simulazione)",
                        category="vehicle"
                    )
                
                @property
                def parameters_schema(self):
                    return {
                        "type": "object",
                        "properties": {
                            "system": {
                                "type": "string",
                                "description": "Sistema specifico da controllare",
                                "enum": ["general", "fuel", "engine", "tires"]
                            }
                        }
                    }
                
                def execute(self, parameters):
                    system = parameters.get('system', 'general')
                    
                    # Simulazione dati veicolo
                    if system == 'fuel':
                        response_text = "Livello carburante: 75% (circa 350 km di autonomia)"
                    elif system == 'engine':
                        response_text = "Motore: Temperatura normale, Pressione olio OK"
                    elif system == 'tires':
                        response_text = "Pneumatici: Pressioni normali (2.2 bar)"
                    else:
                        response_text = "Stato generale: Tutto OK. Carburante 75%, Motore normale, Pneumatici OK"
                    
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        data=response_text,
                        message="Status veicolo recuperato"
                    )
            
            #----------------------------------------------------------------
            # REGISTRAZIONE TOOL NEL SISTEMA MCP
            #----------------------------------------------------------------
            # Register the tools
            navigation_tool = SampleNavigationTool()
            weather_tool = SampleWeatherTool()
            vehicle_tool = SampleVehicleTool()
            
            if self._mcp_handler.register_tool(navigation_tool):
                logging.info('[MainController] Sample navigation tool registered')
            
            if self._mcp_handler.register_tool(weather_tool):
                logging.info('[MainController] Sample weather tool registered')
            
            if self._mcp_handler.register_tool(vehicle_tool):
                logging.info('[MainController] Sample vehicle tool registered')
            
            # Log available tools
            available_tools = self._mcp_handler.get_available_tools()
            tool_names = [tool['name'] for tool in available_tools]
            logging.info(f'[MainController] MCP tools available: {tool_names}')
            
        except Exception as e:
            logging.error(f'[MainController] Failed to register sample tools: {e}')
    
    #----------------------------------------------------------------
    # GETTER COMPONENTI (ESISTENTI)
    #----------------------------------------------------------------
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
    
    def get_ai_handler(self) -> AIHandler:
        """
        Get the AI handler instance.
        
        Returns:
            AIHandler: The AI handler managing AI requests with MCP integration
        """
        return self._ai_handler
    
    def get_mcp_handler(self):
        """
        Get the MCP handler instance.
        
        Returns:
            Optional: The MCP handler managing tool-based interactions, or None if not available
        """
        return self._mcp_handler
    
    #----------------------------------------------------------------
    # STATUS E DIAGNOSTICHE SISTEMA
    #----------------------------------------------------------------
    def get_system_status(self) -> dict:
        """
        Get the current status of all system components including MCP.
        
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
                'ai_handler': self._ai_handler.get_ai_status(),
                'communication_handler': {
                    'status': 'active',
                    'available_events': list(self._communication_handler.get_available_events().keys())
                }
            }
            
            # Add MCP status if available
            if self._mcp_handler:
                status['mcp_system'] = self._mcp_handler.get_system_status()
            else:
                status['mcp_system'] = {
                    'mcp_enabled': False,
                    'message': 'MCP system not available'
                }
            
            return status
        except Exception as e:
            logging.error(f'[MainController] Error getting system status: {e}')
            return {'error': str(e)}
    
    def get_mcp_status(self) -> dict:
        """
        Get detailed MCP system status and tool information.
        
        Returns:
            dict: Detailed MCP system information
        """
        if not self._mcp_handler:
            return {
                'enabled': False,
                'message': 'MCP system not available',
                'tools': [],
                'categories': []
            }
        
        try:
            return {
                'enabled': True,
                'system_status': self._mcp_handler.get_system_status(),
                'validation': self._mcp_handler.validate_system(),
                'tools': self._mcp_handler.get_available_tools(),
                'categories': self._mcp_handler.get_categories()
            }
        except Exception as e:
            logging.error(f'[MainController] Error getting MCP status: {e}')
            return {
                'enabled': False,
                'error': str(e),
                'message': 'Error retrieving MCP status'
            }
    
    #----------------------------------------------------------------
    # SHUTDOWN E RESTART (AGGIORNATI)
    #----------------------------------------------------------------
    def shutdown(self) -> None:
        """
        Gracefully shutdown the main controller and all its components.
        
        This method performs cleanup operations for all components
        including the MCP system before the application terminates.
        """
        try:
            logging.info('[MainController] Shutting down main controller...')
            
            # Shutdown MCP handler if available
            if self._mcp_handler:
                try:
                    self._mcp_handler.shutdown()
                    logging.debug('[MainController] MCP handler shutdown completed')
                except Exception as e:
                    logging.error(f'[MainController] Error shutting down MCP handler: {e}')
            
            # Shutdown AI handler
            if self._ai_handler:
                try:
                    self._ai_handler.shutdown()
                    logging.debug('[MainController] AI handler shutdown completed')
                except Exception as e:
                    logging.error(f'[MainController] Error shutting down AI handler: {e}')
            
            logging.info('[MainController] Main controller shutdown completed')
            
        except Exception as e:
            logging.error(f'[MainController] Error during shutdown: {e}')
    
    def restart_components(self) -> bool:
        """
        Restart all backend components including MCP system.
        
        This method can be used to reinitialize components if needed
        during runtime (useful for error recovery scenarios).
        
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            logging.info('[MainController] Restarting backend components...')
            
            # Shutdown existing components
            self.shutdown()
            
            # Reinitialize all components
            self._initialize_components()
            
            logging.info('[MainController] Components restarted successfully')
            return True
            
        except Exception as e:
            logging.error(f'[MainController] Failed to restart components: {e}')
            return False
    
    #----------------------------------------------------------------
    # AI WARMUP FUNCTIONALITY (ESISTENTE)
    #----------------------------------------------------------------
    def _perform_ai_warmup(self) -> None:
        """
        Perform AI model warmup in a background task.
        
        This method safely performs AI model warmup without blocking
        the main application startup process.
        """
        try:
            logging.info('[MainController] AI warmup task started')
            
            # Get AI processor for warmup
            if (self._ai_handler and 
                self._ai_handler.is_ai_enabled() and 
                hasattr(self._ai_handler, '_ai_processor') and
                self._ai_handler._ai_processor):
                
                # Perform warmup
                warmup_success = self._ai_handler._ai_processor.warmup()
                
                if warmup_success:
                    logging.info('[MainController] AI model warmup completed successfully')
                else:
                    logging.warning('[MainController] AI model warmup failed, but system will continue')
            else:
                logging.warning('[MainController] AI processor not available for warmup')
                
        except Exception as e:
            logging.error(f'[MainController] Error during AI warmup: {e}')
            # Continue anyway - warmup failure should not prevent system operation


#----------------------------------------------------------------
# FUNZIONE SETUP (AGGIORNATA)
#----------------------------------------------------------------
def setup_socketio_events(socketio_instance: SocketIO) -> MainController:
    """
    Set up SocketIO events using the new OOP architecture with MCP support.
    
    This function serves as the entry point for initializing the backend
    system with the new Object-Oriented architecture and MCP integration.
    It replaces the previous procedural setup_socketio_events function.
    
    Args:
        socketio_instance (SocketIO): The Flask-SocketIO instance from app.py
        
    Returns:
        MainController: The initialized main controller instance with MCP support
    """
    try:
        # Create and initialize the main controller with MCP support
        controller = MainController(socketio_instance)
        
        logging.info('[Setup] Frank Camper Assistant backend initialized with OOP architecture and MCP support')
        logging.info('[Setup] System ready to handle /clear, /debugmode, and /usermode commands')
        
        # Log MCP initialization status
        mcp_status = controller.get_mcp_status()
        if mcp_status['enabled']:
            tool_count = len(mcp_status.get('tools', []))
            logging.info(f'[Setup] MCP system ready with {tool_count} tools available')
        else:
            logging.info('[Setup] MCP system not available - running in basic mode')
        
        return controller
        
    except Exception as e:
        logging.error(f'[Setup] Failed to initialize backend system: {e}')
        raise
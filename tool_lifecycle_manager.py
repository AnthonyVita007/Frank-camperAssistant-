"""
Tool Lifecycle Manager Module for Frank Camper Assistant.

This module implements the ToolLifecycleManager class, a delegated agent
responsible for handling tool parameter collection in isolation.
The manager runs its own sub-conversation with Gemini to collect missing
parameters and returns structured results to the main conversation handler.
"""

import logging
import time
from typing import Dict, Any, Optional, List

# Import Gemini API
try:
    import google.generativeai as genai
    import os
    GEMINI_AVAILABLE = True
    
    # Configure Gemini API
    api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
    else:
        GEMINI_AVAILABLE = False
        logging.warning('[ToolLifecycleManager] GOOGLE_GEMINI_API_KEY not found')
        
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning('[ToolLifecycleManager] google.generativeai not available')

# Import tool functions that might be used
try:
    from backend.core.main_controller import SampleWeatherTool, SampleNavigationTool, SampleVehicleTool
except ImportError:
    # Define sample tool functions for compatibility
    def get_weather_sample(location: str = None, forecast: str = None) -> str:
        """Sample weather tool function"""
        if not location:
            return "Errore: location non specificata"
        return f"Meteo per {location}: {forecast or 'Soleggiato'}, 22°C"
    
    def set_route_sample(destination: str = None, preferences: Dict = None) -> str:
        """Sample navigation tool function"""
        if not destination:
            return "Errore: destinazione non specificata"
        return f"Rotta impostata per: {destination}"
    
    def get_vehicle_status_sample(system: str = "general") -> str:
        """Sample vehicle status tool function"""
        return f"Stato veicolo ({system}): Tutto OK"


class ToolLifecycleManager:
    """
    Delegated agent responsible for handling tool parameter collection.
    
    This class implements the delegation pattern where the main conversation
    handler delegates tool parameter collection to this specialized manager.
    The manager runs its own sub-conversation with Gemini to collect missing
    parameters and returns structured results.
    
    Attributes:
        function_name (str): Name of the tool/function to execute
        initial_args (Dict[str, Any]): Already known parameters
        model: Gemini model instance for sub-conversation
        sub_chat: Gemini chat session for parameter collection
    """
    
    def __init__(self, function_name: str, initial_args: Dict[str, Any]):
        """
        Initialize the ToolLifecycleManager.
        
        Args:
            function_name (str): Name of the tool/function to execute
            initial_args (Dict[str, Any]): Already known parameters
        """
        self.function_name = function_name
        self.initial_args = initial_args.copy()
        self.model = None
        self.sub_chat = None
        
        # Tool parameter schemas
        self.tool_schemas = {
            'get_weather_sample': {
                'required': ['location'],
                'optional': ['forecast'],
                'questions': {
                    'location': 'Per quale città vuoi conoscere il meteo?'
                }
            },
            'set_route_sample': {
                'required': ['destination'],
                'optional': ['preferences'],
                'questions': {
                    'destination': 'Dove vuoi andare? Specifica la destinazione.'
                }
            },
            'get_vehicle_status_sample': {
                'required': [],
                'optional': ['system'],
                'questions': {
                    'system': 'Quale sistema vuoi controllare? (general, fuel, engine, tires)'
                }
            }
        }
        
        logging.info(f'[ToolLifecycleManager] Initialized for function: {function_name}')
        logging.debug(f'[ToolLifecycleManager] Initial args: {initial_args}')
    
    def run(self) -> Dict[str, Any]:
        """
        Run the tool lifecycle management process.
        
        This method implements the main lifecycle flow:
        1. Initialize Gemini model and chat session
        2. Identify missing required parameters
        3. Enter parameter collection loop
        4. Handle user input (parameter values or cancellation)
        5. Execute tool when all parameters are collected
        6. Return structured result
        
        Returns:
            Dict[str, Any]: Structured result with status and data
                - {'status': 'completed', 'name': function_name, 'response': tool_response}
                - {'status': 'cancelled'}
                - {'status': 'error', 'error': error_message}
        """
        try:
            # Check if Gemini is available
            if not GEMINI_AVAILABLE:
                logging.error('[ToolLifecycleManager] Gemini API not available')
                return {'status': 'error', 'error': 'Gemini API not available'}
            
            # Initialize Gemini model
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                system_instruction=(
                    "Sei un assistente specializzato nella raccolta di parametri per strumenti. "
                    "Il tuo compito è aiutare l'utente a fornire i parametri mancanti richiesti "
                    "per l'esecuzione di uno strumento specifico. Sii conciso e diretto."
                )
            )
            
            # Start sub-conversation
            self.sub_chat = self.model.start_chat()
            
            # Get tool schema
            schema = self.tool_schemas.get(self.function_name, {})
            required_params = schema.get('required', [])
            questions = schema.get('questions', {})
            
            # Identify missing required parameters
            missing_params = []
            for param in required_params:
                if param not in self.initial_args or not self.initial_args[param]:
                    missing_params.append(param)
            
            # If no parameters are missing, execute directly
            if not missing_params:
                logging.info(f'[ToolLifecycleManager] All parameters available, executing {self.function_name}')
                return self._execute_tool()
            
            # Enter parameter collection loop
            current_params = self.initial_args.copy()
            
            while missing_params:
                # Get the next missing parameter
                param_name = missing_params[0]
                question = questions.get(param_name, f"Fornisci il valore per {param_name}:")
                
                # Ask for the parameter
                try:
                    # Send question to sub-chat (for context)
                    self.sub_chat.send_message(f"Sto raccogliendo il parametro '{param_name}' per lo strumento '{self.function_name}'. Domanda: {question}")
                except Exception as e:
                    logging.warning(f'[ToolLifecycleManager] Error sending to sub-chat: {e}')
                
                # Ask user directly
                print(f"{question}")
                
                # Get user input
                user_input = input("> ").strip()
                
                # Check for cancellation
                if user_input.lower() in ['annulla', 'cancella', 'stop', 'exit', 'quit']:
                    logging.info('[ToolLifecycleManager] Tool execution cancelled by user')
                    return {'status': 'cancelled'}
                
                # If user provided a value, use it
                if user_input:
                    current_params[param_name] = user_input
                    missing_params.remove(param_name)
                    logging.debug(f'[ToolLifecycleManager] Parameter {param_name} set to: {user_input}')
                else:
                    print(f"Per favore fornisci un valore per {param_name} o digita 'annulla' per interrompere.")
            
            # All parameters collected, execute tool
            logging.info(f'[ToolLifecycleManager] All parameters collected for {self.function_name}: {current_params}')
            return self._execute_tool(current_params)
            
        except Exception as e:
            logging.error(f'[ToolLifecycleManager] Error in run(): {e}')
            return {'status': 'error', 'error': str(e)}
    
    def _execute_tool(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the tool with the collected parameters.
        
        Args:
            parameters (Optional[Dict[str, Any]]): Parameters to use, defaults to initial_args
            
        Returns:
            Dict[str, Any]: Execution result
        """
        try:
            params = parameters or self.initial_args
            
            # Map function names to actual functions
            tool_functions = {
                'get_weather_sample': get_weather_sample,
                'set_route_sample': set_route_sample,
                'get_vehicle_status_sample': get_vehicle_status_sample
            }
            
            if self.function_name not in tool_functions:
                error_msg = f"Unknown function: {self.function_name}"
                logging.error(f'[ToolLifecycleManager] {error_msg}')
                return {'status': 'error', 'error': error_msg}
            
            # Execute the function
            function = tool_functions[self.function_name]
            result = function(**params)
            
            logging.info(f'[ToolLifecycleManager] Tool {self.function_name} executed successfully')
            logging.debug(f'[ToolLifecycleManager] Tool result: {result}')
            
            return {
                'status': 'completed',
                'name': self.function_name,
                'response': result
            }
            
        except Exception as e:
            error_msg = f"Error executing {self.function_name}: {str(e)}"
            logging.error(f'[ToolLifecycleManager] {error_msg}')
            return {'status': 'error', 'error': error_msg}
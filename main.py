"""
Main conversation handler for Frank Camper Assistant.

This module implements the main conversation loop using Google Gemini API
with function calling capabilities. It serves as the "Router" in the delegation
pattern, detecting tool calls and delegating parameter collection to the
ToolLifecycleManager when needed.
"""

import logging
import os
from typing import Dict, Any, Optional

# Import Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    
    # Configure Gemini API
    api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
    else:
        GEMINI_AVAILABLE = False
        logging.warning('[Main] GOOGLE_GEMINI_API_KEY not found')
        
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning('[Main] google.generativeai not available')

# Import the ToolLifecycleManager
from tool_lifecycle_manager import ToolLifecycleManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global chat instance
chat = None

def initialize_conversation():
    """Initialize the Gemini conversation with function calling capabilities."""
    global chat
    
    if not GEMINI_AVAILABLE:
        logging.error('[Main] Cannot initialize conversation: Gemini API not available')
        return False
    
    try:
        # Define the available functions for Gemini
        function_declarations = [
            {
                "name": "get_weather_sample",
                "description": "Recupera informazioni meteo per una località specifica",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "La località per cui ottenere le previsioni meteo"
                        },
                        "forecast": {
                            "type": "string",
                            "description": "Tipo di previsione richiesta (opzionale)"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "set_route_sample",
                "description": "Imposta una rotta di navigazione",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "destination": {
                            "type": "string",
                            "description": "La destinazione del viaggio"
                        },
                        "preferences": {
                            "type": "object",
                            "description": "Preferenze di navigazione (opzionale)"
                        }
                    },
                    "required": ["destination"]
                }
            },
            {
                "name": "get_vehicle_status_sample",
                "description": "Recupera lo stato del veicolo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "system": {
                            "type": "string",
                            "description": "Sistema specifico da controllare"
                        }
                    }
                }
            }
        ]
        
        # Create the model with function declarations
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            tools=[{"function_declarations": function_declarations}],
            system_instruction=(
                "Sei Frank, l'assistente AI del camper. Puoi aiutare con meteo, navigazione e stato del veicolo. "
                "Usa le funzioni disponibili quando necessario per rispondere alle richieste dell'utente."
            )
        )
        
        # Start the chat
        chat = model.start_chat()
        
        logging.info('[Main] Conversation initialized successfully')
        return True
        
    except Exception as e:
        logging.error(f'[Main] Error initializing conversation: {e}')
        return False

def run_conversation():
    """
    Main conversation loop implementing the delegation pattern.
    
    This function serves as the "Router" - it processes user input, detects
    function calls, and delegates parameter collection to ToolLifecycleManager
    when needed. It handles the complete flow described in the problem statement.
    """
    global chat
    
    if not chat:
        if not initialize_conversation():
            print("Errore: Impossibile inizializzare la conversazione con Gemini.")
            return
    
    print("Frank Camper Assistant attivo! Digita 'exit' per uscire.")
    print("Esempi: 'Che tempo fa?', 'Imposta la rotta', 'Come sta il camper?'")
    
    while True:
        try:
            # Get user input
            user_input = input("\n> ").strip()
            
            # Check for exit
            if user_input.lower() in ['exit', 'quit', 'esci']:
                print("Arrivederci!")
                break
            
            if not user_input:
                continue
            
            # Send message to Gemini
            response = chat.send_message(user_input, stream=True)
            
            # Process response chunks
            for chunk in response:
                # Check if this chunk contains a function call
                if hasattr(chunk, 'function_call') and chunk.function_call:
                    function_call = chunk.function_call
                    function_name = function_call.name
                    args = dict(function_call.args) if function_call.args else {}
                    
                    logging.info(f'[Main] Function call detected: {function_name} with args: {args}')
                    
                    # Check if required parameters are missing based on function definition
                    missing_params = _check_missing_parameters(function_name, args)
                    
                    if missing_params:
                        # Parameters are missing - delegate to ToolLifecycleManager
                        print(f"\033[91m[LLM principale] -> passa i comandi a -> [ToolLifecycleManager]\033[0m")
                        
                        # Create and run the manager
                        manager = ToolLifecycleManager(function_name=function_name, initial_args=args)
                        result = manager.run()
                        
                        print(f"\033[91m[ToolLifecycleManager] -> passa i comandi a -> [LLM principale]\033[0m")
                        
                        # Handle the result
                        if result['status'] == 'completed':
                            # Send the function response back to Gemini for final response
                            function_response = {
                                'name': result['name'],
                                'response': result['response']
                            }
                            
                            # Send tool result to chat for final response
                            final_response = chat.send_message(
                                f"Risultato della funzione {result['name']}: {result['response']}. "
                                "Fornisci una risposta amichevole all'utente."
                            )
                            
                            # Print the final response
                            for final_chunk in final_response:
                                if hasattr(final_chunk, 'text') and final_chunk.text:
                                    print(final_chunk.text, end='', flush=True)
                        
                        elif result['status'] == 'cancelled':
                            print("Operazione annullata.")
                            # Continue the main loop without sending anything to Gemini
                        
                        elif result['status'] == 'error':
                            print(f"Errore nell'esecuzione: {result.get('error', 'Errore sconosciuto')}")
                            
                    else:
                        # All parameters present - execute directly (this shouldn't happen in our scenario)
                        logging.info(f'[Main] All parameters present for {function_name}, executing directly')
                        # This would be handled by normal Gemini function calling
                        pass
                
                # Handle normal text response
                elif hasattr(chunk, 'text') and chunk.text:
                    print(chunk.text, end='', flush=True)
            
            print()  # New line after response
            
        except KeyboardInterrupt:
            print("\nConversazione interrotta.")
            break
        except Exception as e:
            logging.error(f'[Main] Error in conversation loop: {e}')
            print("Si è verificato un errore. Riprova.")

def _check_missing_parameters(function_name: str, args: Dict[str, Any]) -> list:
    """
    Check which required parameters are missing for a function.
    
    Args:
        function_name (str): Name of the function
        args (Dict[str, Any]): Current arguments
        
    Returns:
        list: List of missing required parameter names
    """
    required_params = {
        'get_weather_sample': ['location'],
        'set_route_sample': ['destination'],
        'get_vehicle_status_sample': []  # No required parameters
    }
    
    required = required_params.get(function_name, [])
    missing = []
    
    for param in required:
        if param not in args or not args[param]:
            missing.append(param)
    
    return missing

def main():
    """Main entry point."""
    print("Inizializzazione Frank Camper Assistant...")
    
    if not GEMINI_AVAILABLE:
        print("Errore: Google Gemini API non disponibile.")
        print("Assicurati di aver impostato GOOGLE_GEMINI_API_KEY.")
        return
    
    run_conversation()

if __name__ == "__main__":
    main()
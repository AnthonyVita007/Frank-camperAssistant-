"""
AI Processor Module for Frank Camper Assistant.

This module handles the communication with llama.cpp local server to process
user requests and generate appropriate responses.
"""

import logging
import time
import requests
import json
from typing import Optional, Dict, Any

from .ai_response import AIResponse


class AIProcessor:
    """
    Processes AI requests using llama.cpp local server.
    
    This class manages the communication with llama.cpp local server running at 127.0.0.1:8080,
    handles errors, implements retry logic, and generates structured responses.
    
    Attributes:
        _llamacpp_url (str): The base URL for the llama.cpp API endpoint
        _model_name (str): Name of the local model to use
        _max_retries (int): Maximum number of retry attempts
        _timeout (float): Request timeout in seconds
        _session (requests.Session): HTTP session for connection pooling
    """
    
    def __init__(
        self,
        llamacpp_url: str = "http://127.0.0.1:8080/completion",
        model_name: str = "phi3:mini",
        max_retries: int = 3,
        timeout: float = 60.0  # Aumentato timeout per llama.cpp
    ) -> None:
        """
        Initialize the AIProcessor with llama.cpp configuration.
        
        Args:
            llamacpp_url (str): URL for llama.cpp API endpoint (default: "http://127.0.0.1:8080/completion")
            model_name (str): Name of the local model (default: "phi3:mini")
            max_retries (int): Maximum retry attempts (default: 3)
            timeout (float): Request timeout in seconds (default: 60.0)
        """
        #----------------------------------------------------------------
        # INIZIALIZZAZIONE CONFIGURAZIONE LLAMA.CPP
        #----------------------------------------------------------------
        self._llamacpp_url = llamacpp_url
        self._model_name = model_name
        self._max_retries = max_retries
        self._timeout = timeout
        
        #----------------------------------------------------------------
        # CONFIGURAZIONE SESSIONE HTTP OTTIMIZZATA
        #----------------------------------------------------------------
        # Create a persistent HTTP session for better performance
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Configurazione adapter per connection pooling ottimizzato
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Strategia di retry a livello HTTP
        retry_strategy = Retry(
            total=0,  # Gestiamo i retry manualmente
            backoff_factor=0,
            status_forcelist=[]
        )
        
        adapter = HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=retry_strategy
        )
        
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        
        #----------------------------------------------------------------
        # TEST CONNESSIONE INIZIALE
        #----------------------------------------------------------------
        # Test connection during initialization
        self._is_available = self._test_connection()
        
        if self._is_available:
            logging.info(f'[AIProcessor] llama.cpp AI processor initialized successfully with model: {model_name}')
        else:
            logging.warning(f'[AIProcessor] llama.cpp AI processor initialized but connection to {llamacpp_url} failed')
    
    def _test_connection(self) -> bool:
        """
        Test connection to llama.cpp server with optimized health check.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            #----------------------------------------------------------------
            # TEST HEALTH CHECK SEMPLIFICATO
            #----------------------------------------------------------------
            # Test with a minimal completion request optimized for speed
            test_payload = {
                "prompt": "Hi",
                "n_predict": 5,
                "temperature": 0.1,
                "stop": ["\n"]
            }
            
            response = self._session.post(
                self._llamacpp_url,
                json=test_payload,
                timeout=10  # Timeout ridotto per test
            )
            
            if response.status_code == 200:
                logging.debug('[AIProcessor] llama.cpp server connection test successful')
                return True
            else:
                logging.warning(f'[AIProcessor] llama.cpp server returned status code: {response.status_code}')
                return False
                
        except requests.exceptions.RequestException as e:
            logging.warning(f'[AIProcessor] Failed to connect to llama.cpp server: {e}')
            return False
        except Exception as e:
            logging.error(f'[AIProcessor] Unexpected error testing llama.cpp connection: {e}')
            return False
    
    def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Process a user request using llama.cpp local LLM.
        
        Args:
            user_input (str): The user's input text
            context (Optional[Dict[str, Any]]): Additional context for the request
            
        Returns:
            AIResponse: The structured AI response
        """
        #----------------------------------------------------------------
        # VALIDAZIONE INPUT UTENTE
        #----------------------------------------------------------------
        if not user_input or not isinstance(user_input, str):
            logging.warning('[AIProcessor] Received empty or invalid user input')
            return AIResponse(
                text="Mi dispiace, non ho ricevuto una richiesta valida.",
                response_type='error',
                success=False,
                message="Invalid user input"
            )
        
        user_input = user_input.strip()
        if not user_input:
            logging.warning('[AIProcessor] Received empty user input after stripping')
            return AIResponse(
                text="Mi dispiace, la tua richiesta sembra essere vuota.",
                response_type='error',
                success=False,
                message="Empty user input"
            )
        
        logging.info(f'[AIProcessor] Processing user request: "{user_input[:100]}..."')
        
        #----------------------------------------------------------------
        # VERIFICA DISPONIBILITÀ LLAMA.CPP
        #----------------------------------------------------------------
        # Check if llama.cpp is available
        if not self._is_available:
            logging.error('[AIProcessor] llama.cpp server not available')
            return AIResponse(
                text="Mi dispiace, il sistema AI locale non è disponibile al momento. Verifica che llama.cpp sia in esecuzione.",
                response_type='error',
                success=False,
                message="llama.cpp server not available"
            )
        
        #----------------------------------------------------------------
        # ELABORAZIONE CON LOGICA DI RETRY OTTIMIZZATA
        #----------------------------------------------------------------
        # Process the request with retry logic
        for attempt in range(self._max_retries):
            try:
                # Prepare the prompt for llama.cpp
                formatted_prompt = self._prepare_prompt(user_input, context)
                
                # Make request to llama.cpp
                response_text = self._make_llamacpp_request(formatted_prompt)
                
                if response_text:
                    return self._create_success_response(response_text, user_input, context)
                else:
                    logging.warning(f'[AIProcessor] Empty response from llama.cpp (attempt {attempt + 1})')
                    if attempt < self._max_retries - 1:
                        time.sleep(2)  # Pausa più lunga per llama.cpp
                        continue
                    else:
                        return self._create_error_response("Nessuna risposta ricevuta dall'AI locale")
                        
            except requests.exceptions.Timeout as e:
                logging.error(f'[AIProcessor] Timeout in llama.cpp request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(3 + (attempt * 2))  # Backoff più aggressivo
                    continue
                else:
                    return self._create_error_response(f"Timeout nella comunicazione con l'AI locale: {str(e)}")
                    
            except requests.exceptions.RequestException as e:
                logging.error(f'[AIProcessor] Network error in llama.cpp request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore di rete nella comunicazione con l'AI locale: {str(e)}")
                    
            except Exception as e:
                logging.error(f'[AIProcessor] Unexpected error in llama.cpp request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore imprevisto nella comunicazione con l'AI locale: {str(e)}")
        
        # This should never be reached, but just in case
        return self._create_error_response("Errore sconosciuto nel processamento della richiesta")
    
    def _prepare_prompt(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare prompt text for llama.cpp completion API with optimized structure.
        
        Args:
            user_input (str): The user's input
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            str: Formatted prompt for llama.cpp
        """
        #----------------------------------------------------------------
        # COSTRUZIONE PROMPT OTTIMIZZATO PER LLAMA.CPP
        #----------------------------------------------------------------
        # Base system message for Frank - ottimizzato per brevità
        system_message = """Sei Frank, assistente AI per viaggi in camper.
                            Rispondi in italiano, sii cordiale e molto conciso.
                            Specialista in viaggi e camper, ma rispondi anche a domande generali.

"""
        
        # Add context if provided
        if context:
            system_message += f"Contesto: {context}\n\n"
        
        # Format the complete prompt con stop tokens chiari
        formatted_prompt = f"{system_message}Utente: {user_input}\n\nFrank:"
        
        return formatted_prompt
    
    def _make_llamacpp_request(self, prompt: str) -> Optional[str]:
        """
        Make a request to llama.cpp completion API with optimized parameters.
        
        Args:
            prompt (str): The formatted prompt for completion
            
        Returns:
            Optional[str]: The response text from llama.cpp, or None if failed
        """
        #----------------------------------------------------------------
        # CONFIGURAZIONE PAYLOAD OTTIMIZZATO PER LLAMA.CPP
        #----------------------------------------------------------------
        payload = {
            "prompt": prompt,
            "n_predict": 512,  # Ridotto per risposte più veloci
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "repeat_penalty": 1.15,  # Aumentato per evitare ripetizioni
            "repeat_last_n": 128,
            "stop": ["\nUtente:", "\n\nUtente:", "Utente:", "\n\n"],
            "stream": False,
            "cache_prompt": True  # Abilita cache se supportata
        }
        
        try:
            logging.debug(f'[AIProcessor] Sending request to llama.cpp: {self._llamacpp_url}')
            
            #----------------------------------------------------------------
            # INVIO RICHIESTA HTTP CON MONITORING TEMPO
            #----------------------------------------------------------------
            start_time = time.time()
            
            response = self._session.post(
                self._llamacpp_url,
                json=payload,
                timeout=self._timeout
            )
            
            elapsed_time = time.time() - start_time
            logging.debug(f'[AIProcessor] llama.cpp response time: {elapsed_time:.2f}s')
            
            response.raise_for_status()  # Raise exception for HTTP errors
            
            #----------------------------------------------------------------
            # PARSING RISPOSTA JSON MIGLIORATO
            #----------------------------------------------------------------
            # Parse JSON response
            response_data = response.json()
            
            # Extract content from llama.cpp response
            if 'content' in response_data:
                content = response_data['content'].strip()
                
                # Pulizia aggiuntiva del contenuto
                content = self._clean_response_content(content)
                
                logging.debug(f'[AIProcessor] Received response from llama.cpp: "{content[:100]}..."')
                return content
            else:
                logging.warning('[AIProcessor] Unexpected response format from llama.cpp')
                logging.debug(f'[AIProcessor] Response data: {response_data}')
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f'[AIProcessor] Timeout after {self._timeout} seconds')
            raise
        except requests.exceptions.ConnectionError:
            logging.error('[AIProcessor] Connection error - is llama.cpp running?')
            raise
        except requests.exceptions.HTTPError as e:
            logging.error(f'[AIProcessor] HTTP error: {e}')
            raise
        except json.JSONDecodeError as e:
            logging.error(f'[AIProcessor] Failed to parse JSON response: {e}')
            raise
        except Exception as e:
            logging.error(f'[AIProcessor] Unexpected error in llama.cpp request: {e}')
            raise
    
    def _clean_response_content(self, content: str) -> str:
        """
        Clean and optimize response content from llama.cpp.
        
        Args:
            content (str): Raw content from llama.cpp
            
        Returns:
            str: Cleaned content
        """
        #----------------------------------------------------------------
        # PULIZIA CONTENUTO RISPOSTA
        #----------------------------------------------------------------
        if not content:
            return content
        
        # Rimuovi prefissi comuni
        prefixes_to_remove = ["Frank:", "Assistente:", "AI:"]
        for prefix in prefixes_to_remove:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        
        # Rimuovi suffissi comuni
        suffixes_to_remove = ["\nUtente:", "\n\nUtente:"]
        for suffix in suffixes_to_remove:
            if content.endswith(suffix):
                content = content[:-len(suffix)].strip()
        
        # Normalizza spazi multipli
        import re
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 newlines consecutive
        content = re.sub(r' {2,}', ' ', content)      # Max 1 space consecutive
        
        return content.strip()
    
    def _create_success_response(
        self, 
        ai_text: str, 
        user_input: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> AIResponse:
        """
        Create a successful AI response.
        
        Args:
            ai_text (str): The AI-generated text
            user_input (str): The original user input
            context (Optional[Dict[str, Any]]): The request context
            
        Returns:
            AIResponse: The structured success response
        """
        #----------------------------------------------------------------
        # COSTRUZIONE METADATA RISPOSTA DETTAGLIATA
        #----------------------------------------------------------------
        metadata = {
            'model': self._model_name,
            'provider': 'llamacpp_local',
            'user_input_length': len(user_input),
            'response_length': len(ai_text),
            'timestamp': time.time(),
            'llamacpp_url': self._llamacpp_url,
            'timeout_used': self._timeout
        }
        
        if context:
            metadata['context'] = context
        
        return AIResponse(
            text=ai_text.strip(),
            response_type='conversational',
            metadata=metadata,
            success=True,
            message='AI response generated successfully via llama.cpp'
        )
    
    def _create_error_response(self, error_message: str) -> AIResponse:
        """
        Create an error AI response.
        
        Args:
            error_message (str): The error message
            
        Returns:
            AIResponse: The structured error response
        """
        #----------------------------------------------------------------
        # COSTRUZIONE RISPOSTA DI ERRORE
        #----------------------------------------------------------------
        return AIResponse(
            text="Mi dispiace, si è verificato un problema nel processare la tua richiesta. Riprova più tardi.",
            response_type='error',
            metadata={
                'error': error_message, 
                'timestamp': time.time(),
                'provider': 'llamacpp_local',
                'model': self._model_name
            },
            success=False,
            message=error_message
        )
    
    def is_available(self) -> bool:
        """
        Check if the AI processor is available and llama.cpp server is responding.
        
        Returns:
            bool: True if llama.cpp is available, False otherwise
        """
        #----------------------------------------------------------------
        # REFRESH STATUS DISPONIBILITÀ
        #----------------------------------------------------------------
        # Refresh availability status with a quick test
        self._is_available = self._test_connection()
        return self._is_available
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model and llama.cpp setup.
        
        Returns:
            Dict[str, Any]: Model and configuration information
        """
        #----------------------------------------------------------------
        # INFORMAZIONI CONFIGURAZIONE MODELLO
        #----------------------------------------------------------------
        return {
            'model_name': self._model_name,
            'llamacpp_url': self._llamacpp_url,
            'provider': 'llamacpp_local',
            'timeout': self._timeout,
            'max_retries': self._max_retries,
            'available': self.is_available()
        }
    
    def change_model(self, new_model_name: str) -> bool:
        """
        Change the active model for AI processing.
        
        Args:
            new_model_name (str): Name of the new model to use
            
        Returns:
            bool: True if model change was successful, False otherwise
        """
        try:
            #----------------------------------------------------------------
            # CAMBIO MODELLO CON VERIFICA
            #----------------------------------------------------------------
            old_model = self._model_name
            self._model_name = new_model_name
            
            # Test the new model with a simple request
            test_available = self.is_available()
            
            if test_available:
                logging.info(f'[AIProcessor] Successfully changed model from {old_model} to {new_model_name}')
                return True
            else:
                # Revert to old model if test failed
                self._model_name = old_model
                logging.warning(f'[AIProcessor] Failed to change to model {new_model_name}, reverted to {old_model}')
                return False
                
        except Exception as e:
            logging.error(f'[AIProcessor] Error changing model: {e}')
            return False
    
    def shutdown(self) -> None:
        """
        Shutdown the AI processor and clean up resources.
        """
        try:
            #----------------------------------------------------------------
            # SHUTDOWN E CLEANUP RISORSE
            #----------------------------------------------------------------
            logging.info('[AIProcessor] Shutting down llama.cpp AI processor')
            self._session.close()
            self._is_available = False
        except Exception as e:
            logging.error(f'[AIProcessor] Error during shutdown: {e}')
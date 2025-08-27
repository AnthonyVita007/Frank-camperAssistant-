"""
AI Processor Module for Frank Camper Assistant.

This module handles the communication with Ollama local LLM to process
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
    Processes AI requests using Ollama local server.
    
    This class manages the communication with Ollama local server running at localhost:11434,
    handles errors, implements retry logic, and generates structured responses.
    
    Attributes:
        _ollama_url (str): The base URL for the Ollama API endpoint
        _model_name (str): Name of the local model to use
        _max_retries (int): Maximum number of retry attempts
        _timeout (float): Request timeout in seconds
        _session (requests.Session): HTTP session for connection pooling
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/chat",
        model_name: str = "phi3:mini",
        max_retries: int = 3,
        timeout: float = 30.0
    ) -> None:
        """
        Initialize the AIProcessor with Ollama configuration.
        
        Args:
            ollama_url (str): URL for Ollama API endpoint (default: "http://localhost:11434/api/chat")
            model_name (str): Name of the local model (default: "phi3:mini")
            max_retries (int): Maximum retry attempts (default: 3)
            timeout (float): Request timeout in seconds (default: 30.0)
        """
        self._ollama_url = ollama_url
        self._model_name = model_name
        self._max_retries = max_retries
        self._timeout = timeout
        
        # Create a persistent HTTP session for better performance
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test connection during initialization
        self._is_available = self._test_connection()
        
        if self._is_available:
            logging.info(f'[AIProcessor] Ollama AI processor initialized successfully with model: {model_name}')
        else:
            logging.warning(f'[AIProcessor] Ollama AI processor initialized but connection to {ollama_url} failed')
    
    def _test_connection(self) -> bool:
        """
        Test connection to Ollama server.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Test with a simple health check to the base URL
            health_url = self._ollama_url.replace('/api/chat', '/api/tags')
            response = self._session.get(health_url, timeout=5)
            
            if response.status_code == 200:
                logging.debug('[AIProcessor] Ollama server connection test successful')
                return True
            else:
                logging.warning(f'[AIProcessor] Ollama server returned status code: {response.status_code}')
                return False
                
        except requests.exceptions.RequestException as e:
            logging.warning(f'[AIProcessor] Failed to connect to Ollama server: {e}')
            return False
        except Exception as e:
            logging.error(f'[AIProcessor] Unexpected error testing Ollama connection: {e}')
            return False
    
    def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Process a user request using Ollama local LLM.
        
        Args:
            user_input (str): The user's input text
            context (Optional[Dict[str, Any]]): Additional context for the request
            
        Returns:
            AIResponse: The structured AI response
        """
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
        
        # Check if Ollama is available
        if not self._is_available:
            logging.error('[AIProcessor] Ollama server not available')
            return AIResponse(
                text="Mi dispiace, il sistema AI locale non è disponibile al momento. Verifica che Ollama sia in esecuzione.",
                response_type='error',
                success=False,
                message="Ollama server not available"
            )
        
        # Process the request with retry logic
        for attempt in range(self._max_retries):
            try:
                # Prepare the messages for Ollama
                messages = self._prepare_messages(user_input, context)
                
                # Make request to Ollama
                response_text = self._make_ollama_request(messages)
                
                if response_text:
                    return self._create_success_response(response_text, user_input, context)
                else:
                    logging.warning(f'[AIProcessor] Empty response from Ollama (attempt {attempt + 1})')
                    if attempt < self._max_retries - 1:
                        time.sleep(1)  # Wait before retry
                        continue
                    else:
                        return self._create_error_response("Nessuna risposta ricevuta dall'AI locale")
                        
            except requests.exceptions.RequestException as e:
                logging.error(f'[AIProcessor] Network error in Ollama request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore di rete nella comunicazione con l'AI locale: {str(e)}")
                    
            except Exception as e:
                logging.error(f'[AIProcessor] Unexpected error in Ollama request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore imprevisto nella comunicazione con l'AI locale: {str(e)}")
        
        # This should never be reached, but just in case
        return self._create_error_response("Errore sconosciuto nel processamento della richiesta")
    
    def _prepare_messages(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> list:
        """
        Prepare messages array for Ollama chat API.
        
        Args:
            user_input (str): The user's input
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            list: Array of messages formatted for Ollama
        """
        # Base system message for Frank
        system_message = """Sei Frank, un assistente AI per camper e viaggiatori. 
        Rispondi sempre in italiano in modo cordiale e utile.
        Sei specializzato nel fornire informazioni e consigli per viaggi in camper, 
        ma puoi rispondere anche a domande generali.
        Mantieni un tono amichevole e professionale.
        Puoi scrivere le risposte usando markdown per formattare il testo, se necessario.
        Le tue risposte devono essere concise ma informative."""
        
        # Add context if provided
        if context:
            system_message += f"\n\nContesto aggiuntivo: {context}"
        
        # Prepare messages array
        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user", 
                "content": user_input
            }
        ]
        
        return messages
    
    def _make_ollama_request(self, messages: list) -> Optional[str]:
        """
        Make a request to Ollama chat API.
        
        Args:
            messages (list): Messages array for the conversation
            
        Returns:
            Optional[str]: The response text from Ollama, or None if failed
        """
        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "num_predict": 2048
            }
        }
        
        try:
            logging.debug(f'[AIProcessor] Sending request to Ollama: {self._ollama_url}')
            
            response = self._session.post(
                self._ollama_url,
                json=payload,
                timeout=self._timeout
            )
            
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse JSON response
            response_data = response.json()
            
            # Extract message content from Ollama response
            if 'message' in response_data and 'content' in response_data['message']:
                content = response_data['message']['content'].strip()
                logging.debug(f'[AIProcessor] Received response from Ollama: "{content[:100]}..."')
                return content
            else:
                logging.warning('[AIProcessor] Unexpected response format from Ollama')
                logging.debug(f'[AIProcessor] Response data: {response_data}')
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f'[AIProcessor] Timeout after {self._timeout} seconds')
            raise
        except requests.exceptions.ConnectionError:
            logging.error('[AIProcessor] Connection error - is Ollama running?')
            raise
        except requests.exceptions.HTTPError as e:
            logging.error(f'[AIProcessor] HTTP error: {e}')
            raise
        except json.JSONDecodeError as e:
            logging.error(f'[AIProcessor] Failed to parse JSON response: {e}')
            raise
        except Exception as e:
            logging.error(f'[AIProcessor] Unexpected error in Ollama request: {e}')
            raise
    
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
        metadata = {
            'model': self._model_name,
            'provider': 'ollama_local',
            'user_input_length': len(user_input),
            'response_length': len(ai_text),
            'timestamp': time.time(),
            'ollama_url': self._ollama_url
        }
        
        if context:
            metadata['context'] = context
        
        return AIResponse(
            text=ai_text.strip(),
            response_type='conversational',
            metadata=metadata,
            success=True,
            message='AI response generated successfully via Ollama'
        )
    
    def _create_error_response(self, error_message: str) -> AIResponse:
        """
        Create an error AI response.
        
        Args:
            error_message (str): The error message
            
        Returns:
            AIResponse: The structured error response
        """
        return AIResponse(
            text="Mi dispiace, si è verificato un problema nel processare la tua richiesta. Riprova più tardi.",
            response_type='error',
            metadata={
                'error': error_message, 
                'timestamp': time.time(),
                'provider': 'ollama_local',
                'model': self._model_name
            },
            success=False,
            message=error_message
        )
    
    def is_available(self) -> bool:
        """
        Check if the AI processor is available and Ollama server is responding.
        
        Returns:
            bool: True if Ollama is available, False otherwise
        """
        # Refresh availability status with a quick test
        self._is_available = self._test_connection()
        return self._is_available
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model and Ollama setup.
        
        Returns:
            Dict[str, Any]: Model and configuration information
        """
        return {
            'model_name': self._model_name,
            'ollama_url': self._ollama_url,
            'provider': 'ollama_local',
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
            logging.info('[AIProcessor] Shutting down Ollama AI processor')
            self._session.close()
            self._is_available = False
        except Exception as e:
            logging.error(f'[AIProcessor] Error during shutdown: {e}')
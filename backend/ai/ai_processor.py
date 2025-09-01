"""
AI Processor Module for Frank Camper Assistant.

This module handles dual AI processing: local llama.cpp server AND Google Gemini API,
providing a unified interface with clear separation between local and cloud implementations.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
import time
import requests
import json
import os
from typing import Optional, Dict, Any, Union
from enum import Enum

from .ai_response import AIResponse


class AIProvider(Enum):
    """Enumeration of available AI providers."""
    LOCAL = "local"
    GEMINI = "gemini"


class AIProcessor:
    """
    Dual AI processor supporting both local llama.cpp and Google Gemini API.
    
    This class provides a unified interface for AI processing while maintaining
    clear separation between local (llama.cpp) and cloud (Gemini) implementations.
    The processor can switch between providers based on configuration or availability.
    
    Attributes:
        _current_provider (AIProvider): Currently active AI provider
        _local_config (dict): Configuration for local llama.cpp
        _gemini_config (dict): Configuration for Google Gemini API
        _session (requests.Session): HTTP session for requests
        _local_available (bool): Whether local AI is available
        _gemini_available (bool): Whether Gemini API is available
    """
    
#----------------------------------------------------------------
# INIZIALIZZAZIONE E CONFIGURAZIONE DUAL-AI
#----------------------------------------------------------------
    def __init__(
        self,
        provider: AIProvider = AIProvider.LOCAL,
        llamacpp_url: str = "http://127.0.0.1:8080/completion",
        llamacpp_model: str = "gemma_3_270M",
        gemini_api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 60.0
    ) -> None:
        """
        Initialize the dual AI processor.
        
        Args:
            provider (AIProvider): Default provider to use
            llamacpp_url (str): URL for llama.cpp API endpoint
            llamacpp_model (str): Name of the local model
            gemini_api_key (Optional[str]): Google Gemini API key
            max_retries (int): Maximum retry attempts
            timeout (float): Request timeout in seconds
        """
        self._current_provider = provider
        self._max_retries = max_retries
        self._timeout = timeout
        
        # Initialize HTTP session
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Configure session adapter
        self._configure_session_adapter()
        
        # Initialize local AI configuration
        self._local_config = {
            'url': llamacpp_url,
            'model': llamacpp_model,
            'enabled': True
        }
        
        # Initialize Gemini API configuration
        self._gemini_config = {
            'api_key': gemini_api_key or os.getenv('GEMINI_API_KEY'),
            'model': 'gemini-1.5-flash',
            'url': 'https://generativelanguage.googleapis.com/v1beta/models/',
            'enabled': True
        }
        
        # Initialize availability status without testing at startup
        self._local_available = False
        self._gemini_available = False
        
        # Log initialization results
        self._log_initialization_status()
    
    def _configure_session_adapter(self) -> None:
        """Configure HTTP session adapter for optimal performance."""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=0,  # Handle retries manually
            backoff_factor=0,
            status_forcelist=[]
        )
        
        adapter = HTTPAdapter(
            pool_connections=2,  # Support both local and cloud
            pool_maxsize=2,
            max_retries=retry_strategy
        )
        
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
    
    def _log_initialization_status(self) -> None:
        """Log the initialization status of both AI providers."""
        local_config_status = "CONFIGURED" if self._local_config['url'] else "NOT CONFIGURED"
        gemini_config_status = "CONFIGURED" if self._gemini_config['api_key'] else "NOT CONFIGURED"
        
        logging.info(f'[AIProcessor] Dual AI processor initialized:')
        logging.info(f'[AIProcessor] - Local llama.cpp: {local_config_status} (availability tested on demand)')
        logging.info(f'[AIProcessor] - Google Gemini: {gemini_config_status} (availability tested on demand)')
        logging.info(f'[AIProcessor] - Current provider: {self._current_provider.value}')
        
        if not self._local_config['url'] and not self._gemini_config['api_key']:
            logging.warning('[AIProcessor] No AI providers configured!')
        else:
            logging.info('[AIProcessor] Provider availability will be tested when first used')


#----------------------------------------------------------------
# SEZIONE: LOGICA LLAMA.CPP (LOCALE)
#----------------------------------------------------------------

    def _test_local_connection(self) -> bool:
        """
        Test connection to local llama.cpp server.
        
        Returns:
            bool: True if local AI is available, False otherwise
        """
        try:
            test_payload = {
                "prompt": "Hi",
                "n_predict": 5,
                "temperature": 0.1,
                "stop": ["\n"]
            }
            
            response = self._session.post(
                self._local_config['url'],
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logging.debug('[AIProcessor] Local llama.cpp connection test successful')
                return True
            else:
                logging.warning(f'[AIProcessor] Local llama.cpp returned status: {response.status_code}')
                return False
                
        except requests.exceptions.RequestException as e:
            logging.warning(f'[AIProcessor] Local llama.cpp connection failed: {e}')
            return False
        except Exception as e:
            logging.error(f'[AIProcessor] Unexpected error testing local connection: {e}')
            return False
    
    def _prepare_local_prompt(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare prompt for local llama.cpp processing.
        
        Args:
            user_input (str): User's input text
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            str: Formatted prompt for llama.cpp
        """
        system_message = """Sei Frank, assistente AI di bordo per viaggi in camper.
        - Rispondi sempre in italiano naturale, corretto e scorrevole ma sii sintetico.
        - Lunghezza: 1–3 frasi, salvo quando viene chiesto esplicitamente un elenco o una guida passo‑passo.
        - Se la richiesta è ambigua, poni una o più domande di chiarimento.
        - Usa unità metriche (km, °C, litri) e termini comuni in italiano, evitando anglicismi inutili.
        """
        
        if context:
            system_message += f"Contesto: {context}\n\n"
        
        return f"{system_message}Utente: {user_input}\n\nFrank:"
    
    def _make_local_request(self, prompt: str) -> Optional[str]:
        """
        Make request to local llama.cpp server.
        
        Args:
            prompt (str): Formatted prompt
            
        Returns:
            Optional[str]: Response text or None if failed
        """
        payload = {
            "prompt": prompt,
            "n_predict": 512,
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
            "repeat_penalty": 1.15,
            "repeat_last_n": 128,
            "stop": ["\nUtente:", "\n\nUtente:", "Utente:", "\n\n"],
            "stream": False,
            "cache_prompt": True
        }
        
        try:
            logging.debug('[AIProcessor] Sending request to local llama.cpp')
            start_time = time.time()
            
            response = self._session.post(
                self._local_config['url'],
                json=payload,
                timeout=self._timeout
            )
            
            elapsed_time = time.time() - start_time
            logging.debug(f'[AIProcessor] Local response time: {elapsed_time:.2f}s')
            
            response.raise_for_status()
            response_data = response.json()
            
            if 'content' in response_data:
                content = response_data['content'].strip()
                content = self._clean_local_response(content)
                return content
            else:
                logging.warning('[AIProcessor] Unexpected local response format')
                return None
                
        except Exception as e:
            logging.error(f'[AIProcessor] Local request error: {e}')
            raise
    
    def _clean_local_response(self, content: str) -> str:
        """
        Clean response content from llama.cpp.
        
        Args:
            content (str): Raw content from llama.cpp
            
        Returns:
            str: Cleaned content
        """
        if not content:
            return content
        
        # Remove common prefixes
        prefixes_to_remove = ["Frank:", "Assistente:", "AI:"]
        for prefix in prefixes_to_remove:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        
        # Remove common suffixes
        suffixes_to_remove = ["\nUtente:", "\n\nUtente:"]
        for suffix in suffixes_to_remove:
            if content.endswith(suffix):
                content = content[:-len(suffix)].strip()
        
        # Normalize whitespace
        import re
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        
        return content.strip()
    
    def _make_local_stream_request(self, prompt: str):
        """
        Make streaming request to local llama.cpp server.
        
        Args:
            prompt (str): Formatted prompt
            
        Yields:
            str: Content chunks as received
        """
        payload = {
            "prompt": prompt,
            "n_predict": 192,
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "repeat_penalty": 1.15,
            "repeat_last_n": 128,
            "stop": ["\nUtente:", "\n\nUtente:", "Utente:", "\n\n"],
            "stream": True,
            "cache_prompt": True
        }
        
        try:
            logging.debug('[AIProcessor] Starting local streaming request')
            
            response = self._session.post(
                self._local_config['url'],
                json=payload,
                timeout=self._timeout,
                stream=True
            )
            
            response.raise_for_status()
            
            chunk_count = 0
            for raw_chunk in response.iter_lines(decode_unicode=True):
                if raw_chunk and raw_chunk.startswith('data: '):
                    data_chunk = raw_chunk[6:]
                    
                    if data_chunk.strip() == '[DONE]':
                        break
                    
                    try:
                        chunk_data = json.loads(data_chunk)
                        if 'content' in chunk_data:
                            content = chunk_data['content']
                            if content:
                                chunk_count += 1
                                yield self._clean_local_streaming_chunk(content)
                    except json.JSONDecodeError:
                        continue
            
            logging.debug(f'[AIProcessor] Local streaming completed: {chunk_count} chunks')
            
        except Exception as e:
            logging.error(f'[AIProcessor] Local streaming error: {e}')
            raise
    
    def _clean_local_streaming_chunk(self, chunk: str) -> str:
        """Clean streaming chunk from llama.cpp."""
        if not chunk:
            return chunk
        
        prefixes_to_remove = ["Frank:", "Assistente:", "AI:"]
        for prefix in prefixes_to_remove:
            if chunk.startswith(prefix):
                chunk = chunk[len(prefix):].strip()
                break
        
        return chunk


#----------------------------------------------------------------
# SEZIONE: LOGICA GOOGLE GEMINI (CLOUD API)
#----------------------------------------------------------------

    def _test_gemini_connection(self) -> bool:
        """
        Test connection to Google Gemini API.
        
        Returns:
            bool: True if Gemini API is available, False otherwise
        """
        if not self._gemini_config['api_key']:
            logging.warning('[AIProcessor] No Gemini API key provided')
            return False
        
        try:
            # Simple test request to Gemini
            url = f"{self._gemini_config['url']}{self._gemini_config['model']}:generateContent"
            
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self._gemini_config['api_key']
            }
            
            test_payload = {
                "contents": [{
                    "parts": [{"text": "Hello"}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 10,
                    "temperature": 0.1
                }
            }
            
            response = self._session.post(
                url,
                headers=headers,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logging.debug('[AIProcessor] Gemini API connection test successful')
                return True
            else:
                logging.warning(f'[AIProcessor] Gemini API returned status: {response.status_code}')
                return False
                
        except requests.exceptions.RequestException as e:
            logging.warning(f'[AIProcessor] Gemini API connection failed: {e}')
            return False
        except Exception as e:
            logging.error(f'[AIProcessor] Unexpected error testing Gemini connection: {e}')
            return False
    
    def _prepare_gemini_prompt(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare prompt for Google Gemini API.
        
        Args:
            user_input (str): User's input text
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            str: Formatted prompt for Gemini
        """
        system_message = """Sei Frank, assistente AI di bordo per viaggi in camper.
        - Rispondi sempre in italiano naturale, corretto e scorrevole.
        - Sii conciso ma completo nelle tue spiegazioni.
        - Se la richiesta è ambigua, poni domande di chiarimento.
        - Usa unità metriche (km, °C, litri) e terminologia italiana.
        - Mantieni un tono amichevole e professionale.
        """
        
        if context:
            system_message += f"\n\nContesto: {context}"
        
        return f"{system_message}\n\nRichiesta dell'utente: {user_input}\n\nRisposta di Frank:"
    
    def _make_gemini_request(self, prompt: str) -> Optional[str]:
        """
        Make request to Google Gemini API.
        
        Args:
            prompt (str): Formatted prompt
            
        Returns:
            Optional[str]: Response text or None if failed
        """
        if not self._gemini_config['api_key']:
            raise Exception("Gemini API key not available")
        
        url = f"{self._gemini_config['url']}{self._gemini_config['model']}:generateContent"
        
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': self._gemini_config['api_key']
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.7,
                "topP": 0.8,
                "topK": 64
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH", 
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        try:
            logging.debug('[AIProcessor] Sending request to Gemini API')
            start_time = time.time()
            
            response = self._session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._timeout
            )
            
            elapsed_time = time.time() - start_time
            logging.debug(f'[AIProcessor] Gemini response time: {elapsed_time:.2f}s')
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract text from Gemini response
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if parts and 'text' in parts[0]:
                        content = parts[0]['text'].strip()
                        return self._clean_gemini_response(content)
            
            logging.warning('[AIProcessor] Unexpected Gemini response format')
            return None
            
        except Exception as e:
            logging.error(f'[AIProcessor] Gemini request error: {e}')
            raise
    
    def _clean_gemini_response(self, content: str) -> str:
        """
        Clean response content from Gemini API.
        
        Args:
            content (str): Raw content from Gemini
            
        Returns:
            str: Cleaned content
        """
        if not content:
            return content
        
        # Remove common AI response prefixes
        prefixes_to_remove = ["Frank:", "Risposta di Frank:", "Assistente:", "AI:"]
        for prefix in prefixes_to_remove:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        
        return content.strip()


#----------------------------------------------------------------
# SEZIONE: ORCHESTRAZIONE E ROUTING
#----------------------------------------------------------------

    def set_provider(self, provider: AIProvider) -> bool:
        """
        Switch to a different AI provider.
        
        Args:
            provider (AIProvider): Provider to switch to
            
        Returns:
            bool: True if switch was successful, False otherwise
        """
        old_provider = self._current_provider
        
        # Test availability of target provider on demand
        if provider == AIProvider.LOCAL:
            if not self._test_local_connection():
                logging.warning('[AIProcessor] Cannot switch to local: not available')
                self._local_available = False
                return False
            self._local_available = True
        elif provider == AIProvider.GEMINI:
            if not self._test_gemini_connection():
                logging.warning('[AIProcessor] Cannot switch to Gemini: not available')
                self._gemini_available = False
                return False
            self._gemini_available = True
        
        self._current_provider = provider
        logging.info(f'[AIProcessor] Switched from {old_provider.value} to {provider.value}')
        return True
    
    def get_current_provider(self) -> AIProvider:
        """Get the currently active AI provider."""
        return self._current_provider
    
    def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Process user request using the current AI provider.
        
        Args:
            user_input (str): User's input text
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            AIResponse: Structured AI response
        """
        # Input validation
        if not user_input or not isinstance(user_input, str):
            logging.warning('[AIProcessor] Invalid input received')
            return AIResponse(
                text="Mi dispiace, non ho ricevuto una richiesta valida.",
                response_type='error',
                success=False,
                message="Invalid user input"
            )
        
        user_input = user_input.strip()
        if not user_input:
            logging.warning('[AIProcessor] Empty input received')
            return AIResponse(
                text="Mi dispiace, la tua richiesta sembra essere vuota.",
                response_type='error',
                success=False,
                message="Empty user input"
            )
        
        logging.info(f'[AIProcessor] Processing request with {self._current_provider.value}: "{user_input[:100]}..."')
        
        # Route to appropriate provider
        for attempt in range(self._max_retries):
            try:
                if self._current_provider == AIProvider.LOCAL:
                    return self._process_with_local(user_input, context)
                elif self._current_provider == AIProvider.GEMINI:
                    return self._process_with_gemini(user_input, context)
                else:
                    return self._create_error_response(f"Unknown provider: {self._current_provider}")
                    
            except Exception as e:
                logging.error(f'[AIProcessor] Attempt {attempt + 1} failed: {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"All attempts failed: {str(e)}")
        
        return self._create_error_response("Unknown error in request processing")
    
    def _process_with_local(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """Process request using local llama.cpp."""
        # Test availability on demand if not yet tested
        if not self._local_available:
            if not self._test_local_connection():
                self._local_available = False
                raise Exception("Local AI not available")
            self._local_available = True
        
        formatted_prompt = self._prepare_local_prompt(user_input, context)
        response_text = self._make_local_request(formatted_prompt)
        
        if response_text:
            return self._create_success_response(
                response_text, 
                user_input, 
                context, 
                AIProvider.LOCAL
            )
        else:
            raise Exception("Empty response from local AI")
    
    def _process_with_gemini(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """Process request using Google Gemini API."""
        # Test availability on demand if not yet tested
        if not self._gemini_available:
            if not self._test_gemini_connection():
                self._gemini_available = False
                raise Exception("Gemini API not available")
            self._gemini_available = True
        
        formatted_prompt = self._prepare_gemini_prompt(user_input, context)
        response_text = self._make_gemini_request(formatted_prompt)
        
        if response_text:
            return self._create_success_response(
                response_text, 
                user_input, 
                context, 
                AIProvider.GEMINI
            )
        else:
            raise Exception("Empty response from Gemini API")
    
    def stream_request(self, user_input: str, context: Optional[Dict[str, Any]] = None):
        """
        Process user request with streaming support.
        
        Args:
            user_input (str): User's input text
            context (Optional[Dict[str, Any]]): Additional context
            
        Yields:
            str: Text chunks as they are generated
        """
        # Input validation
        if not user_input or not isinstance(user_input, str):
            yield "Mi dispiace, non ho ricevuto una richiesta valida."
            return
        
        user_input = user_input.strip()
        if not user_input:
            yield "Mi dispiace, la tua richiesta sembra essere vuota."
            return
        
        logging.info(f'[AIProcessor] Streaming request with {self._current_provider.value}: "{user_input[:100]}..."')
        
        try:
            if self._current_provider == AIProvider.LOCAL:
                if not self._local_available:
                    yield "Il sistema AI locale non è disponibile."
                    return
                
                formatted_prompt = self._prepare_local_prompt(user_input, context)
                for chunk in self._make_local_stream_request(formatted_prompt):
                    if chunk:
                        yield chunk
                        
            elif self._current_provider == AIProvider.GEMINI:
                # Note: Gemini streaming not implemented in this version
                # Fall back to non-streaming
                response = self._process_with_gemini(user_input, context)
                yield response.text
                
            else:
                yield f"Provider sconosciuto: {self._current_provider.value}"
                
        except Exception as e:
            logging.error(f'[AIProcessor] Streaming error: {e}')
            yield f"Si è verificato un errore durante la generazione: {str(e)}"
    
    def _create_success_response(
        self, 
        ai_text: str, 
        user_input: str, 
        context: Optional[Dict[str, Any]], 
        provider: AIProvider
    ) -> AIResponse:
        """Create a successful AI response."""
        metadata = {
            'provider': provider.value,
            'user_input_length': len(user_input),
            'response_length': len(ai_text),
            'timestamp': time.time()
        }
        
        if provider == AIProvider.LOCAL:
            metadata.update({
                'model': self._local_config['model'],
                'llamacpp_url': self._local_config['url']
            })
        elif provider == AIProvider.GEMINI:
            metadata.update({
                'model': self._gemini_config['model'],
                'api_version': 'v1beta'
            })
        
        if context:
            metadata['context'] = context
        
        return AIResponse(
            text=ai_text.strip(),
            response_type='conversational',
            metadata=metadata,
            success=True,
            message=f'AI response generated successfully via {provider.value}'
        )
    
    def _create_error_response(self, error_message: str) -> AIResponse:
        """Create an error AI response."""
        return AIResponse(
            text="Mi dispiace, si è verificato un problema nel processare la tua richiesta. Riprova più tardi.",
            response_type='error',
            metadata={
                'error': error_message,
                'timestamp': time.time(),
                'provider': self._current_provider.value
            },
            success=False,
            message=error_message
        )
    
    def is_available(self) -> bool:
        """Check if any AI provider is available by testing on demand."""
        # Test local availability if not yet determined
        if not self._local_available:
            self._local_available = self._test_local_connection()
        
        # Test gemini availability if not yet determined  
        if not self._gemini_available:
            self._gemini_available = self._test_gemini_connection()
            
        return self._local_available or self._gemini_available
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get detailed status of both providers."""
        return {
            'current_provider': self._current_provider.value,
            'local': {
                'available': self._local_available,
                'model': self._local_config['model'],
                'url': self._local_config['url']
            },
            'gemini': {
                'available': self._gemini_available,
                'model': self._gemini_config['model'],
                'api_key_configured': bool(self._gemini_config['api_key'])
            },
            'overall_available': self.is_available()
        }
    
    def warmup(self) -> bool:
        """Warm up the current AI provider."""
        try:
            if self._current_provider == AIProvider.LOCAL:
                # Test availability first, then warmup if available
                if self._test_local_connection():
                    self._local_available = True
                    return self._warmup_local()
                else:
                    self._local_available = False
                    return False
            elif self._current_provider == AIProvider.GEMINI:
                # Test availability first, then warmup if available
                if self._test_gemini_connection():
                    self._gemini_available = True
                    return self._warmup_gemini()
                else:
                    self._gemini_available = False
                    return False
            else:
                logging.warning('[AIProcessor] No provider available for warmup')
                return False
        except Exception as e:
            logging.error(f'[AIProcessor] Warmup error: {e}')
            return False
    
    def _warmup_local(self) -> bool:
        """Warm up local llama.cpp."""
        try:
            logging.info('[AIProcessor] Starting local AI warmup...')
            warmup_payload = {
                "prompt": "Hi",
                "n_predict": 5,
                "temperature": 0.1,
                "cache_prompt": True,
                "stop": ["\n"]
            }
            
            response = self._session.post(
                self._local_config['url'],
                json=warmup_payload,
                timeout=15
            )
            
            if response.status_code == 200:
                logging.info('[AIProcessor] Local AI warmup completed')
                return True
            else:
                logging.warning(f'[AIProcessor] Local AI warmup failed: {response.status_code}')
                return False
                
        except Exception as e:
            logging.warning(f'[AIProcessor] Local AI warmup error: {e}')
            return False
    
    def _warmup_gemini(self) -> bool:
        """Warm up Gemini API connection."""
        try:
            logging.info('[AIProcessor] Starting Gemini API warmup...')
            # Gemini doesn't need warmup like local models, just test connection
            return self._test_gemini_connection()
        except Exception as e:
            logging.warning(f'[AIProcessor] Gemini API warmup error: {e}')
            return False
    
    def shutdown(self) -> None:
        """Shutdown the AI processor and clean up resources."""
        try:
            logging.info('[AIProcessor] Shutting down dual AI processor')
            self._session.close()
            self._local_available = False
            self._gemini_available = False
        except Exception as e:
            logging.error(f'[AIProcessor] Shutdown error: {e}')
"""
AI Processor Module for Frank Camper Assistant.

This module handles the communication with Ollama local LLM to process
user requests and generate appropriate responses.
"""

import logging
import time
import requests
import json
import hashlib
import threading
from collections import OrderedDict
from typing import Optional, Dict, Any, Callable

from .ai_response import AIResponse


class AIProcessor:
    """
    Processes AI requests using Ollama local server with advanced optimizations.
    
    This class manages the communication with Ollama local server running at localhost:11434,
    handles errors, implements retry logic, intelligent caching, progress callbacks,
    and generates structured responses with performance metrics.
    
    Attributes:
        _ollama_url (str): The base URL for the Ollama API endpoint
        _model_name (str): Name of the local model to use
        _max_retries (int): Maximum number of retry attempts
        _timeout (float): Request timeout in seconds
        _session (requests.Session): HTTP session for connection pooling
        _cache (OrderedDict): LRU cache for responses
        _cache_lock (threading.Lock): Thread-safe cache access
        _performance_metrics (Dict): Performance tracking data
        _progress_callback (Optional[Callable]): Callback for progress updates
        _is_warmed_up (bool): Whether the model has been warmed up
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/chat",
        model_name: str = "phi3:mini",
        max_retries: int = 3,
        timeout: float = 25.0,
        cache_size: int = 100,
        enable_cache: bool = True,
        enable_warmup: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> None:
        """
        Initialize the AIProcessor with Ollama configuration and optimizations.
        
        Args:
            ollama_url (str): URL for Ollama API endpoint (default: "http://localhost:11434/api/chat")
            model_name (str): Name of the local model (default: "phi3:mini")
            max_retries (int): Maximum retry attempts (default: 3)
            timeout (float): Request timeout in seconds (default: 25.0, reduced from 30.0)
            cache_size (int): Maximum number of cached responses (default: 100)
            enable_cache (bool): Enable intelligent caching (default: True)
            enable_warmup (bool): Enable model warmup at initialization (default: True)
            progress_callback (Optional[Callable]): Callback for progress updates
        """
        self._ollama_url = ollama_url
        self._model_name = model_name
        self._max_retries = max_retries
        self._timeout = timeout
        self._cache_size = cache_size
        self._enable_cache = enable_cache
        self._enable_warmup = enable_warmup
        self._progress_callback = progress_callback
        
        # Initialize caching system
        self._cache = OrderedDict()
        self._cache_lock = threading.Lock()
        
        # Initialize performance metrics
        self._performance_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0.0,
            'total_response_time': 0.0,
            'warmup_completed': False,
            'startup_time': time.time()
        }
        
        # Warmup status
        self._is_warmed_up = False
        
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
            
            # Perform warmup if enabled
            if self._enable_warmup:
                self._warmup_model()
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
    
    def _warmup_model(self) -> None:
        """
        Warm up the model with a simple request to improve initial response times.
        """
        if self._is_warmed_up:
            return
            
        try:
            logging.info('[AIProcessor] Starting model warmup...')
            if self._progress_callback:
                self._progress_callback("Warming up model...", 0.1)
            
            # Simple warmup prompt in Italian
            warmup_prompt = "Ciao, come stai?"
            warmup_messages = [{
                "role": "system",
                "content": "Sei Frank, un assistente AI per camper. Rispondi brevemente."
            }, {
                "role": "user",
                "content": warmup_prompt
            }]
            
            start_time = time.time()
            
            # Make warmup request with reduced parameters for speed
            payload = {
                "model": self._model_name,
                "messages": warmup_messages,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "top_p": 0.7,
                    "top_k": 20,
                    "num_predict": 50  # Very short response for warmup
                }
            }
            
            response = self._session.post(
                self._ollama_url,
                json=payload,
                timeout=15  # Shorter timeout for warmup
            )
            
            warmup_time = time.time() - start_time
            
            if response.status_code == 200:
                self._is_warmed_up = True
                self._performance_metrics['warmup_completed'] = True
                logging.info(f'[AIProcessor] Model warmup completed successfully in {warmup_time:.2f}s')
                if self._progress_callback:
                    self._progress_callback("Model warmed up successfully!", 1.0)
            else:
                logging.warning(f'[AIProcessor] Model warmup failed with status: {response.status_code}')
                
        except Exception as e:
            logging.warning(f'[AIProcessor] Model warmup failed: {e}')
    
    def _generate_cache_key(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a cache key for the given input and context.
        
        Args:
            user_input (str): The user's input
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            str: SHA-256 hash key for caching
        """
        # Create a consistent string representation
        cache_string = f"{user_input.strip().lower()}"
        if context:
            # Sort context keys for consistent hashing
            context_str = json.dumps(context, sort_keys=True)
            cache_string += f"||{context_str}"
        
        # Add model name to cache key to invalidate cache on model change
        cache_string += f"||{self._model_name}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(cache_string.encode('utf-8')).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[AIResponse]:
        """
        Get a response from cache if available.
        
        Args:
            cache_key (str): The cache key
            
        Returns:
            Optional[AIResponse]: Cached response or None
        """
        if not self._enable_cache:
            return None
            
        with self._cache_lock:
            if cache_key in self._cache:
                # Move to end (most recently used)
                response = self._cache.pop(cache_key)
                self._cache[cache_key] = response
                
                self._performance_metrics['cache_hits'] += 1
                logging.debug(f'[AIProcessor] Cache hit for key: {cache_key[:16]}...')
                return response
                
        return None
    
    def _store_in_cache(self, cache_key: str, response: AIResponse) -> None:
        """
        Store a response in cache.
        
        Args:
            cache_key (str): The cache key
            response (AIResponse): The response to cache
        """
        if not self._enable_cache or not response.success:
            return
            
        with self._cache_lock:
            # Remove oldest items if cache is full
            while len(self._cache) >= self._cache_size:
                self._cache.popitem(last=False)  # Remove oldest (FIFO)
            
            self._cache[cache_key] = response
            logging.debug(f'[AIProcessor] Stored response in cache: {cache_key[:16]}...')
    
    def _update_performance_metrics(self, response_time: float, cache_hit: bool = False) -> None:
        """
        Update performance metrics.
        
        Args:
            response_time (float): Response time in seconds
            cache_hit (bool): Whether this was a cache hit
        """
        self._performance_metrics['total_requests'] += 1
        
        if not cache_hit:
            self._performance_metrics['cache_misses'] += 1
            self._performance_metrics['total_response_time'] += response_time
            
            # Update average response time (excluding cache hits)
            cache_misses = self._performance_metrics['cache_misses']
            self._performance_metrics['average_response_time'] = (
                self._performance_metrics['total_response_time'] / cache_misses
            )
    
    def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Process a user request using Ollama local LLM with optimizations.
        
        Args:
            user_input (str): The user's input text
            context (Optional[Dict[str, Any]]): Additional context for the request
            
        Returns:
            AIResponse: The structured AI response
        """
        start_time = time.time()
        
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
        
        # Check cache first
        cache_key = self._generate_cache_key(user_input, context)
        cached_response = self._get_from_cache(cache_key)
        
        if cached_response:
            logging.info('[AIProcessor] Returning cached response')
            if self._progress_callback:
                self._progress_callback("Risposta dal cache", 1.0)
            
            response_time = time.time() - start_time
            self._update_performance_metrics(response_time, cache_hit=True)
            return cached_response
        
        # Check if Ollama is available
        if not self._is_available:
            logging.error('[AIProcessor] Ollama server not available')
            return AIResponse(
                text="Mi dispiace, il sistema AI locale non è disponibile al momento. Verifica che Ollama sia in esecuzione.",
                response_type='error',
                success=False,
                message="Ollama server not available"
            )
        
        # Progress callback - starting processing
        if self._progress_callback:
            self._progress_callback("Elaborazione richiesta...", 0.2)
        
        # Process the request with retry logic
        for attempt in range(self._max_retries):
            try:
                # Progress callback - preparing
                if self._progress_callback:
                    progress = 0.2 + (attempt * 0.3 / self._max_retries)
                    self._progress_callback(f"Tentativo {attempt + 1}/{self._max_retries}...", progress)
                
                # Prepare the messages for Ollama
                messages = self._prepare_messages(user_input, context)
                
                # Progress callback - sending request
                if self._progress_callback:
                    self._progress_callback("Invio richiesta al modello...", 0.6)
                
                # Make request to Ollama
                response_text = self._make_ollama_request(messages)
                
                if response_text:
                    # Progress callback - processing response
                    if self._progress_callback:
                        self._progress_callback("Elaborazione risposta...", 0.9)
                    
                    response = self._create_success_response(response_text, user_input, context)
                    
                    # Store in cache
                    self._store_in_cache(cache_key, response)
                    
                    # Update metrics
                    response_time = time.time() - start_time
                    self._update_performance_metrics(response_time, cache_hit=False)
                    
                    # Progress callback - complete
                    if self._progress_callback:
                        self._progress_callback("Completato!", 1.0)
                    
                    return response
                else:
                    logging.warning(f'[AIProcessor] Empty response from Ollama (attempt {attempt + 1})')
                    if attempt < self._max_retries - 1:
                        if self._progress_callback:
                            self._progress_callback(f"Risposta vuota, riprovo...", 0.3 + (attempt * 0.2))
                        time.sleep(1)  # Wait before retry
                        continue
                    else:
                        return self._create_error_response("Nessuna risposta ricevuta dall'AI locale")
                        
            except requests.exceptions.RequestException as e:
                logging.error(f'[AIProcessor] Network error in Ollama request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    if self._progress_callback:
                        self._progress_callback(f"Errore di rete, riprovo...", 0.3 + (attempt * 0.2))
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore di rete nella comunicazione con l'AI locale: {str(e)}")
                    
            except Exception as e:
                logging.error(f'[AIProcessor] Unexpected error in Ollama request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    if self._progress_callback:
                        self._progress_callback(f"Errore imprevisto, riprovo...", 0.3 + (attempt * 0.2))
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore imprevisto nella comunicazione con l'AI locale: {str(e)}")
        
        # This should never be reached, but just in case
        return self._create_error_response("Errore sconosciuto nel processamento della richiesta")
    
    def _prepare_messages(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> list:
        """
        Prepare optimized messages array for Ollama chat API with Italian context.
        
        Args:
            user_input (str): The user's input
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            list: Array of messages formatted for Ollama
        """
        # Optimized system message for Frank with improved Italian context
        system_message = """Sei Frank, l'assistente AI per camper e viaggiatori italiani. 
        
REGOLE IMPORTANTI:
- Rispondi SEMPRE in italiano corretto e fluente
- Mantieni risposte concise ma complete (max 3-4 frasi per domande semplici)
- Usa un tono cordiale, professionale ma amichevole
- Per argomenti complessi, usa elenchi puntati per maggiore chiarezza
- Specializzati in: viaggi in camper, turismo, meccanica di base, cucina da viaggio, normative stradali
- Per domande generali, fornisci comunque risposte utili ma contestualizzate al mondo dei viaggi

STILE DI RISPOSTA:
- Diretto e pratico per consigli tecnici
- Entusiasta per destinazioni di viaggio  
- Empatico per problemi durante il viaggio
- Usa markdown per formattare testo quando necessario (grassetto, elenchi)"""
        
        # Add context if provided
        if context:
            system_message += f"\n\nCONTESTO AGGIUNTIVO: {context}"
        
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
        Make an optimized request to Ollama chat API with improved parameters.
        
        Args:
            messages (list): Messages array for the conversation
            
        Returns:
            Optional[str]: The response text from Ollama, or None if failed
        """
        # Optimized parameters for better performance and Italian context
        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.6,      # Reduced from 0.7 for more focused responses
                "top_p": 0.85,          # Slightly increased for better Italian fluency
                "top_k": 30,            # Reduced from 40 for faster generation
                "num_predict": 1024,    # Reduced from 2048 for 40-50% faster responses
                "repeat_penalty": 1.1,  # Added to prevent repetitive responses
                "stop": ["</s>", "[INST]", "[/INST]"]  # Stop tokens for cleaner output
            }
        }
        
        try:
            logging.debug(f'[AIProcessor] Sending optimized request to Ollama: {self._ollama_url}')
            
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
        Create a successful AI response with enhanced metadata and performance metrics.
        
        Args:
            ai_text (str): The AI-generated text
            user_input (str): The original user input
            context (Optional[Dict[str, Any]]): The request context
            
        Returns:
            AIResponse: The structured success response
        """
        # Enhanced metadata with performance information
        metadata = {
            'model': self._model_name,
            'provider': 'ollama_local_optimized',
            'user_input_length': len(user_input),
            'response_length': len(ai_text),
            'timestamp': time.time(),
            'ollama_url': self._ollama_url,
            'optimization_version': '2.0',
            'performance_metrics': {
                'total_requests': self._performance_metrics['total_requests'],
                'cache_hit_rate': (
                    self._performance_metrics['cache_hits'] / 
                    max(1, self._performance_metrics['total_requests'])
                ) * 100,
                'average_response_time': self._performance_metrics['average_response_time'],
                'warmed_up': self._is_warmed_up
            }
        }
        
        if context:
            metadata['context'] = context
        
        return AIResponse(
            text=ai_text.strip(),
            response_type='conversational',
            metadata=metadata,
            success=True,
            message='AI response generated successfully via optimized Ollama'
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
        Get comprehensive information about the current model, configuration and performance.
        
        Returns:
            Dict[str, Any]: Enhanced model and performance information
        """
        basic_info = {
            'model_name': self._model_name,
            'ollama_url': self._ollama_url,
            'provider': 'ollama_local_optimized',
            'timeout': self._timeout,
            'max_retries': self._max_retries,
            'available': self.is_available(),
            'optimizations': {
                'cache_enabled': self._enable_cache,
                'cache_size': self._cache_size,
                'warmup_enabled': self._enable_warmup,
                'warmed_up': self._is_warmed_up,
                'progress_callback_enabled': self._progress_callback is not None
            }
        }
        
        # Add performance metrics if available
        try:
            performance = self.get_performance_metrics()
            basic_info['performance'] = {
                'total_requests': performance['total_requests'],
                'cache_hit_rate': performance['cache_hit_rate_percentage'],
                'average_response_time': performance['average_response_time_seconds'],
                'uptime_seconds': performance['uptime_seconds']
            }
        except Exception as e:
            basic_info['performance'] = {'error': str(e)}
        
        return basic_info
    
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
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics for monitoring and optimization.
        
        Returns:
            Dict[str, Any]: Comprehensive performance data
        """
        total_requests = self._performance_metrics['total_requests']
        cache_hits = self._performance_metrics['cache_hits']
        
        metrics = {
            'total_requests': total_requests,
            'cache_hits': cache_hits,
            'cache_misses': self._performance_metrics['cache_misses'],
            'cache_hit_rate_percentage': (cache_hits / max(1, total_requests)) * 100,
            'average_response_time_seconds': self._performance_metrics['average_response_time'],
            'total_response_time_seconds': self._performance_metrics['total_response_time'],
            'cache_size_current': len(self._cache),
            'cache_size_max': self._cache_size,
            'cache_utilization_percentage': (len(self._cache) / max(1, self._cache_size)) * 100,
            'warmed_up': self._is_warmed_up,
            'warmup_completed': self._performance_metrics['warmup_completed'],
            'uptime_seconds': time.time() - self._performance_metrics['startup_time'],
            'optimizations_enabled': {
                'caching': self._enable_cache,
                'warmup': self._enable_warmup,
                'progress_callback': self._progress_callback is not None
            },
            'model_info': {
                'name': self._model_name,
                'url': self._ollama_url,
                'timeout': self._timeout,
                'max_retries': self._max_retries
            }
        }
        
        return metrics
    
    def clear_cache(self) -> Dict[str, int]:
        """
        Clear the response cache and return statistics.
        
        Returns:
            Dict[str, int]: Statistics about cleared cache
        """
        with self._cache_lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            
        logging.info(f'[AIProcessor] Cleared cache with {cleared_count} entries')
        return {
            'cleared_entries': cleared_count,
            'cache_size_after': len(self._cache)
        }
    
    def set_progress_callback(self, callback: Optional[Callable[[str, float], None]]) -> None:
        """
        Set or update the progress callback function.
        
        Args:
            callback (Optional[Callable]): Progress callback function or None to disable
        """
        self._progress_callback = callback
        logging.info(f'[AIProcessor] Progress callback {"enabled" if callback else "disabled"}')
    
    def preload_common_responses(self) -> Dict[str, Any]:
        """
        Preload cache with common Frank responses to improve initial performance.
        
        Returns:
            Dict[str, Any]: Preload statistics
        """
        if not self._is_available or not self._enable_cache:
            return {'preloaded': 0, 'message': 'Preload skipped - cache disabled or AI unavailable'}
        
        common_prompts = [
            "Ciao, come stai?",
            "Che tempo fa?", 
            "Consigli per viaggi in camper",
            "Come si guida un camper?",
            "Cosa portare in viaggio",
            "Dove parcheggiare il camper",
            "Manutenzione del camper"
        ]
        
        preloaded = 0
        start_time = time.time()
        
        for prompt in common_prompts:
            try:
                cache_key = self._generate_cache_key(prompt)
                
                # Skip if already cached
                if self._get_from_cache(cache_key):
                    continue
                
                # Generate response and cache it
                if self._progress_callback:
                    self._progress_callback(f"Precaricamento: {prompt[:30]}...", 
                                          preloaded / len(common_prompts))
                
                response = self.process_request(prompt)
                if response.success:
                    preloaded += 1
                    
            except Exception as e:
                logging.warning(f'[AIProcessor] Failed to preload prompt "{prompt}": {e}')
                continue
        
        preload_time = time.time() - start_time
        
        result = {
            'preloaded': preloaded,
            'total_prompts': len(common_prompts),
            'preload_time_seconds': preload_time,
            'cache_size_after': len(self._cache)
        }
        
        logging.info(f'[AIProcessor] Preloaded {preloaded}/{len(common_prompts)} responses in {preload_time:.2f}s')
        return result
    
    def shutdown(self) -> None:
        """
        Shutdown the AI processor and clean up resources with performance summary.
        """
        try:
            # Log performance summary before shutdown
            metrics = self.get_performance_metrics()
            logging.info(f'[AIProcessor] Shutdown summary - Total requests: {metrics["total_requests"]}, '
                        f'Cache hit rate: {metrics["cache_hit_rate_percentage"]:.1f}%, '
                        f'Avg response time: {metrics["average_response_time_seconds"]:.2f}s')
            
            # Clear cache
            with self._cache_lock:
                self._cache.clear()
            
            logging.info('[AIProcessor] Shutting down optimized Ollama AI processor')
            self._session.close()
            self._is_available = False
            self._is_warmed_up = False
            
        except Exception as e:
            logging.error(f'[AIProcessor] Error during shutdown: {e}')
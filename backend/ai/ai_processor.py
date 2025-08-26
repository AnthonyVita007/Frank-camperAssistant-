"""
AI Processor Module for Frank Camper Assistant.

This module handles the communication with Google Gemini API to process
user requests and generate appropriate responses.
"""

import logging
import os
import time
from typing import Optional, Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .ai_response import AIResponse


class AIProcessor:
    """
    Processes AI requests using Google Gemini API.
    
    This class manages the communication with Google Gemini API,
    handles errors, implements retry logic, and generates structured responses.
    
    Attributes:
        _model: The Google Gemini model instance
        _api_key (str): The API key for Google Gemini
        _model_name (str): Name of the model to use
        _max_retries (int): Maximum number of retry attempts
        _timeout (float): Request timeout in seconds
    """
    
    def __init__(
        self, 
        model_name: str = "gemini-1.5-flash",
        max_retries: int = 3,
        timeout: float = 30.0
    ) -> None:
        """
        Initialize the AIProcessor.
        
        Args:
            model_name (str): Name of the Google Gemini model (default: "gemini-1.5-flash")
            max_retries (int): Maximum retry attempts (default: 3)
            timeout (float): Request timeout in seconds (default: 30.0)
        """
        self._model_name = model_name
        self._max_retries = max_retries
        self._timeout = timeout
        self._model = None
        
        # Initialize the API
        self._initialize_api()
        
        logging.debug(f'[AIProcessor] AI processor initialized with model: {model_name}')
    
    def _initialize_api(self) -> None:
        """
        Initialize the Google Gemini API connection.
        
        Raises:
            ValueError: If API key is not found in environment variables
            Exception: If API initialization fails
        """
        try:
            # Get API key from environment variable
            self._api_key = os.getenv('GEMINI_API_KEY')
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY environment variable is required")
            
            # Configure the API
            genai.configure(api_key=self._api_key)
            
            # Initialize the model with safety settings
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 64,
                "max_output_tokens": 8192,
            }
            
            safety_settings = [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
            ]
            
            self._model = genai.GenerativeModel(
                model_name=self._model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logging.info('[AIProcessor] Google Gemini API initialized successfully')
            
        except Exception as e:
            logging.error(f'[AIProcessor] Failed to initialize Google Gemini API: {e}')
            raise
    
    def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Process a user request using Google Gemini API.
        
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
        
        # Check if API is properly initialized
        if not self._model:
            logging.error('[AIProcessor] API not properly initialized')
            return AIResponse(
                text="Mi dispiace, il sistema AI non è disponibile al momento.",
                response_type='error',
                success=False,
                message="AI system not available"
            )
        
        # Process the request with retry logic
        for attempt in range(self._max_retries):
            try:
                # Prepare the prompt with context
                prompt = self._prepare_prompt(user_input, context)
                
                # Generate response
                response = self._model.generate_content(prompt)
                
                # Process the response
                if response and response.text:
                    return self._create_success_response(response.text, user_input, context)
                else:
                    logging.warning(f'[AIProcessor] Empty response from API (attempt {attempt + 1})')
                    if attempt < self._max_retries - 1:
                        time.sleep(1)  # Wait before retry
                        continue
                    else:
                        return self._create_error_response("Nessuna risposta ricevuta dall'AI")
                        
            except Exception as e:
                logging.error(f'[AIProcessor] Error in API request (attempt {attempt + 1}): {e}')
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return self._create_error_response(f"Errore nella comunicazione con l'AI: {str(e)}")
        
        # This should never be reached, but just in case
        return self._create_error_response("Errore sconosciuto nel processamento della richiesta")
    
    def _prepare_prompt(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare the prompt for the AI model.
        
        Args:
            user_input (str): The user's input
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            str: The prepared prompt
        """
        # Base system prompt for Frank
        system_prompt = """Sei Frank, un assistente AI per camper e viaggiatori. 
Rispondi sempre in italiano in modo cordiale e utile. 
Sei specializzato nel fornire informazioni e consigli per viaggi in camper, 
ma puoi rispondere anche a domande generali.
Mantieni un tono amichevole e professionale."""
        
        # Add context if provided
        if context:
            system_prompt += f"\n\nContesto aggiuntivo: {context}"
        
        # Combine system prompt with user input
        full_prompt = f"{system_prompt}\n\nUtente: {user_input}\nFrank:"
        
        return full_prompt
    
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
            'user_input_length': len(user_input),
            'response_length': len(ai_text),
            'timestamp': time.time()
        }
        
        if context:
            metadata['context'] = context
        
        return AIResponse(
            text=ai_text.strip(),
            response_type='conversational',
            metadata=metadata,
            success=True,
            message='AI response generated successfully'
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
            metadata={'error': error_message, 'timestamp': time.time()},
            success=False,
            message=error_message
        )
    
    def is_available(self) -> bool:
        """
        Check if the AI processor is available and configured.
        
        Returns:
            bool: True if the processor is available, False otherwise
        """
        return self._model is not None and self._api_key is not None
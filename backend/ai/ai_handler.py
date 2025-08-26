"""
AI Handler Module for Frank Camper Assistant.

This module provides the integration layer between the AI system and the main controller,
managing AI request validation, processing coordination, and logging.
"""

import logging
from typing import Optional, Dict, Any

from .ai_processor import AIProcessor
from .ai_response import AIResponse


class AIHandler:
    """
    Handles AI request processing and integration with the main system.
    
    This class serves as the interface between the main controller and the AI processor,
    providing validation, coordination, and logging for AI interactions.
    
    Attributes:
        _ai_processor (AIProcessor): The AI processor instance
        _is_enabled (bool): Whether AI processing is enabled
    """
    
    def __init__(self, ai_processor: Optional[AIProcessor] = None) -> None:
        """
        Initialize the AIHandler.
        
        Args:
            ai_processor (Optional[AIProcessor]): Custom AI processor instance.
                                                  If None, creates a default one.
        """
        try:
            self._ai_processor = ai_processor or AIProcessor()
            self._is_enabled = self._ai_processor.is_available()
            
            if self._is_enabled:
                logging.info('[AIHandler] AI handler initialized successfully')
            else:
                logging.warning('[AIHandler] AI handler initialized but AI processor is not available')
                
        except Exception as e:
            logging.error(f'[AIHandler] Failed to initialize AI handler: {e}')
            self._ai_processor = None
            self._is_enabled = False
    
    def handle_ai_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Handle an AI request from the user.
        
        This method validates the input, processes the request through the AI processor,
        and returns a structured response.
        
        Args:
            user_input (str): The user's input text
            context (Optional[Dict[str, Any]]): Additional context for the request
            
        Returns:
            AIResponse: The structured AI response
        """
        # Validate input
        if not self._validate_input(user_input):
            logging.warning(f'[AIHandler] Invalid input received: "{user_input}"')
            return AIResponse(
                text="Mi dispiace, non ho ricevuto una richiesta valida.",
                response_type='error',
                success=False,
                message="Invalid input"
            )
        
        # Check if AI is available
        if not self._is_enabled or not self._ai_processor:
            logging.warning('[AIHandler] AI processing requested but not available')
            return AIResponse(
                text="Mi dispiace, il sistema AI non è disponibile al momento. Riprova più tardi.",
                response_type='error',
                success=False,
                message="AI system not available"
            )
        
        # Log the request
        logging.info(f'[AIHandler] Processing AI request: "{user_input[:100]}..."')
        
        try:
            # Process the request
            response = self._ai_processor.process_request(user_input, context)
            
            # Log the response
            if response.success:
                logging.info(f'[AIHandler] AI request processed successfully')
                logging.debug(f'[AIHandler] AI response: "{response.text[:100]}..."')
            else:
                logging.warning(f'[AIHandler] AI request failed: {response.message}')
            
            return response
            
        except Exception as e:
            logging.error(f'[AIHandler] Unexpected error processing AI request: {e}')
            return AIResponse(
                text="Mi dispiace, si è verificato un errore imprevisto. Riprova più tardi.",
                response_type='error',
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    def _validate_input(self, user_input: str) -> bool:
        """
        Validate user input for AI processing.
        
        Args:
            user_input (str): The user input to validate
            
        Returns:
            bool: True if input is valid, False otherwise
        """
        if not user_input or not isinstance(user_input, str):
            return False
        
        # Check if input is not empty after stripping
        if not user_input.strip():
            return False
        
        # Check length limits (reasonable limits for AI processing)
        if len(user_input.strip()) > 5000:  # 5000 character limit
            logging.warning(f'[AIHandler] Input too long: {len(user_input)} characters')
            return False
        
        return True
    
    def is_ai_enabled(self) -> bool:
        """
        Check if AI processing is enabled and available.
        
        Returns:
            bool: True if AI is enabled and available, False otherwise
        """
        return self._is_enabled and self._ai_processor is not None
    
    def get_ai_status(self) -> Dict[str, Any]:
        """
        Get the current status of the AI system.
        
        Returns:
            Dict[str, Any]: Status information about the AI system
        """
        status = {
            'enabled': self._is_enabled,
            'processor_available': self._ai_processor is not None,
            'processor_status': 'unknown'
        }
        
        if self._ai_processor:
            try:
                status['processor_status'] = 'available' if self._ai_processor.is_available() else 'unavailable'
            except Exception as e:
                status['processor_status'] = f'error: {str(e)}'
        
        return status
    
    def shutdown(self) -> None:
        """
        Shutdown the AI handler and clean up resources.
        """
        logging.info('[AIHandler] Shutting down AI handler')
        self._is_enabled = False
        # Note: AIProcessor doesn't need explicit cleanup in this implementation
        # but this method is here for future extensibility
    
    def restart_ai_processor(self) -> bool:
        """
        Restart the AI processor.
        
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            logging.info('[AIHandler] Restarting AI processor')
            self._ai_processor = AIProcessor()
            self._is_enabled = self._ai_processor.is_available()
            
            if self._is_enabled:
                logging.info('[AIHandler] AI processor restarted successfully')
                return True
            else:
                logging.warning('[AIHandler] AI processor restarted but not available')
                return False
                
        except Exception as e:
            logging.error(f'[AIHandler] Failed to restart AI processor: {e}')
            self._ai_processor = None
            self._is_enabled = False
            return False
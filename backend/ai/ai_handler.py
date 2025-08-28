"""
AI Handler Module for Frank Camper Assistant.

This module provides the integration layer between the AI system and the main controller,
managing AI request validation, processing coordination, and logging.
"""

import logging
from typing import Optional, Dict, Any, Callable

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
    
    def __init__(self, ai_processor: Optional[AIProcessor] = None, 
                 progress_callback: Optional[Callable[[str, float], None]] = None) -> None:
        """
        Initialize the AIHandler with optimizations support.
        
        Args:
            ai_processor (Optional[AIProcessor]): Custom AI processor instance.
                                                  If None, creates a default optimized one.
            progress_callback (Optional[Callable]): Callback for progress updates
        """
        try:
            if ai_processor:
                self._ai_processor = ai_processor
            else:
                # Create optimized AI processor with enhanced defaults
                self._ai_processor = AIProcessor(
                    enable_cache=True,
                    enable_warmup=True,
                    cache_size=100,
                    timeout=25.0,  # Reduced timeout for faster responses
                    progress_callback=progress_callback
                )
            
            self._is_enabled = self._ai_processor.is_available()
            
            if self._is_enabled:
                logging.info('[AIHandler] Optimized AI handler initialized successfully')
                
                # Try preloading common responses for better performance
                try:
                    preload_stats = self._ai_processor.preload_common_responses()
                    logging.info(f'[AIHandler] Preloaded {preload_stats["preloaded"]} common responses')
                except Exception as e:
                    logging.warning(f'[AIHandler] Preload failed: {e}')
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
        Get the current status of the AI system with enhanced performance metrics.
        
        Returns:
            Dict[str, Any]: Enhanced status information about the AI system
        """
        status = {
            'enabled': self._is_enabled,
            'processor_available': self._ai_processor is not None,
            'processor_status': 'unknown',
            'optimizations': {
                'caching_enabled': False,
                'warmup_enabled': False,
                'progress_callback_enabled': False
            },
            'performance_metrics': None
        }
        
        if self._ai_processor:
            try:
                status['processor_status'] = 'available' if self._ai_processor.is_available() else 'unavailable'
                
                # Get enhanced model info with optimizations
                model_info = self._ai_processor.get_model_info()
                status['model_info'] = model_info
                
                # Get performance metrics
                performance = self._ai_processor.get_performance_metrics()
                status['performance_metrics'] = performance
                
                # Update optimization status
                status['optimizations'] = model_info.get('optimizations', {})
                
            except Exception as e:
                status['processor_status'] = f'error: {str(e)}'
        
        return status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics from the AI processor.
        
        Returns:
            Dict[str, Any]: Performance metrics or error information
        """
        if not self._ai_processor:
            return {'error': 'AI processor not available'}
        
        try:
            return self._ai_processor.get_performance_metrics()
        except Exception as e:
            return {'error': str(e)}
    
    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear the AI processor cache.
        
        Returns:
            Dict[str, Any]: Cache clearing statistics or error information
        """
        if not self._ai_processor:
            return {'error': 'AI processor not available'}
        
        try:
            return self._ai_processor.clear_cache()
        except Exception as e:
            return {'error': str(e)}
    
    def set_progress_callback(self, callback: Optional[Callable[[str, float], None]]) -> bool:
        """
        Set progress callback for the AI processor.
        
        Args:
            callback (Optional[Callable]): Progress callback function
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._ai_processor:
            return False
        
        try:
            self._ai_processor.set_progress_callback(callback)
            return True
        except Exception as e:
            logging.error(f'[AIHandler] Failed to set progress callback: {e}')
            return False
    
    def shutdown(self) -> None:
        """
        Shutdown the AI handler and clean up resources with performance summary.
        """
        logging.info('[AIHandler] Shutting down optimized AI handler')
        
        # Log performance summary if available
        if self._ai_processor:
            try:
                metrics = self._ai_processor.get_performance_metrics()
                logging.info(f'[AIHandler] Performance summary - Total requests: {metrics["total_requests"]}, '
                            f'Cache hit rate: {metrics["cache_hit_rate_percentage"]:.1f}%')
                
                # Properly shutdown the processor
                self._ai_processor.shutdown()
            except Exception as e:
                logging.warning(f'[AIHandler] Error during processor shutdown: {e}')
        
        self._is_enabled = False
    
    def restart_ai_processor(self) -> bool:
        """
        Restart the AI processor with optimizations.
        
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            logging.info('[AIHandler] Restarting optimized AI processor')
            
            # Create new optimized processor
            self._ai_processor = AIProcessor(
                enable_cache=True,
                enable_warmup=True,
                cache_size=100,
                timeout=25.0
            )
            
            self._is_enabled = self._ai_processor.is_available()
            
            if self._is_enabled:
                logging.info('[AIHandler] Optimized AI processor restarted successfully')
                
                # Try preloading common responses
                try:
                    preload_stats = self._ai_processor.preload_common_responses()
                    logging.info(f'[AIHandler] Preloaded {preload_stats["preloaded"]} responses after restart')
                except Exception as e:
                    logging.warning(f'[AIHandler] Preload after restart failed: {e}')
                
                return True
            else:
                logging.warning('[AIHandler] AI processor restarted but not available')
                return False
                
        except Exception as e:
            logging.error(f'[AIHandler] Failed to restart AI processor: {e}')
            self._ai_processor = None
            self._is_enabled = False
            return False
"""
AI Handler Module for Frank Camper Assistant.

This module provides the integration layer between the AI system and the main controller,
managing AI request validation, processing coordination, and logging.
"""

import logging
import re
from typing import Optional, Dict, Any

from .ai_processor import AIProcessor
from .ai_response import AIResponse
from ..mcp.tools.navigation_tool import NavigationTool


class AIHandler:
    """
    Handles AI request processing and integration with the main system.
    
    This class serves as the interface between the main controller and the AI processor,
    providing validation, coordination, and logging for AI interactions.
    
    Attributes:
        _ai_processor (AIProcessor): The AI processor instance
        _is_enabled (bool): Whether AI processing is enabled
        _navigation_tool (NavigationTool): MCP navigation tool
    """
    
    def __init__(self, ai_processor: Optional[AIProcessor] = None) -> None:
        """
        Initialize the AIHandler.
        
        Args:
            ai_processor (Optional[AIProcessor]): Custom AI processor instance.
                                                  If None, creates a default one.
        """
        # Initialize MCP tools first (these should always work)
        try:
            self._navigation_tool = NavigationTool()
            logging.debug('[AIHandler] Navigation tool initialized successfully')
        except Exception as e:
            logging.error(f'[AIHandler] Failed to initialize navigation tool: {e}')
            self._navigation_tool = None
        
        # Initialize AI processor (this may fail if API key is missing)
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
        and returns a structured response. It also checks for MCP tool triggers.
        
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
        
        # Check for navigation intent first
        navigation_intent = self._detect_navigation_intent(user_input)
        if navigation_intent:
            return self._handle_navigation_request(navigation_intent, user_input)
        
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
    
    def _detect_navigation_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Detect navigation intent in user input.
        
        Args:
            user_input (str): The user input to analyze
            
        Returns:
            Optional[Dict[str, Any]]: Navigation intent data if detected, None otherwise
        """
        input_lower = user_input.lower().strip()
        
        # Navigation trigger patterns
        navigation_patterns = [
            r'(?:vai|portami|naviga|dirigiti|porta)\s+(?:a|verso)\s+(.+?)(?:\s+evitando|\s+senza|$)',
            r'(?:apri|avvia|attiva)\s+(?:il\s+)?navigatore',
            r'(?:come\s+)?(?:arrivo|arrivare)\s+(?:a|verso)\s+(.+?)(?:\s+evitando|\s+senza|$)',
            r'(?:strada|percorso|rotta)\s+(?:per|verso|a)\s+(.+?)(?:\s+evitando|\s+senza|$)',
            r'(?:dove\s+)?(?:è|si trova)\s+(.+)',
            r'navigazione\s+(?:per|verso|a)\s+(.+?)(?:\s+evitando|\s+senza|$)'
        ]
        
        for pattern in navigation_patterns:
            match = re.search(pattern, input_lower)
            if match:
                # Extract destination
                destination_text = match.group(1) if match.groups() else None
                
                # Extract preferences
                preferences = self._extract_navigation_preferences(input_lower)
                
                return {
                    'destination_text': destination_text,
                    'preferences': preferences,
                    'original_input': user_input
                }
        
        return None
    
    def _extract_navigation_preferences(self, user_input: str) -> Dict[str, bool]:
        """
        Extract navigation preferences from user input.
        
        Args:
            user_input (str): The user input to analyze
            
        Returns:
            Dict[str, bool]: Extracted preferences
        """
        preferences = {}
        
        # Check for toll avoidance
        if any(term in user_input for term in ['evita pedaggi', 'senza pedaggi', 'non pedaggi']):
            preferences['avoid_tolls'] = True
        
        # Check for highway avoidance
        if any(term in user_input for term in ['evita autostrade', 'senza autostrade', 'strade statali']):
            preferences['avoid_motorways'] = True
        
        # Check for ferry avoidance
        if any(term in user_input for term in ['evita traghetti', 'senza traghetti']):
            preferences['avoid_ferries'] = True
        
        return preferences
    
    def _handle_navigation_request(self, navigation_intent: Dict[str, Any], original_input: str) -> AIResponse:
        """
        Handle a navigation request using the MCP navigation tool.
        
        Args:
            navigation_intent (Dict[str, Any]): Navigation intent data
            original_input (str): Original user input
            
        Returns:
            AIResponse: Navigation response with action metadata
        """
        logging.info(f'[AIHandler] Handling navigation request: {navigation_intent}')
        
        try:
            # For MVP, use geocoding fallback for common Italian cities
            destination_coords = self._simple_geocode(navigation_intent.get('destination_text', ''))
            
            if not destination_coords:
                return AIResponse(
                    text=f"Mi dispiace, non riesco a trovare la destinazione '{navigation_intent.get('destination_text', '')}'.",
                    response_type='error',
                    success=False,
                    message="Destination not found"
                )
            
            # Prepare navigation parameters
            nav_params = {
                'destination': destination_coords,
                'preferences': navigation_intent.get('preferences', {})
            }
            
            # Execute navigation tool
            if self._navigation_tool:
                tool_result = self._navigation_tool.execute(nav_params)
                
                if tool_result.success:
                    # Create AI response with navigation action
                    response_text = f"Imposto il percorso verso {destination_coords.get('address', 'destinazione')}. " + tool_result.message
                    
                    return AIResponse(
                        text=response_text,
                        response_type='navigation',
                        success=True,
                        metadata={
                            'action': 'open_navigator',
                            'route_payload': tool_result.data
                        }
                    )
                else:
                    return AIResponse(
                        text=f"Mi dispiace, non riesco a calcolare il percorso: {tool_result.message}",
                        response_type='error',
                        success=False,
                        message=tool_result.message
                    )
            else:
                return AIResponse(
                    text="Mi dispiace, il sistema di navigazione non è disponibile.",
                    response_type='error',
                    success=False,
                    message="Navigation tool not available"
                )
                
        except Exception as e:
            logging.error(f'[AIHandler] Navigation request failed: {e}')
            return AIResponse(
                text="Mi dispiace, si è verificato un errore durante il calcolo del percorso.",
                response_type='error',
                success=False,
                message=f"Navigation error: {str(e)}"
            )
    
    def _simple_geocode(self, destination_text: str) -> Optional[Dict[str, Any]]:
        """
        Simple geocoding for common Italian destinations (MVP fallback).
        
        Args:
            destination_text (str): Destination text to geocode
            
        Returns:
            Optional[Dict[str, Any]]: Coordinates if found
        """
        if not destination_text:
            return None
        
        # Simple geocoding database for common Italian cities
        geocoding_db = {
            'roma': {'lat': 41.9028, 'lon': 12.4964, 'address': 'Roma, Italia'},
            'milano': {'lat': 45.4642, 'lon': 9.1900, 'address': 'Milano, Italia'},
            'napoli': {'lat': 40.8518, 'lon': 14.2681, 'address': 'Napoli, Italia'},
            'firenze': {'lat': 43.7696, 'lon': 11.2558, 'address': 'Firenze, Italia'},
            'venezia': {'lat': 45.4408, 'lon': 12.3155, 'address': 'Venezia, Italia'},
            'torino': {'lat': 45.0703, 'lon': 7.6869, 'address': 'Torino, Italia'},
            'bologna': {'lat': 44.4949, 'lon': 11.3426, 'address': 'Bologna, Italia'},
            'genova': {'lat': 44.4056, 'lon': 8.9463, 'address': 'Genova, Italia'},
            'palermo': {'lat': 38.1157, 'lon': 13.3615, 'address': 'Palermo, Italia'},
            'bari': {'lat': 41.1171, 'lon': 16.8719, 'address': 'Bari, Italia'}
        }
        
        # Normalize destination text
        dest_normalized = destination_text.lower().strip()
        
        # Remove common words
        for word in ['a', 'verso', 'città', 'di']:
            dest_normalized = dest_normalized.replace(word, '').strip()
        
        # Check for matches
        for city, coords in geocoding_db.items():
            if city in dest_normalized or dest_normalized in city:
                logging.info(f'[AIHandler] Geocoded "{destination_text}" to {city}')
                return coords
        
        logging.warning(f'[AIHandler] Could not geocode destination: {destination_text}')
        return None
    
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
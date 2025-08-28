"""
AI Handler Module for Frank Camper Assistant.

This module provides the integration layer between the AI system and the main controller,
managing AI request validation, processing coordination, and logging.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
from typing import Optional, Dict, Any, List

from .ai_processor import AIProcessor
from .ai_response import AIResponse


class AIHandler:
    """
    Handles AI request processing and integration with the main system.
    
    This class serves as the interface between the main controller and the AI processor,
    providing validation, coordination, and logging for AI interactions. Now includes
    MCP (Model Context Protocol) integration for tool-based interactions.
    
    Attributes:
        _ai_processor (AIProcessor): The AI processor instance
        _is_enabled (bool): Whether AI processing is enabled
        _mcp_handler (Optional): The MCP handler for tool interactions
        _tool_detection_enabled (bool): Whether to detect tool usage intents
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE AI HANDLER CON SUPPORTO MCP
    #----------------------------------------------------------------
    def __init__(self, ai_processor: Optional[AIProcessor] = None, mcp_handler: Optional = None) -> None: # type: ignore
        """
        Initialize the AIHandler with optional MCP support.
        
        Args:
            ai_processor (Optional[AIProcessor]): Custom AI processor instance.
                                                  If None, creates a default one.
            mcp_handler (Optional): MCP handler for tool interactions.
                                   If None, tool features will be disabled.
        """
        try:
            self._ai_processor = ai_processor or AIProcessor()
            self._is_enabled = self._ai_processor.is_available()
            
            # MCP Integration
            self._mcp_handler = mcp_handler
            self._tool_detection_enabled = mcp_handler is not None
            
            if self._is_enabled:
                logging.info('[AIHandler] AI handler initialized successfully')
                if self._tool_detection_enabled:
                    logging.info('[AIHandler] MCP tool integration enabled')
                else:
                    logging.info('[AIHandler] MCP tool integration disabled (no MCP handler)')
            else:
                logging.warning('[AIHandler] AI handler initialized but AI processor is not available')
                
        except Exception as e:
            logging.error(f'[AIHandler] Failed to initialize AI handler: {e}')
            self._ai_processor = None
            self._is_enabled = False
            self._mcp_handler = None
            self._tool_detection_enabled = False
    
    #----------------------------------------------------------------
    # GESTIONE RICHIESTE AI CON SUPPORTO MCP
    #----------------------------------------------------------------
    def handle_ai_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Handle an AI request from the user with MCP tool detection.
        
        This method validates the input, detects if tools are needed, and either
        processes the request through MCP tools or regular AI conversation.
        
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
            # Step 1: Detect if this request needs tools
            if self._tool_detection_enabled:
                tool_intent = self._detect_tool_intent(user_input, context)
                
                if tool_intent:
                    # Handle request through MCP system
                    return self._handle_tool_request(user_input, tool_intent, context)
            
            # Step 2: Handle as regular conversational AI
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
    
    #----------------------------------------------------------------
    # RILEVAMENTO INTENTI PER STRUMENTI MCP
    #----------------------------------------------------------------
    def _detect_tool_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Detect if the user input requires tool usage.
        
        This method analyzes the user input to determine if it contains
        intents that would benefit from tool execution rather than
        conversational AI.
        
        Args:
            user_input (str): The user's input text
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            Optional[Dict[str, Any]]: Tool intent information if detected, None otherwise
        """
        try:
            if not self._mcp_handler:
                return None
            
            # Convert to lowercase for pattern matching
            input_lower = user_input.lower().strip()
            
            # Define intent patterns and their corresponding tool categories
            intent_patterns = {
                'navigation': [
                    'rotta', 'percorso', 'navigazione', 'direzione', 'strada',
                    'portami', 'andare', 'destinazione', 'gps', 'mappa',
                    'autostrada', 'pedaggi', 'evita', 'traffico'
                ],
                'vehicle': [
                    'stato veicolo', 'carburante', 'benzina', 'gasolio', 'motore',
                    'pressione pneumatici', 'temperatura', 'diagnostica', 'obd',
                    'batteria', 'liquidi', 'livello olio'
                ],
                'weather': [
                    'meteo', 'tempo', 'pioggia', 'sole', 'temperature', 'previsioni',
                    'clima', 'nuvole', 'vento', 'temporale', 'neve'
                ],
                'maintenance': [
                    'manutenzione', 'scadenza', 'tagliando', 'revisione', 
                    'promemoria', 'controllo', 'sostituzione', 'filtro',
                    'cambio olio', 'freni'
                ]
            }
            
            # Check for intent matches
            detected_intents = {}
            
            for category, patterns in intent_patterns.items():
                for pattern in patterns:
                    if pattern in input_lower:
                        if category not in detected_intents:
                            detected_intents[category] = []
                        detected_intents[category].append(pattern)
            
            # If we found intent patterns, return tool intent
            if detected_intents:
                # Find the most likely intent (category with most matches)
                primary_intent = max(detected_intents.keys(), key=lambda k: len(detected_intents[k]))
                
                tool_intent = {
                    'primary_category': primary_intent,
                    'detected_patterns': detected_intents,
                    'confidence': len(detected_intents[primary_intent]) / len(intent_patterns[primary_intent]),
                    'raw_input': user_input
                }
                
                logging.debug(f'[AIHandler] Detected tool intent: {primary_intent} (confidence: {tool_intent["confidence"]:.2f})')
                return tool_intent
            
            return None
            
        except Exception as e:
            logging.error(f'[AIHandler] Error detecting tool intent: {e}')
            return None
    
    #----------------------------------------------------------------
    # GESTIONE RICHIESTE TRAMITE STRUMENTI MCP
    #----------------------------------------------------------------
    def _handle_tool_request(
        self, 
        user_input: str, 
        tool_intent: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> AIResponse:
        """
        Handle a request that requires tool execution.
        
        This method coordinates between AI understanding and tool execution,
        extracting parameters from natural language and executing appropriate tools.
        
        Args:
            user_input (str): The user's input text
            tool_intent (Dict[str, Any]): Detected tool intent information
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            AIResponse: Response from tool execution or error
        """
        try:
            primary_category = tool_intent.get('primary_category')
            confidence = tool_intent.get('confidence', 0.0)
            
            logging.info(f'[AIHandler] Processing tool request for category: {primary_category}')
            
            # Get available tools for this category
            available_tools = self._mcp_handler.get_tools_by_category(primary_category)
            
            if not available_tools:
                logging.warning(f'[AIHandler] No tools available for category: {primary_category}')
                # Fallback to conversational AI
                return self._fallback_to_conversation(user_input, f"Categoria strumenti '{primary_category}' non disponibile")
            
            # For now, use the first available tool in the category
            # In a more sophisticated implementation, we would use AI to choose the best tool
            selected_tool = available_tools[0]
            tool_name = selected_tool.get('name')
            
            if not tool_name:
                logging.error(f'[AIHandler] Invalid tool information: {selected_tool}')
                return self._fallback_to_conversation(user_input, "Informazioni strumento non valide")
            
            # Extract parameters using AI
            parameters = self._extract_tool_parameters(user_input, tool_name, selected_tool, context)
            
            # Execute the tool
            logging.info(f'[AIHandler] Executing tool: {tool_name} with parameters: {parameters}')
            tool_result = self._mcp_handler.execute_tool(tool_name, parameters)
            
            # Convert tool result to AI response
            return self._convert_tool_result_to_ai_response(tool_result, tool_name, user_input)
            
        except Exception as e:
            logging.error(f'[AIHandler] Error handling tool request: {e}')
            return self._fallback_to_conversation(user_input, f"Errore nell'esecuzione dello strumento: {str(e)}")
    
    def _extract_tool_parameters(
        self, 
        user_input: str, 
        tool_name: str, 
        tool_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract parameters for tool execution from natural language input.
        
        This method uses AI to understand the user's intent and extract
        the specific parameters needed for tool execution.
        
        Args:
            user_input (str): The user's input text
            tool_name (str): Name of the tool to execute
            tool_info (Dict[str, Any]): Information about the tool
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            Dict[str, Any]: Extracted parameters for tool execution
        """
        try:
            # Get the tool's parameter schema
            schema = tool_info.get('parameters_schema', {})
            required_params = schema.get('required', [])
            
            # Simple parameter extraction based on tool type
            # In a real implementation, this would use more sophisticated NLP
            
            parameters = {}
            input_lower = user_input.lower()
            
            # Navigation tool parameter extraction
            if 'navigation' in tool_name.lower() or 'route' in tool_name.lower():
                # Extract destination
                if 'destination' in required_params:
                    destination = self._extract_destination(user_input)
                    if destination:
                        parameters['destination'] = destination
                
                # Extract preferences
                if 'preferences' in schema.get('properties', {}):
                    preferences = {}
                    if 'pedaggi' in input_lower and ('evita' in input_lower or 'senza' in input_lower):
                        preferences['avoid_tolls'] = True
                    if 'autostrada' in input_lower and ('evita' in input_lower or 'senza' in input_lower):
                        preferences['avoid_highways'] = True
                    if preferences:
                        parameters['preferences'] = preferences
            
            # Weather tool parameter extraction
            elif 'weather' in tool_name.lower() or 'meteo' in tool_name.lower():
                if 'location' in required_params:
                    location = self._extract_location(user_input)
                    if location:
                        parameters['location'] = location
                    else:
                        parameters['location'] = 'current'  # Default to current location
            
            # Vehicle tool parameter extraction
            elif 'vehicle' in tool_name.lower():
                if 'system' in schema.get('properties', {}):
                    if 'carburante' in input_lower or 'benzina' in input_lower:
                        parameters['system'] = 'fuel'
                    elif 'pneumatici' in input_lower:
                        parameters['system'] = 'tires'
                    elif 'motore' in input_lower:
                        parameters['system'] = 'engine'
                    else:
                        parameters['system'] = 'general'
            
            # Add context if provided
            if context:
                parameters['context'] = context
            
            logging.debug(f'[AIHandler] Extracted parameters for {tool_name}: {parameters}')
            return parameters
            
        except Exception as e:
            logging.error(f'[AIHandler] Error extracting tool parameters: {e}')
            return {}
    
    def _extract_destination(self, user_input: str) -> Optional[str]:
        """
        Extract destination from user input for navigation tools.
        
        Args:
            user_input (str): The user's input text
            
        Returns:
            Optional[str]: Extracted destination or None
        """
        # Simple destination extraction patterns
        # In a real implementation, this would use more sophisticated NLP
        
        patterns = [
            r'(?:a |verso |per |in |su )?([A-Z][a-zA-Z\s]+?)(?:\s|$|,)',
            r'(?:portami|andare|dirigere).*?(?:a |verso |per |in )([A-Z][a-zA-Z\s]+?)(?:\s|$|,)',
            r'rotta.*?(?:per |verso |a )([A-Z][a-zA-Z\s]+?)(?:\s|$|,)'
        ]
        
        import re
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                destination = match.group(1).strip()
                if len(destination) > 2:  # Minimum length check
                    return destination
        
        return None
    
    def _extract_location(self, user_input: str) -> Optional[str]:
        """
        Extract location from user input for weather tools.
        
        Args:
            user_input (str): The user's input text
            
        Returns:
            Optional[str]: Extracted location or None
        """
        # Simple location extraction for weather
        patterns = [
            r'(?:a |in |su |per )([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\?)',
            r'meteo.*?(?:a |in |di )([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\?)'
        ]
        
        import re
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                location = match.group(1).strip()
                if len(location) > 2:
                    return location
        
        return None
    
    def _convert_tool_result_to_ai_response(
        self, 
        tool_result, 
        tool_name: str, 
        original_input: str
    ) -> AIResponse:
        """
        Convert a tool execution result to an AIResponse.
        
        Args:
            tool_result: The result from tool execution
            tool_name (str): Name of the executed tool
            original_input (str): The original user input
            
        Returns:
            AIResponse: Converted AI response
        """
        try:
            # Import here to avoid circular imports
            from ..mcp.mcp_tool import ToolResultStatus
            
            if tool_result.status == ToolResultStatus.SUCCESS:
                return AIResponse(
                    text=str(tool_result.data) if tool_result.data else tool_result.message,
                    response_type='tool_response',
                    metadata={
                        'tool_name': tool_name,
                        'tool_status': tool_result.status.value,
                        'original_input': original_input,
                        'tool_metadata': tool_result.metadata or {}
                    },
                    success=True,
                    message=f"Tool '{tool_name}' executed successfully"
                )
            elif tool_result.status == ToolResultStatus.REQUIRES_CONFIRMATION:
                return AIResponse(
                    text=tool_result.confirmation_message or tool_result.message,
                    response_type='confirmation_required',
                    metadata={
                        'tool_name': tool_name,
                        'tool_status': tool_result.status.value,
                        'requires_action': True,
                        'original_input': original_input
                    },
                    suggested_actions=['conferma', 'annulla'],
                    success=True,
                    message="Tool execution requires user confirmation"
                )
            else:
                # Error or other status
                return AIResponse(
                    text=f"Si è verificato un problema: {tool_result.message}",
                    response_type='tool_error',
                    metadata={
                        'tool_name': tool_name,
                        'tool_status': tool_result.status.value,
                        'error_message': tool_result.message,
                        'original_input': original_input
                    },
                    success=False,
                    message=f"Tool '{tool_name}' execution failed"
                )
                
        except Exception as e:
            logging.error(f'[AIHandler] Error converting tool result: {e}')
            return AIResponse(
                text="Si è verificato un errore nell'elaborazione del risultato.",
                response_type='error',
                success=False,
                message=f"Error converting tool result: {str(e)}"
            )
    
    def _fallback_to_conversation(self, user_input: str, reason: str) -> AIResponse:
        """
        Fallback to regular conversational AI when tool execution fails.
        
        Args:
            user_input (str): The original user input
            reason (str): Reason for fallback
            
        Returns:
            AIResponse: Conversational AI response
        """
        try:
            logging.info(f'[AIHandler] Falling back to conversational AI: {reason}')
            
            # Process as regular AI request
            response = self._ai_processor.process_request(user_input)
            
            # Add fallback information to metadata
            if response.metadata is None:
                response.metadata = {}
            response.metadata['fallback_reason'] = reason
            response.metadata['was_tool_request'] = True
            
            return response
            
        except Exception as e:
            logging.error(f'[AIHandler] Error in fallback to conversation: {e}')
            return AIResponse(
                text="Mi dispiace, si è verificato un errore nell'elaborazione della richiesta.",
                response_type='error',
                success=False,
                message=f"Fallback error: {str(e)}"
            )
    
    #----------------------------------------------------------------
    # STREAMING CON SUPPORTO MCP
    #----------------------------------------------------------------
    def handle_ai_stream(self, user_input: str, context: Optional[Dict[str, Any]] = None):
        """
        Handle a streaming AI request from the user with MCP tool detection.
        
        This method provides streaming AI responses by yielding text chunks
        as they are generated, enabling real-time response rendering.
        Note: Tool execution is not streamed, only conversational responses.
        
        Args:
            user_input (str): The user's input text
            context (Optional[Dict[str, Any]]): Additional context for the request
            
        Yields:
            str: Text chunks as they are generated by the AI
        """
        # Validate input
        if not self._validate_input(user_input):
            logging.warning(f'[AIHandler] Invalid input for streaming request: "{user_input}"')
            yield "Mi dispiace, non ho ricevuto una richiesta valida."
            return
        
        # Check if AI is available
        if not self._is_enabled or not self._ai_processor:
            logging.warning('[AIHandler] AI streaming requested but not available')
            yield "Mi dispiace, il sistema AI non è disponibile al momento. Riprova più tardi."
            return
        
        # Log the streaming request
        logging.info(f'[AIHandler] Processing streaming AI request: "{user_input[:100]}..."')
        
        try:
            # Check for tool intent first
            if self._tool_detection_enabled:
                tool_intent = self._detect_tool_intent(user_input, context)
                
                if tool_intent:
                    # For tool requests, we don't stream - execute and return result
                    tool_response = self._handle_tool_request(user_input, tool_intent, context)
                    yield tool_response.text
                    return
            
            # Process as streaming conversational AI
            for chunk in self._ai_processor.stream_request(user_input, context):
                if chunk:
                    yield chunk
            
            logging.info('[AIHandler] Streaming AI request completed successfully')
            
        except Exception as e:
            logging.error(f'[AIHandler] Unexpected error in streaming AI request: {e}')
            yield "Mi dispiace, si è verificato un errore imprevisto durante la generazione della risposta."
    
    #----------------------------------------------------------------
    # METODI ESISTENTI (invariati)
    #----------------------------------------------------------------
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
    
    def is_mcp_enabled(self) -> bool:
        """
        Check if MCP tool integration is enabled and available.
        
        Returns:
            bool: True if MCP is enabled and available, False otherwise
        """
        return self._tool_detection_enabled and self._mcp_handler is not None
    
    def get_ai_status(self) -> Dict[str, Any]:
        """
        Get the current status of the AI system including MCP integration.
        
        Returns:
            Dict[str, Any]: Status information about the AI system
        """
        status = {
            'enabled': self._is_enabled,
            'processor_available': self._ai_processor is not None,
            'processor_status': 'unknown',
            'mcp_enabled': self._tool_detection_enabled,
            'mcp_handler_available': self._mcp_handler is not None
        }
        
        if self._ai_processor:
            try:
                status['processor_status'] = 'available' if self._ai_processor.is_available() else 'unavailable'
            except Exception as e:
                status['processor_status'] = f'error: {str(e)}'
        
        if self._mcp_handler:
            try:
                mcp_status = self._mcp_handler.get_system_status()
                status['mcp_status'] = mcp_status
            except Exception as e:
                status['mcp_status'] = f'error: {str(e)}'
        
        return status
    
    def shutdown(self) -> None:
        """
        Shutdown the AI handler and clean up resources.
        """
        logging.info('[AIHandler] Shutting down AI handler')
        self._is_enabled = False
        self._tool_detection_enabled = False
        
        # Shutdown MCP handler if available
        if self._mcp_handler:
            try:
                self._mcp_handler.shutdown()
            except Exception as e:
                logging.error(f'[AIHandler] Error shutting down MCP handler: {e}')
        
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
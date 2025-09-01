"""
Tool Lifecycle Agent Module for Frank Camper Assistant.

This module provides the ToolLifecycleAgent class which manages the complete
lifecycle of tool execution independently from the main LLM, including parameter
collection, validation, execution, and cleanup.
"""

#----------------------------------------------------------------
# IMPORT E DIPENDENZE
#----------------------------------------------------------------
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
from .ai_response import AIResponse
from .intent_prompts import get_clarification_prompt


#----------------------------------------------------------------
# TOOL SESSION DATA STRUCTURE (LIFECYCLE MANAGEMENT)
#----------------------------------------------------------------
@dataclass
class ToolSessionState:
    """
    State information for an active tool session.
    
    This tracks all information needed to manage a tool lifecycle
    from parameter collection through execution to completion.
    """
    # Tool identification
    tool_name: str
    tool_info: Dict[str, Any]
    schema: Dict[str, Any]
    
    # Session state
    state: str  # clarifying, ready_to_start, running, finished, canceled
    active: bool
    
    # Parameters and requirements
    required: List[str]
    parameters: Dict[str, Any]
    missing: List[str]
    
    # Clarification tracking
    last_question: Optional[str]
    asked_count: int
    
    # Lifecycle tracking
    started_at: float
    created_at: float
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.started_at is None:
            self.started_at = time.time()


class ToolLifecycleAgent:
    """
    Agent responsible for managing the complete lifecycle of tool execution.
    
    This agent handles the tool lifecycle independently from the main LLM:
    - Parameter collection and validation
    - Clarification questions via LLM
    - Tool execution via MCP
    - State management and event emission
    - Cancellation handling
    
    The agent emits the same events as the existing system to maintain UI compatibility.
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE
    #----------------------------------------------------------------
    def __init__(
        self,
        ai_processor,  # AI processor for generating clarification questions
        mcp_handler,   # MCP handler for tool execution
        event_emitter: Callable[[str, Dict[str, Any]], None],  # Function to emit backend_action events
        on_complete: Callable[[str, Dict[str, Any]], None]     # Callback when lifecycle completes
    ) -> None:
        """
        Initialize the ToolLifecycleAgent.
        
        Args:
            ai_processor: AI processor for generating clarification questions
            mcp_handler: MCP handler for tool execution
            event_emitter: Function to emit backend_action events
            on_complete: Callback function when tool lifecycle completes
        """
        self._ai_processor = ai_processor
        self._mcp_handler = mcp_handler
        self._event_emitter = event_emitter
        self._on_complete = on_complete
        
        # Active tool sessions per session_id
        self._tool_sessions: Dict[str, ToolSessionState] = {}
        
        logging.info('[ToolLifecycleAgent] Initialized successfully')
    
    #----------------------------------------------------------------
    # PUBLIC API METHODS
    #----------------------------------------------------------------
    def start(
        self, 
        session_id: str, 
        tool_name: str, 
        tool_info: Dict[str, Any], 
        initial_params: Dict[str, Any]
    ) -> Optional[AIResponse]:
        """
        Start a new tool lifecycle session.
        
        Args:
            session_id (str): Session identifier
            tool_name (str): Name of the tool to execute
            tool_info (Dict[str, Any]): Tool information including schema
            initial_params (Dict[str, Any]): Initial parameters extracted
            
        Returns:
            Optional[AIResponse]: Response if tool executes immediately, None if clarification needed
        """
        try:
            # Calculate missing required parameters
            required_params = tool_info.get('parameters_schema', {}).get('required', [])
            missing_required = []
            
            for param in required_params:
                if not self._is_parameter_present(param, initial_params):
                    missing_required.append(param)
            
            # Create tool session
            self._create_tool_session(session_id, tool_name, tool_info, initial_params, missing_required)
            
            # Emit tool_selected event
            self._event_emitter('tool_selected', {
                'tool_name': tool_name
            })
            
            # Start the lifecycle based on missing parameters
            if missing_required:
                self._start_clarification_phase(session_id)
            else:
                self._move_to_ready_to_start(session_id)
                # Automatically execute if all parameters are ready
                return self._execute_tool(session_id)
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error starting tool lifecycle: {e}')
            self._on_complete(session_id, {
                'outcome': 'error',
                'error': str(e)
            })
    
    def is_active(self, session_id: str) -> bool:
        """
        Check if there's an active tool session for the given session ID.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if tool session is active, False otherwise
        """
        if session_id not in self._tool_sessions:
            return False
        
        session = self._tool_sessions[session_id]
        return session.active and session.state not in ['finished', 'canceled']
    
    def handle_user_message(self, session_id: str, text: str) -> AIResponse:
        """
        Handle user message during an active tool session.
        
        Args:
            session_id (str): Session identifier
            text (str): User input text
            
        Returns:
            AIResponse: Response to send back to user
        """
        try:
            if not self.is_active(session_id):
                return AIResponse(
                    text="Nessuna sessione tool attiva.",
                    success=False,
                    response_type="error"
                )
            
            session = self._tool_sessions[session_id]
            text_lower = text.lower().strip()
            
            # Handle cancellation requests
            if any(cancel_word in text_lower for cancel_word in ['annulla', 'cancella', 'stop', 'cancel']):
                return self.cancel(session_id, "user_request")
            
            # Handle based on current state
            if session.state == 'clarifying':
                return self._handle_clarification_input(session_id, text)
            elif session.state == 'ready_to_start':
                # Already ready, just execute
                return self._execute_tool(session_id)
            elif session.state == 'running':
                return AIResponse(
                    text="Tool in esecuzione, attendere...",
                    success=True,
                    response_type="tool_status"
                )
            else:
                return AIResponse(
                    text=f"Stato tool non gestito: {session.state}",
                    success=False,
                    response_type="error"
                )
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error handling user message: {e}')
            return AIResponse(
                text="Errore nella gestione del messaggio.",
                success=False,
                response_type="error"
            )
    
    def cancel(self, session_id: str, reason: str = "user_cancel") -> AIResponse:
        """
        Cancel an active tool session.
        
        Args:
            session_id (str): Session identifier
            reason (str): Reason for cancellation
            
        Returns:
            AIResponse: Cancellation confirmation
        """
        try:
            if session_id not in self._tool_sessions:
                return AIResponse(
                    text="Nessuna sessione tool da annullare.",
                    success=True,
                    response_type="info"
                )
            
            session = self._tool_sessions[session_id]
            
            # Emit cancellation events
            self._event_emitter('tool_session_canceled', {
                'session_id': session_id,
                'tool_name': session.tool_name,
                'state': session.state,
                'reason': reason,
                'params_partial': session.parameters
            })
            
            # Cleanup session
            self._cleanup_tool_session(session_id, 'canceled', 'user_canceled', f'Tool {session.tool_name} canceled by user')
            
            # Notify completion
            self._on_complete(session_id, {
                'outcome': 'canceled',
                'reason': reason
            })
            
            return AIResponse(
                text=f"Tool {session.tool_name} annullato.",
                success=True,
                response_type="tool_canceled"
            )
            
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error canceling tool session: {e}')
            return AIResponse(
                text="Errore nell'annullamento del tool.",
                success=False,
                response_type="error"
            )
    
    #----------------------------------------------------------------
    # PRIVATE LIFECYCLE METHODS
    #----------------------------------------------------------------
    def _create_tool_session(
        self, 
        session_id: str, 
        tool_name: str, 
        tool_info: Dict[str, Any], 
        initial_params: Dict[str, Any], 
        missing_required: List[str]
    ) -> None:
        """
        Create a new tool session for lifecycle management.
        """
        try:
            # Determine initial state based on missing parameters
            initial_state = "clarifying" if missing_required else "ready_to_start"
            
            # Create tool session
            session = ToolSessionState(
                tool_name=tool_name,
                tool_info=tool_info,
                schema=tool_info.get('parameters_schema', {}),
                state=initial_state,
                active=True,
                required=tool_info.get('parameters_schema', {}).get('required', []),
                parameters=initial_params.copy(),
                missing=missing_required.copy(),
                last_question=None,
                asked_count=0,
                started_at=time.time(),
                created_at=time.time()
            )
            
            self._tool_sessions[session_id] = session
            
            # Emit tool lifecycle started event
            self._event_emitter('tool_lifecycle_started', {
                'session_id': session_id,
                'tool_name': tool_name,
                'state': initial_state,
                'missing_required': missing_required,
                'params_partial': initial_params,
                'timestamp': session.created_at
            })
            
            logging.info(f'[ToolLifecycleAgent] Created tool session {session_id} for {tool_name} in state {initial_state}')
            
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error creating tool session: {e}')
            raise
    
    def _start_clarification_phase(self, session_id: str) -> None:
        """
        Start the clarification phase for missing parameters.
        """
        try:
            session = self._tool_sessions[session_id]
            question = self._generate_clarification_question(session_id)
            
            if question:
                session.last_question = question
                session.asked_count += 1
                
                # Here we would normally send the question to the user via AI response
                # but since this is called from start(), the question will be asked
                # when the first user message arrives in clarifying state
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error starting clarification phase: {e}')
    
    def _handle_clarification_input(self, session_id: str, user_input: str) -> AIResponse:
        """
        Handle user input during the clarification phase.
        """
        try:
            session = self._tool_sessions[session_id]
            
            # Try to extract parameters from user input
            extracted_params = self._extract_parameters_from_input(user_input, session.missing, session.tool_name)
            
            # Check if this input is relevant to tool parameters
            if not extracted_params and not self._is_input_tool_relevant(user_input, session.missing):
                # Emit gating notice
                self._event_emitter('tool_gating_notice', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'state': session.state,
                    'message': f'Modalità Tool attiva: accetto solo {", ".join(session.missing)} o "annulla"',
                    'missing_required': session.missing
                })
                
                return AIResponse(
                    text=f'Modalità Tool attiva per {session.tool_name}. Fornisci: {", ".join(session.missing)} oppure scrivi "annulla".',
                    success=True,
                    response_type="tool_gating"
                )
            
            # Update parameters
            if extracted_params:
                for param_name, param_value in extracted_params.items():
                    session.parameters[param_name] = param_value
                    
                    # Emit parameter received event
                    self._event_emitter('tool_parameter_received', {
                        'session_id': session_id,
                        'tool_name': session.tool_name,
                        'param_name': param_name,
                        'param_value': param_value,
                        'params_partial': session.parameters.copy(),
                        'missing_required': []  # Will be updated below
                    })
                
                # Recalculate missing parameters
                session.missing = []
                for param in session.required:
                    if not self._is_parameter_present(param, session.parameters):
                        session.missing.append(param)
            
            # Check if we have all required parameters
            if not session.missing:
                self._move_to_ready_to_start(session_id)
                return self._execute_tool(session_id)
            else:
                # Still missing parameters, ask for more
                question = self._generate_clarification_question(session_id)
                session.last_question = question
                session.asked_count += 1
                
                return AIResponse(
                    text=question,
                    success=True,
                    response_type="ai_response"
                )
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error handling clarification input: {e}')
            return AIResponse(
                text="Errore nella gestione dei parametri.",
                success=False,
                response_type="error"
            )
    
    def _move_to_ready_to_start(self, session_id: str) -> None:
        """
        Move session to ready_to_start state and emit event.
        """
        try:
            session = self._tool_sessions[session_id]
            session.state = 'ready_to_start'
            
            self._event_emitter('tool_parameters_ready', {
                'session_id': session_id,
                'tool_name': session.tool_name,
                'parameters': session.parameters.copy()
            })
            
            # Also emit the legacy event name for compatibility
            self._event_emitter('tool_ready_to_start', {
                'session_id': session_id,
                'tool_name': session.tool_name
            })
            
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error moving to ready_to_start: {e}')
    
    def _execute_tool(self, session_id: str) -> AIResponse:
        """
        Execute the tool with collected parameters.
        """
        try:
            session = self._tool_sessions[session_id]
            session.state = 'running'
            
            # Emit tool_started event
            self._event_emitter('tool_started', {
                'session_id': session_id,
                'tool_name': session.tool_name,
                'parameters': session.parameters.copy()
            })
            
            # Execute via MCP
            if not self._mcp_handler:
                raise Exception("MCP handler not available")
            
            # Normalize parameters
            normalized_params = self._normalize_parameters(session.parameters, session.tool_name)
            
            # Execute tool
            tool_result = self._mcp_handler.execute_tool(session.tool_name, normalized_params)
            
            # Handle result
            success = False
            if tool_result:
                # Check if status indicates success (handle both enum and boolean)
                if hasattr(tool_result.status, 'value'):
                    success = tool_result.status.value == "success"
                elif isinstance(tool_result.status, bool):
                    success = tool_result.status
                elif tool_result.status == "success":
                    success = True
            
            if success:
                # Emit tool_result and tool_finished events
                self._event_emitter('tool_result', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'result': tool_result.data,
                    'success': True
                })
                
                self._event_emitter('tool_finished', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'status': str(True)
                })
                
                # Cleanup session
                self._cleanup_tool_session(session_id, 'finished', str(True), f'Tool {session.tool_name} completed')
                
                # Notify completion
                self._on_complete(session_id, {
                    'outcome': 'success',
                    'result': tool_result.data if tool_result else 'completed'
                })
                
                result_message = f"{tool_result.data if tool_result else 'Tool completed'}. [Modalità Tool disattivata: {session.tool_name} | session chiusa]"
                return AIResponse(
                    text=result_message,
                    success=True,
                    response_type="tool_execution"
                )
            else:
                # Tool execution failed
                error_message = f"Errore nell'esecuzione di {session.tool_name}: {tool_result.data if tool_result else 'Unknown error'}"
                
                # Cleanup session
                self._cleanup_tool_session(session_id, 'finished', 'error', error_message)
                
                # Notify completion
                self._on_complete(session_id, {
                    'outcome': 'error',
                    'error': error_message
                })
                
                return AIResponse(
                    text=error_message,
                    success=False,
                    response_type="error"
                )
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error executing tool: {e}')
            
            # Cleanup session on error
            self._cleanup_tool_session(session_id, 'finished', 'error', f'Tool execution error: {str(e)}')
            
            # Notify completion
            self._on_complete(session_id, {
                'outcome': 'error',
                'error': str(e)
            })
            
            return AIResponse(
                text=f"Errore nell'esecuzione del tool: {str(e)}",
                success=False,
                response_type="error"
            )
    
    def _cleanup_tool_session(self, session_id: str, final_state: str, status: str = "", message: str = "") -> None:
        """
        Clean up a tool session and emit final events.
        """
        try:
            if session_id in self._tool_sessions:
                session = self._tool_sessions[session_id]
                session.active = False
                session.state = final_state
                
                # Emit tool_lifecycle_finished event
                self._event_emitter('tool_lifecycle_finished', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'final_state': final_state,
                    'status': status,
                    'message': message
                })
                
                # Remove session
                del self._tool_sessions[session_id]
                
                logging.info(f'[ToolLifecycleAgent] Cleaned up tool session {session_id} with final state {final_state}')
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error cleaning up tool session: {e}')
    
    #----------------------------------------------------------------
    # PARAMETER EXTRACTION AND VALIDATION
    #----------------------------------------------------------------
    def _generate_clarification_question(self, session_id: str) -> str:
        """
        Generate a clarification question for missing parameters.
        """
        try:
            session = self._tool_sessions[session_id]
            
            if not session.missing:
                return "Tutti i parametri sono stati forniti."
            
            # Use AI processor to generate clarification question
            if self._ai_processor and hasattr(self._ai_processor, 'process_request'):
                try:
                    prompt = get_clarification_prompt(
                        user_input="",  # No specific user input for initial question
                        intent=session.tool_name,
                        missing_params=session.missing
                    )
                    
                    ai_response = self._ai_processor.process_request(prompt)
                    if ai_response and ai_response.success and ai_response.text:
                        return ai_response.text.strip()
                except Exception as e:
                    logging.warning(f'[ToolLifecycleAgent] AI clarification generation failed: {e}')
            
            # Fallback to simple question
            if len(session.missing) == 1:
                param = session.missing[0]
                if param == 'destination':
                    return "Qual è la destinazione del viaggio?"
                elif param == 'location':
                    return "Per quale località vuoi le informazioni?"
                else:
                    return f"Fornisci il parametro {param}:"
            else:
                return f"Fornisci i seguenti parametri: {', '.join(session.missing)}"
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error generating clarification question: {e}')
            return "Fornisci i parametri mancanti."
    
    def _extract_parameters_from_input(self, user_input: str, missing_params: List[str], tool_name: str) -> Dict[str, Any]:
        """
        Extract parameters from user input using simple pattern matching.
        """
        params = {}
        user_lower = user_input.lower().strip()
        
        # Skip extraction for obviously non-parameter inputs
        question_indicators = ['come', 'cosa', 'chi', 'dove', 'quando', 'perché', 'stai', 'vai', 'fai']
        if any(word in user_lower for word in question_indicators):
            return params
        
        # Simple pattern matching for common parameters
        if 'destination' in missing_params:
            # Extract destination from common patterns
            words = user_input.strip().split()
            if words and len(words) <= 3:  # More restrictive
                # If it's a single word or looks like a place name, use it as destination
                if len(words) == 1 or any(word[0].isupper() for word in words):
                    # Additional validation - check if it looks like a place name
                    if not any(word.lower() in question_indicators for word in words):
                        params['destination'] = user_input.strip()
        
        if 'location' in missing_params:
            # Similar to destination
            words = user_input.strip().split()
            if words and len(words) <= 3:  # More restrictive
                if len(words) == 1 or any(word[0].isupper() for word in words):
                    if not any(word.lower() in question_indicators for word in words):
                        params['location'] = user_input.strip()
        
        # Check for toll/highway preferences
        if 'pedaggi' in user_lower or 'toll' in user_lower:
            params['avoid_tolls'] = True
        if 'autostrade' in user_lower or 'highway' in user_lower:
            params['avoid_highways'] = True
        
        return params
    
    def _normalize_parameters(self, params: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """
        Normalize parameters for specific tools (e.g., preferences for navigation).
        """
        if tool_name == 'set_route_sample':
            # Handle navigation preferences normalization
            normalized = params.copy()
            
            # If avoid_tolls or avoid_highways are at top level, move them to preferences
            preferences = normalized.get('preferences', {})
            
            if 'avoid_tolls' in normalized:
                preferences['avoid_tolls'] = normalized.pop('avoid_tolls')
            if 'avoid_highways' in normalized:
                preferences['avoid_highways'] = normalized.pop('avoid_highways')
            
            if preferences:
                normalized['preferences'] = preferences
            
            return normalized
        
        return params
    
    def _is_parameter_present(self, param_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Check if a parameter is present in the parameters dict, handling nested objects.
        """
        if '.' in param_name:
            # Handle nested parameters
            parts = param_name.split('.')
            current = parameters
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return False
                current = current[part]
            return current is not None and current != ""
        else:
            # Simple parameter
            return param_name in parameters and parameters[param_name] is not None and parameters[param_name] != ""
    
    def _is_input_tool_relevant(self, user_input: str, missing_params: List[str]) -> bool:
        """
        Check if user input is relevant to the tool parameters we're collecting.
        """
        user_lower = user_input.lower().strip()
        
        # Check if input could be a parameter value
        for param in missing_params:
            if param in ['destination', 'location']:
                # Could be a place name
                words = user_input.strip().split()
                if words and len(words) <= 3:
                    if len(words) == 1 or any(word[0].isupper() for word in words):
                        return True
        
        # Check for preference keywords
        if any(keyword in user_lower for keyword in ['pedaggi', 'toll', 'autostrade', 'highway']):
            return True
        
        return False
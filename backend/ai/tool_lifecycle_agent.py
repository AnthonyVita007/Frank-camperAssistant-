"""
Tool Lifecycle Agent Module for Frank Camper Assistant.

This module provides a dedicated AI agent for managing the complete lifecycle of tool operations,
handling the rigorous state machine: detected → clarifying → ready_to_start → running → finished/canceled.
The agent manages parameter collection, validation, tool execution, and comprehensive event emission.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable

from .ai_response import AIResponse
from .intent_prompts import get_clarification_prompt


#----------------------------------------------------------------
# TOOL SESSION DATA STRUCTURE
#----------------------------------------------------------------
@dataclass
class ToolLifecycleSession:
    """
    Data structure for tracking tool session lifecycle within the agent.
    States: detected → clarifying → ready_to_start → running → finished/canceled
    """
    # Tool identification
    tool_name: str
    tool_info: Dict[str, Any]
    schema: Dict[str, Any]
    
    # Session state
    state: str  # "detected" | "clarifying" | "ready_to_start" | "running" | "finished" | "canceled"
    active: bool
    
    # Parameters
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
    Dedicated AI agent for managing the complete lifecycle of tool operations.
    
    This agent owns the tool state machine and handles:
    - Parameter collection and validation
    - Clarification dialogues with users
    - Tool execution coordination
    - Comprehensive lifecycle event emission
    - Session cleanup and completion callbacks
    
    The agent operates independently once started and maintains strict gating
    during active sessions, only accepting relevant parameters or cancellation.
    """
    
    def __init__(
        self,
        ai_processor,
        mcp_handler,
        event_emitter: Callable[[str, Dict[str, Any]], None],
        on_complete: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """
        Initialize the ToolLifecycleAgent.
        
        Args:
            ai_processor: AI processor for generating clarification questions
            mcp_handler: MCP handler for tool execution
            event_emitter: Function to emit backend_action events
            on_complete: Callback when lifecycle completes (session_id, outcome)
        """
        self._ai_processor = ai_processor
        self._mcp_handler = mcp_handler
        self._event_emitter = event_emitter
        self._on_complete = on_complete
        
        # Active sessions managed by this agent
        self._active_sessions: Dict[str, ToolLifecycleSession] = {}
        
        logging.info('[ToolLifecycleAgent] Agent initialized and ready')
    
    def start(
        self,
        session_id: str,
        tool_name: str,
        tool_info: Dict[str, Any],
        initial_params: Dict[str, Any]
    ) -> None:
        """
        Start a new tool lifecycle session.
        
        Args:
            session_id: Unique session identifier
            tool_name: Name of the tool to execute
            tool_info: Tool information including schema
            initial_params: Initially extracted parameters
        """
        try:
            # Extract schema and required parameters
            schema = tool_info.get('parameters_schema', {})
            required = schema.get('required', [])
            
            # Calculate missing required parameters
            missing_required = [
                param for param in required 
                if not self._is_parameter_present(param, initial_params)
            ]
            
            # Determine initial state
            initial_state = "clarifying" if missing_required else "ready_to_start"
            
            # Create session
            session = ToolLifecycleSession(
                tool_name=tool_name,
                tool_info=tool_info,
                schema=schema,
                state=initial_state,
                active=True,
                required=required,
                parameters=initial_params.copy(),
                missing=missing_required.copy(),
                last_question=None,
                asked_count=0,
                started_at=time.time(),
                created_at=time.time()
            )
            
            self._active_sessions[session_id] = session
            
            # Emit lifecycle started event
            self._event_emitter('tool_lifecycle_started', {
                'session_id': session_id,
                'tool_name': tool_name,
                'state': initial_state,
                'missing_required': missing_required,
                'params_partial': initial_params,
                'timestamp': session.created_at
            })
            
            # Emit tool selected event
            self._event_emitter('tool_selected', {
                'tool_name': tool_name
            })
            
            logging.info(f'[ToolLifecycleAgent] Started lifecycle for {tool_name} in state {initial_state}')
            
            # If no missing parameters, proceed to execution
            if not missing_required:
                self._proceed_to_execution(session_id)
            
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error starting lifecycle: {e}')
            self._cleanup_session(session_id, 'error', 'error', f'Failed to start: {str(e)}')
    
    def handle_user_message(self, session_id: str, text: str) -> AIResponse:
        """
        Handle user message during active tool lifecycle.
        
        Args:
            session_id: Session identifier
            text: User input text
            
        Returns:
            AIResponse: Response to user
        """
        try:
            if session_id not in self._active_sessions:
                return AIResponse(
                    text="Errore: nessuna sessione tool attiva.",
                    success=False,
                    response_type="error"
                )
            
            session = self._active_sessions[session_id]
            
            # Check for cancellation keywords
            cancel_keywords = ['annulla', 'cancella', 'stop', 'basta', 'esci']
            if any(keyword in text.lower() for keyword in cancel_keywords):
                return self.cancel(session_id, "user_cancel")
            
            # If not in clarifying state, reject input
            if session.state != 'clarifying':
                return AIResponse(
                    text=f"Sessione tool in stato {session.state}. Non posso accettare input in questo momento.",
                    success=True,
                    response_type="tool_gating"
                )
            
            # Extract parameters from user response
            extracted_params = self._extract_parameters_from_response(text, session)
            
            # Check if any required parameters were extracted
            relevant_params = {}
            for param_name, param_value in extracted_params.items():
                if param_name in session.missing and param_value:
                    relevant_params[param_name] = param_value
            
            # If no relevant parameters found, send gating notice
            if not relevant_params:
                gating_message = (
                    f'Sono nel ciclo di vita del Tool "{session.tool_name}" e al momento posso accettare solo:\n'
                    f'- i parametri richiesti: {", ".join(session.missing)}\n'
                    f'- oppure "annulla" per interrompere\n'
                    f'Finché non ricevo {", ".join(session.missing)}, non posso gestire altre richieste. '
                    f'[Modalità Tool attiva: {session.tool_name} | stato: {session.state} | missing: {", ".join(session.missing)}]'
                )
                
                # Emit gating notice event
                self._event_emitter('tool_gating_notice', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'state': session.state,
                    'message': f'Modalità Tool attiva: accetto solo {", ".join(session.missing)} o "annulla"',
                    'missing_required': session.missing
                })
                
                return AIResponse(
                    text=gating_message,
                    success=True,
                    response_type="tool_gating"
                )
            
            # Update session with new parameters
            for param_name, param_value in relevant_params.items():
                session.parameters[param_name] = param_value
                
                # Emit parameter received event
                self._event_emitter('tool_parameter_received', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'param_name': param_name,
                    'param_value': param_value,
                    'params_partial': session.parameters.copy(),
                    'missing_required': [p for p in session.missing if p != param_name]
                })
            
            # Recalculate missing parameters
            session.missing = [
                req for req in session.required 
                if not self._is_parameter_present(req, session.parameters)
            ]
            
            # Check if we still have missing parameters
            if session.missing:
                session.asked_count += 1
                
                # Generate next clarification question
                question = self._generate_clarification_question(session)
                session.last_question = question
                
                # Format response with updated missing list
                pairs = ", ".join([f'{k} = "{v}"' for k, v in relevant_params.items()])
                missing_list = ", ".join(session.missing)

                param_received_msg = (
                    f'Parametro ricevuto: {pairs}. '
                    f'[Parametri richiesti aggiornati: {missing_list}]'
                )
                if session.missing:
                    param_received_msg += f" {question}"
                
                return AIResponse(
                    text=param_received_msg,
                    success=True,
                    response_type="clarification",
                    metadata={"clarifying": True, "missing": session.missing}
                )
            
            # All required parameters collected - proceed to execution
            logging.info(f'[ToolLifecycleAgent] All parameters collected for {session.tool_name}: {session.parameters}')
            
            pairs = ", ".join([f'{k} = "{v}"' for k, v in relevant_params.items()])
            param_complete_msg = f'Parametro ricevuto: {pairs}. [Parametri richiesti completi]'
            
            # Execute tool
            execution_result = self._proceed_to_execution(session_id)
            
            # Combine messages
            full_message = f"{param_complete_msg} {execution_result.text}"
            return AIResponse(
                text=full_message,
                success=execution_result.success,
                response_type=execution_result.response_type
            )
            
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error handling user message: {e}')
            self._cleanup_session(session_id, 'error', 'error', f'Error handling message: {str(e)}')
            return AIResponse(
                text="Si è verificato un errore durante l'elaborazione.",
                success=False,
                response_type="error"
            )
    
    def is_active(self, session_id: str) -> bool:
        """
        Check if a session is active in this agent.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if session is active
        """
        return (session_id in self._active_sessions and 
                self._active_sessions[session_id].active and
                self._active_sessions[session_id].state not in ['finished', 'canceled'])
    
    def cancel(self, session_id: str, reason: str = "user_cancel") -> AIResponse:
        """
        Cancel an active tool session.
        
        Args:
            session_id: Session identifier
            reason: Cancellation reason
            
        Returns:
            AIResponse: Cancellation confirmation
        """
        try:
            if session_id not in self._active_sessions:
                return AIResponse(
                    text="Nessuna operazione da annullare.",
                    success=True,
                    response_type="conversational"
                )
            
            session = self._active_sessions[session_id]
            tool_name = session.tool_name
            current_state = session.state
            
            # Emit session canceled event
            self._event_emitter('tool_session_canceled', {
                'session_id': session_id,
                'tool_name': tool_name,
                'state': current_state,
                'reason': reason,
                'params_partial': session.parameters
            })
            
            # Clean up session
            self._cleanup_session(session_id, 'canceled', reason, f'Tool {tool_name} canceled')
            
            logging.info(f'[ToolLifecycleAgent] Canceled tool session for {tool_name}')
            return AIResponse(
                text=f'Operazione annullata. Ho terminato il ciclo di vita del Tool "{tool_name}". [tool_session canceled → {tool_name}] [Modalità Tool disattivata: {tool_name} | session chiusa]',
                success=True,
                response_type="conversational"
            )
                
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error canceling session: {e}')
            return AIResponse(
                text="Errore durante l'annullamento dell'operazione.",
                success=False,
                response_type="error"
            )
    
    def _proceed_to_execution(self, session_id: str) -> AIResponse:
        """
        Proceed to tool execution when all parameters are ready.
        
        Args:
            session_id: Session identifier
            
        Returns:
            AIResponse: Execution result
        """
        if session_id not in self._active_sessions:
            return AIResponse(
                text="Errore: sessione non trovata.",
                success=False,
                response_type="error"
            )
        
        session = self._active_sessions[session_id]
        
        try:
            # Update session state to ready_to_start
            session.state = 'ready_to_start'
            self._event_emitter('tool_parameters_ready', {
                'session_id': session_id,
                'tool_name': session.tool_name,
                'parameters': session.parameters
            })
            
            # Update session state to running
            session.state = 'running'
            self._event_emitter('tool_started', {
                'session_id': session_id,
                'tool_name': session.tool_name, 
                'parameters': session.parameters
            })
            
            # Execute the tool
            logging.info(f'[ToolLifecycleAgent] Executing tool "{session.tool_name}" with parameters: {session.parameters}')
            tool_result = self._mcp_handler.execute_tool(session.tool_name, session.parameters)
            
            # Emit completion event
            try:
                status_value = getattr(tool_result.status, 'value', str(tool_result.status))
            except Exception:
                status_value = 'unknown'
            
            self._event_emitter('tool_result', {
                'session_id': session_id,
                'tool_name': session.tool_name, 
                'status': status_value,
                'data': tool_result.data if hasattr(tool_result, 'data') else str(tool_result)
            })
            
            # Clean up session
            self._cleanup_session(session_id, 'finished', status_value, f"Tool {session.tool_name} completed")
            
            # Format result message
            from backend.mcp.mcp_tool import ToolResultStatus
            if tool_result.status == ToolResultStatus.SUCCESS:
                result_message = f"[tool_parameters_ready → {session.tool_name}] [tool_started → {session.tool_name} | parameters: {session.parameters}] {tool_result.data} [tool_result → {session.tool_name} | status: {status_value}] [Modalità Tool disattivata: {session.tool_name} | session chiusa]"
                return AIResponse(
                    text=result_message,
                    success=True,
                    response_type="tool_execution"
                )
            else:
                error_message = f"Errore nell'esecuzione di {session.tool_name}: {tool_result.data}"
                return AIResponse(
                    text=error_message,
                    success=False,
                    response_type="error"
                )
        
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error executing tool: {e}')
            self._cleanup_session(session_id, 'error', 'error', f'Tool execution failed: {str(e)}')
            return AIResponse(
                text=f"Errore nell'esecuzione di {session.tool_name}: {str(e)}",
                success=False,
                response_type="error"
            )
    
    def _extract_parameters_from_response(self, text: str, session: ToolLifecycleSession) -> Dict[str, Any]:
        """
        Extract parameters from user response using AI processor or fallback.
        
        Args:
            text: User input text
            session: Current session
            
        Returns:
            Dict[str, Any]: Extracted parameters
        """
        try:
            # Try AI processor if available
            if self._ai_processor and hasattr(self._ai_processor, 'process_request'):
                # Use the AI processor for parameter extraction
                # This is a simplified version - in practice you'd use proper parameter extraction
                pass
            
            # Fallback to pattern matching
            return self._fallback_parameter_extraction(text, session.missing)
        
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error extracting parameters: {e}')
            return {}
    
    def _fallback_parameter_extraction(self, user_input: str, missing_params: List[str]) -> Dict[str, Any]:
        """
        Fallback parameter extraction using simple pattern matching.
        
        Args:
            user_input: User input
            missing_params: List of missing parameters
            
        Returns:
            Dict[str, Any]: Extracted parameters
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
        
        return params
    
    def _generate_clarification_question(self, session: ToolLifecycleSession) -> str:
        """
        Generate a clarification question for missing parameters.
        
        Args:
            session: Current session
            
        Returns:
            str: Clarification question
        """
        try:
            # Try AI processor if available
            if self._ai_processor and hasattr(self._ai_processor, 'process_request'):
                try:
                    prompt = get_clarification_prompt(
                        user_input="",  # We don't have the original input here
                        intent=session.tool_name,
                        missing_params=session.missing
                    )
                    
                    response = self._ai_processor.process_request(prompt)
                    if response and hasattr(response, 'text') and response.text:
                        # Try to parse the response and extract question
                        import json
                        try:
                            data = json.loads(response.text)
                            if isinstance(data, dict) and 'questions' in data:
                                return data['questions'][0] if data['questions'] else self._fallback_question(session.missing[0])
                            elif isinstance(data, list) and data:
                                return data[0]
                        except json.JSONDecodeError:
                            pass
                        
                        # If JSON parsing fails, use the response directly if it looks like a question
                        if response.text.strip().endswith('?'):
                            return response.text.strip()
                            
                except Exception as e:
                    logging.warning(f'[ToolLifecycleAgent] AI question generation failed: {e}')
            
            # Fallback to deterministic question for first missing parameter
            return self._fallback_question(session.missing[0])
            
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error generating clarification question: {e}')
            return f"Puoi fornire il parametro mancante: {session.missing[0]}?"
    
    def _fallback_question(self, missing_param: str) -> str:
        """
        Generate a fallback question for a missing parameter.
        
        Args:
            missing_param: Name of the missing parameter
            
        Returns:
            str: Question to ask the user
        """
        question_map = {
            'destination': "Qual è la destinazione?",
            'location': "Per quale località?",
            'system': "Quale sistema vuoi controllare?",
            'maintenance_type': "Che tipo di manutenzione?",
            'time_filter': "Quale periodo temporale?",
            'urgency': "Qual è il livello di urgenza?",
        }
        
        return question_map.get(missing_param, f"Puoi fornire: {missing_param}?")
    
    def _is_parameter_present(self, param_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Check if a parameter is present in the parameters dict, handling nested objects.
        
        Args:
            param_name: Parameter name (can be nested like 'preferences.avoid_tolls')
            parameters: Parameters dictionary
            
        Returns:
            bool: True if parameter is present and not None/empty
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
    
    def _cleanup_session(self, session_id: str, final_state: str, status: str = "", message: str = "") -> None:
        """
        Clean up and remove a tool session at the end of its lifecycle.
        
        Args:
            session_id: Session identifier
            final_state: Final state (finished/canceled/error)
            status: Final status
            message: Final message
        """
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions[session_id]
        tool_name = session.tool_name
        
        # Emit lifecycle finished event
        self._event_emitter('tool_lifecycle_finished', {
            'session_id': session_id,
            'tool_name': tool_name,
            'final_state': final_state,
            'status': status,
            'message': message
        })
        
        # Prepare outcome for completion callback
        outcome = {
            'tool_name': tool_name,
            'final_state': final_state,
            'status': status,
            'message': message,
            'parameters': session.parameters,
            'session_data': session
        }
        
        # Remove session from memory
        del self._active_sessions[session_id]
        
        # Call completion callback
        try:
            self._on_complete(session_id, outcome)
        except Exception as e:
            logging.error(f'[ToolLifecycleAgent] Error in completion callback: {e}')
        
        logging.info(f'[ToolLifecycleAgent] Cleaned up session {session_id} for {tool_name} with final state {final_state}')
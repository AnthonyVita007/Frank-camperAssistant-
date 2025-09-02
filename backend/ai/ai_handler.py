"""
AI Handler Module for Frank Camper Assistant.

This module provides the integration layer between the AI system and the main controller,
managing AI request validation, processing coordination, and logging.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union, Callable

from .ai_processor import AIProcessor  # Il processor (può essere single-provider o dual-provider)
from .ai_response import AIResponse
from .llm_intent_detector import LLMIntentDetector, IntentDetectionResult
from .intent_prompts import get_clarification_prompt

# Import opzionale dell'Enum AIProvider (presente solo se l'AIProcessor è dual-provider)
try:
    from .ai_processor import AIProvider  # type: ignore
except Exception:
    AIProvider = None  # type: ignore


#----------------------------------------------------------------
# TOOL SESSION DATA STRUCTURE (COMPREHENSIVE LIFECYCLE)
#----------------------------------------------------------------
@dataclass
class ToolSessionState:
    """
    Data structure for tracking comprehensive tool session lifecycle.
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

# Backward compatibility alias
PendingToolSession = ToolSessionState


class AIHandler:
    """
    Handles AI request processing and integration with the main system.
    
    This class serves as the interface between the main controller and the AI processor,
    providing validation, coordination, and logging for AI interactions. Includes
    MCP (Model Context Protocol) integration for tool-based interactions and advanced
    LLM-based intent recognition with pattern matching fallback.
    
    Parameter extraction for tools is handled entirely by the LLM system when available,
    with a minimal non-intrusive fallback for when LLM is disabled.
    
    Attributes:
        _ai_processor (AIProcessor): The AI processor instance
        _is_enabled (bool): Whether AI processing is enabled
        _mcp_handler (Optional): The MCP handler for tool interactions
        _tool_detection_enabled (bool): Whether to detect tool usage intents
        _llm_intent_detector (Optional[LLMIntentDetector]): LLM-based intent detector
        _llm_intent_enabled (bool): Whether LLM intent detection is enabled
    """
    
#----------------------------------------------------------------
# COSTRUTTORE AIHandler CON EVENT EMITTER OPZIONALE
#----------------------------------------------------------------
    def __init__(
    self, 
    ai_processor: Optional[AIProcessor] = None, 
    mcp_handler: Optional = None,  # type: ignore
    llm_intent_enabled: bool = True, 
    llm_intent_detector: Optional[LLMIntentDetector] = None,  # type: ignore
    event_emitter: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> None:
        """
        Initialize the AIHandler with optional MCP support and LLM intent detection.
        event_emitter: callable opzionale con firma (action: str, data: Dict[str, Any]) -> None
                    usato per emettere 'backend_action' verso il frontend Debug.
        """
        try:
            #----------------------------------------------------------------
            # PROCESSOR E STATO BASE
            #----------------------------------------------------------------
            self._ai_processor = ai_processor or AIProcessor()
            self._is_enabled = self._ai_processor.is_available()
            
            #----------------------------------------------------------------
            # EMITTER EVENTI BACKEND_ACTION (opzionale)
            #----------------------------------------------------------------
            self._event_emitter: Optional[Callable[[str, Dict[str, Any]], None]] = event_emitter
            
            #----------------------------------------------------------------
            # INTEGRAZIONE MCP (TOOLS)
            #----------------------------------------------------------------
            self._mcp_handler = mcp_handler
            self._tool_detection_enabled = mcp_handler is not None
            
            #----------------------------------------------------------------
            # INTEGRAZIONE LLM INTENT DETECTION
            #----------------------------------------------------------------
            if llm_intent_detector is not None:
                self._llm_intent_detector = llm_intent_detector
                self._llm_intent_enabled = llm_intent_detector.is_enabled()
                logging.info('[AIHandler] Using pre-configured LLM intent detector')
            else:
                self._llm_intent_enabled = llm_intent_enabled and self._is_enabled
                self._llm_intent_detector = None
                if self._llm_intent_enabled:
                    try:
                        self._llm_intent_detector = LLMIntentDetector(
                            ai_processor=self._ai_processor,
                            enabled=True
                        )
                        if self._llm_intent_detector.is_enabled():
                            logging.info('[AIHandler] LLM intent detection initialized successfully')
                        else:
                            logging.warning('[AIHandler] LLM intent detection initialized but not available')
                            self._llm_intent_enabled = False
                    except Exception as e:
                        logging.error(f'[AIHandler] Failed to initialize LLM intent detection: {e}')
                        self._llm_intent_enabled = False
                        self._llm_intent_detector = None
            
            #----------------------------------------------------------------
            # TOOL SESSION LIFECYCLE MANAGEMENT
            #----------------------------------------------------------------
            self._tool_sessions: Dict[str, ToolSessionState] = {}
            
            # Backward compatibility
            self._pending_sessions: Dict[str, ToolSessionState] = self._tool_sessions
            
            #----------------------------------------------------------------
            # LOG DI STATO
            #----------------------------------------------------------------
            if self._is_enabled:
                logging.info('[AIHandler] AI handler initialized successfully')
                if self._tool_detection_enabled:
                    logging.info('[AIHandler] MCP tool integration enabled')
                    if self._llm_intent_enabled:
                        logging.info('[AIHandler] Hybrid intent detection enabled (LLM + pattern matching)')
                    else:
                        logging.info('[AIHandler] Pattern matching intent detection enabled')
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
            self._llm_intent_enabled = False
            self._llm_intent_detector = None
            self._event_emitter = None
            self._pending_sessions = {}

    @classmethod
    def from_config(
        cls, 
        config_path: Optional[str] = None, 
        ai_processor: Optional[AIProcessor] = None, 
        mcp_handler: Optional = None # type: ignore
    ):
        """
        Create an AIHandler instance using configuration from config file.
        """
        try:
            from .llm_intent_config import create_llm_intent_detector_from_config
            llm_intent_detector = create_llm_intent_detector_from_config(
                ai_processor=ai_processor,
                config_path=config_path
            )
            return cls(
                ai_processor=ai_processor,
                mcp_handler=mcp_handler,
                llm_intent_detector=llm_intent_detector
            )
        except Exception as e:
            logging.error(f'[AIHandler] Error creating AI handler from config: {e}')
            return cls(
                ai_processor=ai_processor,
                mcp_handler=mcp_handler,
                llm_intent_enabled=False
            )
    
    #----------------------------------------------------------------
    # API: CAMBIO PROVIDER AI (SUPPORTO SWITCH LOCALE ↔ GEMINI)
    #----------------------------------------------------------------
    def set_ai_provider(self, provider: Union[str, Any]) -> bool:
        """
        Switch to a different AI provider (if supported by AIProcessor) with automatic fallback.
        
        Args:
            provider (Union[str, Any]): 'local' | 'gemini' | AIProvider enum (se disponibile)
        
        Returns:
            bool: True se lo switch è avvenuto con successo, altrimenti False.
        """
        try:
            if not self._ai_processor:
                logging.warning('[AIHandler] Cannot switch provider: AI processor not available')
                return False
            
            # Se l'AIProcessor non espone set_provider, non è dual-provider
            if not hasattr(self._ai_processor, 'set_provider'):
                logging.warning('[AIHandler] set_provider not supported by current AIProcessor')
                return False
            
            # Normalizzazione provider
            target = provider
            target_name = ""
            if isinstance(provider, str):
                prov_str = provider.strip().lower()
                target_name = prov_str
                if AIProvider:
                    if prov_str == 'local':
                        target = AIProvider.LOCAL  # type: ignore
                    elif prov_str == 'gemini':
                        target = AIProvider.GEMINI  # type: ignore
                    else:
                        logging.warning(f'[AIHandler] Unknown provider string: {provider}')
                        return False
                else:
                    # Se AIProvider non è disponibile, non possiamo convertire
                    logging.warning('[AIHandler] AIProvider enum not available in AIProcessor module')
                    return False
            else:
                target_name = getattr(target, "value", str(target))
            
            # Esegui lo switch
            success = self._ai_processor.set_provider(target)  # type: ignore
            if success:
                logging.info(f'[AIHandler] Switched AI provider to: {target_name}')
                # Re-inizializza (opzionale) il detector degli intenti con il processor attuale
                if self._llm_intent_enabled:
                    try:
                        self._llm_intent_detector = LLMIntentDetector(
                            ai_processor=self._ai_processor,
                            enabled=True
                        )
                    except Exception as e:
                        logging.warning(f'[AIHandler] Could not reinitialize LLM intent detector after provider switch: {e}')
                return True
            
            # Se lo switch ha fallito e stavamo tentando di passare a GEMINI, prova fallback a LOCAL
            if target_name == 'gemini':
                logging.warning('[AIHandler] Gemini switch failed, attempting automatic fallback to LOCAL')
                try:
                    local_target = AIProvider.LOCAL if AIProvider else 'local'  # type: ignore
                    fallback_success = self._ai_processor.set_provider(local_target)  # type: ignore
                    if fallback_success:
                        logging.info('[AIHandler] Automatic fallback to LOCAL successful')
                        # Re-inizializza detector per LOCAL
                        if self._llm_intent_enabled:
                            try:
                                self._llm_intent_detector = LLMIntentDetector(
                                    ai_processor=self._ai_processor,
                                    enabled=True
                                )
                            except Exception as e:
                                logging.warning(f'[AIHandler] Could not reinitialize LLM intent detector after fallback: {e}')
                        return True
                    else:
                        logging.error('[AIHandler] Automatic fallback to LOCAL also failed')
                except Exception as fallback_error:
                    logging.error(f'[AIHandler] Error during automatic fallback: {fallback_error}')
            
            logging.warning('[AIHandler] AI provider switch failed in AIProcessor')
            return False
        
        except Exception as e:
            logging.error(f'[AIHandler] Error switching AI provider: {e}')
            return False
    
    def get_current_ai_provider(self) -> Optional[Any]:
        """
        Get the currently active AI provider (if supported).
        
        Returns:
            Optional[Any]: AIProvider enum o stringa identificativa; None se non disponibile.
        """
        try:
            if not self._ai_processor or not hasattr(self._ai_processor, 'get_current_provider'):
                return None
            return self._ai_processor.get_current_provider()  # type: ignore
        except Exception as e:
            logging.error(f'[AIHandler] Error getting current AI provider: {e}')
            return None
    
    #----------------------------------------------------------------
    # GESTIONE RICHIESTE AI CON SUPPORTO MCP
    #----------------------------------------------------------------
    def handle_ai_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        Handle an AI request from the user with MCP tool detection.
        """
        # Validazione
        if not self._validate_input(user_input):
            logging.warning(f'[AIHandler] Invalid input received: "{user_input}"')
            return AIResponse(
                text="Mi dispiace, non ho ricevuto una richiesta valida.",
                response_type='error',
                success=False,
                message="Invalid input"
            )
        
        # Disponibilità AI
        if not self._is_enabled or not self._ai_processor:
            logging.warning('[AIHandler] AI processing requested but not available')
            return AIResponse(
                text="Mi dispiace, il sistema AI non è disponibile al momento. Riprova più tardi.",
                response_type='error',
                success=False,
                message="AI system not available"
            )
        
        logging.info(f'[AIHandler] Processing AI request: "{user_input[:100]}..."')
        
        try:
            # Step 1: Intenti tool (se MCP abilitato)
            if self._tool_detection_enabled:
                tool_intent = self._detect_tool_intent(user_input, context)
                if tool_intent:
                    return self._handle_tool_request(user_input, tool_intent, context)
            
            # Step 2: Conversazione standard
            response = self._ai_processor.process_request(user_input, context)
            if response.success:
                logging.info('[AIHandler] AI request processed successfully')
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
    # RILEVAMENTO INTENTI PER STRUMENTI MCP (IBRIDO)
    #----------------------------------------------------------------
    def _detect_tool_intent_pattern_matching(
        self, 
        user_input: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if the user input requires tool usage using pattern matching.
        """
        try:
            input_lower = user_input.lower().strip()
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
            
            detected_intents: Dict[str, List[str]] = {}
            for category, patterns in intent_patterns.items():
                for pattern in patterns:
                    if pattern in input_lower:
                        detected_intents.setdefault(category, []).append(pattern)
            
            if detected_intents:
                primary_intent = max(detected_intents.keys(), key=lambda k: len(detected_intents[k]))
                return {
                    'primary_category': primary_intent,
                    'detected_patterns': detected_intents,
                    'confidence': len(detected_intents[primary_intent]) / len(intent_patterns[primary_intent]),
                    'raw_input': user_input
                }
            return None
        
        except Exception as e:
            logging.error(f'[AIHandler] Error detecting tool intent: {e}')
            return None
    
    def _detect_tool_intent(
        self, 
        user_input: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if the user input requires tool usage using hybrid approach:
        1) LLM-based detection (se abilitato)
        2) Pattern matching come fallback/integrazione
        """
        try:
            if not self._mcp_handler:
                return None
            
            # LLM-based detection
            if self._llm_intent_enabled and self._llm_intent_detector:
                try:
                    available_tools = None
                    if self._mcp_handler:
                        available_tool_info = self._mcp_handler.get_available_tools()
                        available_tools = [t.get('name') for t in available_tool_info if t.get('name')]
                    
                    llm_result = self._llm_intent_detector.detect_intent(
                        user_input=user_input,
                        available_tools=available_tools,
                        context=context
                    )
                    
                    logging.debug(f'[AIHandler] LLM intent detection: conf={llm_result.confidence:.2f}, requires_tool={llm_result.requires_tool}')
                    
                    # Alta confidenza
                    if llm_result.confidence >= getattr(self._llm_intent_detector, '_confidence_threshold_high', 0.8):
                        if llm_result.requires_tool and llm_result.primary_intent:
                            result = self._convert_llm_result_to_legacy_format(llm_result)
                            logging.info(f'[AIHandler] High confidence LLM detection: {llm_result.primary_intent}')
                            return result
                        return None
                    
                    # Media confidenza → combina con pattern
                    if llm_result.confidence >= getattr(self._llm_intent_detector, '_confidence_threshold_low', 0.5):
                        pattern_result = self._detect_tool_intent_pattern_matching(user_input, context)
                        if (llm_result.requires_tool and pattern_result and 
                            llm_result.primary_intent == pattern_result.get('primary_category')):
                            combined = self._convert_llm_result_to_legacy_format(llm_result)
                            combined['confidence'] = min(1.0, llm_result.confidence * 1.2)
                            combined['detection_method'] = 'llm_pattern_combined'
                            logging.info(f'[AIHandler] Combined agreement: {llm_result.primary_intent}')
                            return combined
                        elif llm_result.requires_tool and llm_result.primary_intent:
                            res = self._convert_llm_result_to_legacy_format(llm_result)
                            res['detection_method'] = 'llm_medium_confidence'
                            logging.info(f'[AIHandler] Medium confidence LLM detection (override)')
                            return res
                        elif pattern_result:
                            pattern_result['detection_method'] = 'pattern_override'
                            logging.info('[AIHandler] Pattern matching override')
                            return pattern_result
                    
                    # Bassa confidenza → pattern fallback
                except Exception as e:
                    logging.error(f'[AIHandler] Error in LLM intent detection: {e}')
                    # Continua su pattern fallback
            
            pattern_result = self._detect_tool_intent_pattern_matching(user_input, context)
            if pattern_result:
                pattern_result['detection_method'] = 'pattern_matching_fallback'
                logging.debug(f'[AIHandler] Pattern fallback: {pattern_result.get("primary_category")}')
            return pattern_result
        
        except Exception as e:
            logging.error(f'[AIHandler] Error in hybrid intent detection: {e}')
            return None
    
    def _convert_llm_result_to_legacy_format(self, llm_result: IntentDetectionResult) -> Dict[str, Any]:
        """
        Convert LLM detection result to legacy format for compatibility.
        """
        try:
            return {
                'primary_category': llm_result.primary_intent,
                'detected_patterns': llm_result.extracted_parameters,
                'confidence': llm_result.confidence,
                'raw_input': llm_result.extracted_parameters.get('raw_input', ''),
                'llm_reasoning': llm_result.reasoning,
                'llm_parameters': llm_result.extracted_parameters,
                'multi_intent': llm_result.multi_intent,
                'clarification_needed': llm_result.clarification_needed,
                'clarification_questions': llm_result.clarification_questions,
                'detection_method': 'llm'
            }
        except Exception as e:
            logging.error(f'[AIHandler] Error converting LLM result: {e}')
            return {
                'primary_category': llm_result.primary_intent,
                'confidence': llm_result.confidence,
                'detection_method': 'llm_error'
            }
    
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
        Handle a request that requires tool execution with rigorous lifecycle management.
        Creates tool session at detection time and emits comprehensive lifecycle events.
        """
        try:
            # Extract session_id from context
            session_id = context.get('session_id') if context else None
            if not session_id:
                logging.warning('[AIHandler] No session_id in context for tool request')
                return self._fallback_to_conversation(user_input, "Errore: ID sessione mancante")
            
            #----------------------------------------------------------------
            # IDENTIFICAZIONE CATEGORIA E SELEZIONE TOOL
            #----------------------------------------------------------------
            primary_category = tool_intent.get('primary_category')
            logging.info(f'[AIHandler] Processing tool request for category: {primary_category}')
            
            available_tools = self._mcp_handler.get_tools_by_category(primary_category)
            if not available_tools:
                logging.warning(f'[AIHandler] No tools available for category: {primary_category}')
                return self._fallback_to_conversation(user_input, f"Categoria strumenti '{primary_category}' non disponibile")
            
            # Select the first available tool (in a real implementation, you might want more sophisticated selection)
            selected_tool = available_tools[0]
            tool_name = selected_tool.get('name')
            if not tool_name:
                logging.error(f'[AIHandler] Invalid tool info: {selected_tool}')
                return self._fallback_to_conversation(user_input, "Informazioni strumento non valide")
            
            # Emit tool selected event
            self._emit_backend_action('tool_selected', {'tool_name': tool_name})
            
            #----------------------------------------------------------------
            # ESTRAZIONE PARAMETRI (LLM + fallback) E VALUTAZIONE READY
            #----------------------------------------------------------------
            parameters = self._extract_tool_parameters(user_input, tool_name, selected_tool, context)
            
            # Normalize parameters (e.g., preferences for navigation)
            parameters = self._normalize_parameters(parameters, tool_name)
            
            # Check required parameters
            required_params = selected_tool.get('parameters_schema', {}).get('required', [])
            missing_required = [param for param in required_params if param not in parameters or not parameters[param]]
            
            logging.info(f'[AIHandler] Tool {tool_name} parameters: {parameters}, missing: {missing_required}')
            
            #----------------------------------------------------------------
            # CREATE TOOL SESSION (ALWAYS, REGARDLESS OF MISSING PARAMS)
            #----------------------------------------------------------------
            self._create_tool_session(session_id, tool_name, selected_tool, parameters, missing_required)
            
            #----------------------------------------------------------------
            # BRANCH: CLARIFICATION vs EXECUTION
            #----------------------------------------------------------------
            if missing_required:
                # Start clarification process
                return self._start_tool_clarification(session_id, user_input)
            else:
                # Ready to execute immediately
                return self._execute_tool_directly(session_id)
                
        except Exception as e:
            logging.error(f'[AIHandler] Error handling tool request: {e}')
            return self._fallback_to_conversation(user_input, f"Errore nell'elaborazione della richiesta strumento: {str(e)}")
    
    def _start_tool_clarification(self, session_id: str, user_input: str) -> AIResponse:
        """
        Start the clarification process for missing parameters.
        """
        if session_id not in self._tool_sessions:
            return AIResponse(
                text="Errore: sessione tool non trovata.",
                success=False,
                response_type="error"
            )
        
        session = self._tool_sessions[session_id]
        
        # Generate clarification question
        question = self._generate_clarification_question(session)
        session.last_question = question
        session.asked_count += 1
        
        # Emit clarification event
        self._emit_backend_action('tool_clarification', {
            'session_id': session_id,
            'tool_name': session.tool_name,
            'missing_required': session.missing,
            'question': question
        })
        
        # Format the response with gating information
        formatted_message = (
            f"Ho rilevato che la tua richiesta richiede l'uso dello strumento: {session.tool_name}. "
            f"[Modalità Tool attiva: {session.tool_name} | stato: {session.state} | session_id={session_id}] "
            f"Per avviare {session.tool_name.lower()} ho bisogno di questi parametri obbligatori: {', '.join(session.missing)}. "
            f"{question}"
        )
        
        return AIResponse(
            text=formatted_message,
            success=True,
            response_type="tool_clarification"
        )
    
    def _execute_tool_directly(self, session_id: str) -> AIResponse:
        """
        Execute tool directly when all parameters are available.
        """
        if session_id not in self._tool_sessions:
            return AIResponse(
                text="Errore: sessione tool non trovata.",
                success=False,
                response_type="error"
            )
        
        session = self._tool_sessions[session_id]
        
        # Update session state to ready_to_start
        self._update_tool_session_state(session_id, 'ready_to_start')
        self._emit_backend_action('tool_ready_to_start', {
            'session_id': session_id,
            'tool_name': session.tool_name
        })
        
        # Update session state to running
        self._update_tool_session_state(session_id, 'running')
        self._emit_backend_action('tool_started', {
            'session_id': session_id,
            'tool_name': session.tool_name, 
            'parameters': session.parameters
        })
        
        # Execute the tool
        logging.info(f'[AIHandler] Executing tool "{session.tool_name}" with parameters: {session.parameters}')
        tool_result = self._mcp_handler.execute_tool(session.tool_name, session.parameters)
        
        # Emit completion event
        try:
            status_value = getattr(tool_result.status, 'value', str(tool_result.status))
        except Exception:
            status_value = 'unknown'
        
        self._emit_backend_action('tool_finished', {
            'session_id': session_id,
            'tool_name': session.tool_name, 
            'status': status_value
        })
        
        # Clean up session
        self._cleanup_tool_session(session_id, 'finished', status_value, f"Tool {session.tool_name} completed")
        
        # Format result message
        from backend.mcp.mcp_tool import ToolResultStatus
        if tool_result.status == ToolResultStatus.SUCCESS:
            result_message = f"{tool_result.data}. [Modalità Tool disattivata: {session.tool_name} | session chiusa]"
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
        
    def _extract_tool_parameters(
        self, 
        user_input: str, 
        tool_name: str, 
        tool_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract parameters for tool execution from natural language input using LLM.
        """
        try:
            schema = tool_info.get('parameters_schema', {}) or {}
            
            # Usa LLMIntentDetector se abilitato
            if self._llm_intent_enabled and self._llm_intent_detector:
                logging.debug(f'[AIHandler] Using LLM parameter extraction for tool: {tool_name}')
                llm_params = self._llm_intent_detector.extract_parameters(
                    user_input=user_input,
                    tool_name=tool_name,
                    tool_schema=schema,
                    context=context
                )
                if llm_params:
                    validated = self._validate_extracted_parameters(llm_params, schema)
                    logging.debug(f'[AIHandler] LLM validated parameters for {tool_name}: {validated}')
                    return validated
                else:
                    logging.warning(f'[AIHandler] LLM parameter extraction returned empty for {tool_name}')
            
            # Fallback minimale (non intrusivo)
            logging.info(f'[AIHandler] Using fallback parameter extraction for {tool_name}')
            return self._extract_parameters_fallback(user_input, tool_info, context)
        
        except Exception as e:
            logging.error(f'[AIHandler] Error extracting tool parameters: {e}')
            return self._extract_parameters_fallback(user_input, tool_info, context)
    
    def _validate_extracted_parameters(
        self, 
        parameters: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and normalize parameters extracted from LLM against tool schema.
        """
        try:
            if not schema:
                return parameters or {}
            
            validated: Dict[str, Any] = {}
            props = schema.get('properties', {}) or {}
            
            for name, value in (parameters or {}).items():
                if name in props:
                    validated[name] = self._normalize_parameter_value(value, props.get(name, {}))
                else:
                    logging.debug(f'[AIHandler] Ignoring param not in schema: {name}')
            
            # Log eventuali required mancanti (non blocca)
            required = schema.get('required', []) or []
            missing = [r for r in required if r not in validated]
            if missing:
                logging.warning(f'[AIHandler] Missing required parameters after LLM extraction: {missing}')
            
            return validated
        except Exception as e:
            logging.error(f'[AIHandler] Error validating parameters: {e}')
            return parameters or {}
    
    def _normalize_parameter_value(self, value: Any, property_schema: Dict[str, Any]) -> Any:
        """
        Normalize parameter value based on schema type definition.
        """
        try:
            expected = (property_schema or {}).get('type', 'string')
            
            if expected == 'boolean':
                if isinstance(value, str):
                    return value.strip().lower() in ('true', '1', 'yes', 'si', 'sì', 'on')
                return bool(value)
            if expected == 'integer':
                return int(value) if value is not None else None
            if expected == 'number':
                return float(value) if value is not None else None
            if expected == 'string':
                # Normalizzazione minima stringhe
                return str(value).strip() if value is not None else ''
            
            return value
        except Exception as e:
            logging.warning(f'[AIHandler] Error normalizing parameter value: {e}')
            return value
    
    def _extract_parameters_fallback(
        self, 
        user_input: str, 
        tool_info: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced fallback for parameter extraction when LLM fails.
        Uses pattern matching for common parameters.
        """
        try:
            params: Dict[str, Any] = {}
            schema = tool_info.get('parameters_schema', {}) or {}
            tool_name = tool_info.get('name', '').lower()
            
            # Include context if present
            if context:
                params['context'] = context
            
            # Enhanced pattern matching based on tool category
            if 'navigation' in tool_name:
                params.update(self._extract_navigation_params_fallback(user_input))
            elif 'weather' in tool_name:
                params.update(self._extract_weather_params_fallback(user_input))
            elif 'vehicle' in tool_name:
                params.update(self._extract_vehicle_params_fallback(user_input))
            elif 'maintenance' in tool_name:
                params.update(self._extract_maintenance_params_fallback(user_input))
            
            # Include raw user input if schema expects it
            if 'user_input' in (schema.get('properties', {}) or {}):
                params['user_input'] = user_input
            
            logging.debug(f'[AIHandler] Enhanced fallback params for {tool_info.get("name", "unknown")}: {params}')
            return params
        except Exception as e:
            logging.error(f'[AIHandler] Error in enhanced fallback parameter extraction: {e}')
            return {}
    
    def _extract_navigation_params_fallback(self, user_input: str) -> Dict[str, Any]:
        """Extract navigation parameters using pattern matching."""
        params = {}
        text = user_input.lower()
        
        # Destination extraction patterns
        import re
        
        # Common destination patterns
        destination_patterns = [
            r'(?:portami|vai|naviga|rotta|strada).*?(?:a|per|verso)\s+([a-zA-ZÀ-ÿ\s]+?)(?:\s|$|,|\.|\?|!)',
            r'(?:destinazione|meta).*?[:]\s*([a-zA-ZÀ-ÿ\s]+?)(?:\s|$|,|\.|\?|!)',
            r'(?:puoi\s+)?portarmi\s+a\s+([a-zA-ZÀ-ÿ\s]+?)(?:\s|$|,|\.|\?|!)',  # Handle "puoi portarmi a..."
            r'^([a-zA-ZÀ-ÿ\s]+?)(?:\s|$)$',  # Single word/location only
        ]
        
        for pattern in destination_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                destination = match.group(1).strip().title()
                if len(destination) > 1:  # Avoid single characters
                    params['destination'] = destination
                    break
        
        # Preferences extraction
        if any(word in text for word in ['pedaggi', 'pedaggio', 'toll']):
            params['avoid_tolls'] = 'evita' in text or 'senza' in text or 'no' in text
        
        if any(word in text for word in ['autostrade', 'autostrada', 'highway']):
            params['avoid_highways'] = 'evita' in text or 'senza' in text or 'no' in text
        
        # Route type
        if any(word in text for word in ['veloce', 'rapido', 'fastest']):
            params['route_type'] = 'fastest'
        elif any(word in text for word in ['breve', 'corto', 'shortest']):
            params['route_type'] = 'shortest'
        elif any(word in text for word in ['panoramic', 'scenic', 'bello']):
            params['route_type'] = 'scenic'
        
        return params
    
    def _extract_weather_params_fallback(self, user_input: str) -> Dict[str, Any]:
        """Extract weather parameters using pattern matching."""
        params = {}
        text = user_input.lower()
        
        import re
        
        # Location extraction
        location_patterns = [
            r'(?:a|per|di|in)\s+([a-zA-ZÀ-ÿ\s]+?)(?:\s|$|,|\.|\?|!)',
            r'meteo\s+([a-zA-ZÀ-ÿ\s]+?)(?:\s|$|,|\.|\?|!)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip().title()
                if len(location) > 1:
                    params['location'] = location
                    break
        
        # Time range
        if any(word in text for word in ['domani', 'tomorrow']):
            params['time_range'] = 'tomorrow'
        elif any(word in text for word in ['oggi', 'today']):
            params['time_range'] = 'today'
        elif any(word in text for word in ['weekend', 'fine settimana']):
            params['time_range'] = 'weekend'
        elif any(word in text for word in ['settimana', 'week']):
            params['time_range'] = 'week'
        elif any(word in text for word in ['ora', 'adesso', 'now']):
            params['time_range'] = 'now'
        
        # Specific weather data
        if any(word in text for word in ['pioggia', 'piove', 'rain']):
            params['specific_data'] = 'rain'
        elif any(word in text for word in ['temperatura', 'temp', 'caldo', 'freddo']):
            params['specific_data'] = 'temperature'
        elif any(word in text for word in ['vento', 'wind']):
            params['specific_data'] = 'wind'
        
        return params
    
    def _extract_vehicle_params_fallback(self, user_input: str) -> Dict[str, Any]:
        """Extract vehicle parameters using pattern matching."""
        params = {}
        text = user_input.lower()
        
        # System identification
        if any(word in text for word in ['motore', 'engine']):
            params['system'] = 'engine'
        elif any(word in text for word in ['carburante', 'benzina', 'fuel', 'gas']):
            params['system'] = 'fuel'
        elif any(word in text for word in ['pneumatic', 'gomme', 'tires']):
            params['system'] = 'tires'
        elif any(word in text for word in ['batteria', 'battery']):
            params['system'] = 'battery'
        else:
            params['system'] = 'general'
        
        # Check type
        if any(word in text for word in ['stato', 'status', 'come va']):
            params['check_type'] = 'status'
        elif any(word in text for word in ['diagnostic', 'controllo', 'verifica']):
            params['check_type'] = 'diagnostic'
        elif any(word in text for word in ['livell', 'level']):
            params['check_type'] = 'levels'
        
        # Urgency
        if any(word in text for word in ['urgente', 'urgent', 'subito']):
            params['urgency'] = 'high'
        elif any(word in text for word in ['importante', 'medium']):
            params['urgency'] = 'medium'
        else:
            params['urgency'] = 'low'
        
        return params
    
    def _extract_maintenance_params_fallback(self, user_input: str) -> Dict[str, Any]:
        """Extract maintenance parameters using pattern matching."""
        params = {}
        text = user_input.lower()
        
        # Maintenance type
        if any(word in text for word in ['olio', 'oil']):
            params['maintenance_type'] = 'oil_change'
        elif any(word in text for word in ['filtro', 'filter']):
            params['maintenance_type'] = 'filter'
        elif any(word in text for word in ['revisione', 'inspection', 'controllo']):
            params['maintenance_type'] = 'inspection'
        else:
            params['maintenance_type'] = 'general'
        
        # Time filter
        if any(word in text for word in ['scadut', 'overdue', 'ritardo']):
            params['time_filter'] = 'overdue'
        elif any(word in text for word in ['prossim', 'upcoming', 'scadenza']):
            params['time_filter'] = 'upcoming'
        else:
            params['time_filter'] = 'all'
        
        # Urgency
        if any(word in text for word in ['urgente', 'urgent', 'subito']):
            params['urgency'] = 'high'
        elif any(word in text for word in ['importante', 'medium']):
            params['urgency'] = 'medium'
        else:
            params['urgency'] = 'low'
        
        return params
    
    def _convert_tool_result_to_ai_response(
        self, 
        tool_result, 
        tool_name: str, 
        original_input: str
    ) -> AIResponse:
        """
        Convert a tool execution result to an AIResponse.
        """
        try:
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
        """
        try:
            logging.info(f'[AIHandler] Falling back to conversational AI: {reason}')
            response = self._ai_processor.process_request(user_input)
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
    # STREAMING CON SUPPORTO MCP (SOLO CONVERSAZIONI)
    #----------------------------------------------------------------
    def handle_ai_stream(self, user_input: str, context: Optional[Dict[str, Any]] = None):
        """
        Handle a streaming AI request from the user with MCP tool detection.
        Tool execution is not streamed; only conversational responses are streamed.
        """
        if not self._validate_input(user_input):
            logging.warning(f'[AIHandler] Invalid input for streaming request: "{user_input}"')
            yield "Mi dispiace, non ho ricevuto una richiesta valida."
            return
        
        if not self._is_enabled or not self._ai_processor:
            logging.warning('[AIHandler] AI streaming requested but not available')
            yield "Mi dispiace, il sistema AI non è disponibile al momento. Riprova più tardi."
            return
        
        logging.info(f'[AIHandler] Processing streaming AI request: "{user_input[:100]}..."')
        
        try:
            if self._tool_detection_enabled:
                tool_intent = self._detect_tool_intent(user_input, context)
                if tool_intent:
                    tool_response = self._handle_tool_request(user_input, tool_intent, context)
                    yield tool_response.text
                    return
            
            for chunk in self._ai_processor.stream_request(user_input, context):
                if chunk:
                    yield chunk
            
            logging.info('[AIHandler] Streaming AI request completed successfully')
        except Exception as e:
            logging.error(f'[AIHandler] Unexpected error in streaming AI request: {e}')
            yield "Mi dispiace, si è verificato un errore imprevisto durante la generazione della risposta."
    
    #----------------------------------------------------------------
    # METODI DI SUPPORTO E STATO
    #----------------------------------------------------------------
    def _validate_input(self, user_input: str) -> bool:
        """
        Validate user input for AI processing.
        """
        if not user_input or not isinstance(user_input, str):
            return False
        if not user_input.strip():
            return False
        if len(user_input.strip()) > 5000:
            logging.warning(f'[AIHandler] Input too long: {len(user_input)} characters')
            return False
        return True
    
    def is_ai_enabled(self) -> bool:
        """
        Check if AI processing is enabled and available.
        """
        return self._is_enabled and self._ai_processor is not None
    
    def is_mcp_enabled(self) -> bool:
        """
        Check if MCP tool integration is enabled and available.
        """
        return self._tool_detection_enabled and self._mcp_handler is not None
    
    def is_llm_intent_enabled(self) -> bool:
        """
        Check if LLM-based intent detection is enabled and available.
        """
        return self._llm_intent_enabled and self._llm_intent_detector is not None
    
    def get_ai_status(self) -> Dict[str, Any]:
        """
        Get the current status of the AI system including MCP and LLM intent detection.
        """
        status: Dict[str, Any] = {
            'enabled': self._is_enabled,
            'processor_available': self._ai_processor is not None,
            'processor_status': 'unknown',
            'mcp_enabled': self._tool_detection_enabled,
            'mcp_handler_available': self._mcp_handler is not None,
            'llm_intent_enabled': self._llm_intent_enabled,
            'llm_intent_detector_available': self._llm_intent_detector is not None
        }
        
        # Stato del processor e provider (se supportato)
        if self._ai_processor:
            try:
                if hasattr(self._ai_processor, 'is_available'):
                    status['processor_status'] = 'available' if self._ai_processor.is_available() else 'unavailable'
                # Provider details (dual-provider)
                if hasattr(self._ai_processor, 'get_provider_status'):
                    status['provider_status'] = self._ai_processor.get_provider_status()  # type: ignore
                elif hasattr(self._ai_processor, 'get_model_info'):
                    status['model_info'] = self._ai_processor.get_model_info()  # compatibilità single-provider
            except Exception as e:
                status['processor_status'] = f'error: {str(e)}'
        
        # Stato MCP
        if self._mcp_handler:
            try:
                status['mcp_status'] = self._mcp_handler.get_system_status()
            except Exception as e:
                status['mcp_status'] = f'error: {str(e)}'
        
        # Stato LLM intent
        if self._llm_intent_detector:
            try:
                status['llm_intent_status'] = self._llm_intent_detector.get_status()
            except Exception as e:
                status['llm_intent_status'] = f'error: {str(e)}'
        
        return status

    def _emit_backend_action(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emette un evento 'backend_action' usando l'emitter passato al costruttore.
        Se l'emitter non è configurato, effettua solo un log di debug.
        """
        try:
            if callable(self._event_emitter):
                self._event_emitter(action, data or {})
            else:
                logging.debug(f"[AIHandler] (no-emitter) backend_action: {action} {data or {}}")
        except Exception as e:
            logging.warning(f"[AIHandler] Failed to emit backend_action '{action}': {e}")

    #----------------------------------------------------------------
    # TOOL CLARIFICATION CYCLE METHODS
    #----------------------------------------------------------------
    
    def has_pending_tool_session(self, session_id: str) -> bool:
        """
        Check if there's an active tool session (not just clarification) for the given session ID.
        Updated to work with the new comprehensive tool session management.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if there's an active tool session, False otherwise
        """
        return self.is_tool_session_active(session_id)
    
    def start_tool_clarification(
        self, 
        session_id: str, 
        tool_name: str, 
        tool_info: Dict[str, Any], 
        initial_params: Dict[str, Any], 
        missing_required: List[str]
    ) -> None:
        """
        Start a tool clarification session.
        
        Args:
            session_id (str): Session identifier
            tool_name (str): Name of the tool
            tool_info (Dict[str, Any]): Tool information including schema
            initial_params (Dict[str, Any]): Initially extracted parameters
            missing_required (List[str]): List of missing required parameters
        """
        try:
            schema = tool_info.get('parameters_schema', {})
            required = schema.get('required', [])
            
            pending_session = PendingToolSession(
                tool_name=tool_name,
                tool_info=tool_info,
                schema=schema,
                required=required,
                parameters=initial_params.copy(),
                missing=missing_required.copy(),
                last_question=None,
                asked_count=0,
                created_at=time.time()
            )
            
            self._pending_sessions[session_id] = pending_session
            logging.debug(f'[AIHandler] Started tool clarification session for {tool_name} with missing: {missing_required}')
            
        except Exception as e:
            logging.error(f'[AIHandler] Error starting tool clarification: {e}')
    
    def continue_tool_clarification(self, session_id: str, user_input: str) -> AIResponse:
        """
        Continue a tool clarification session with rigorous gating.
        Only accepts parameter input or cancellation during active tool session.
        
        Args:
            session_id (str): Session identifier
            user_input (str): User's response to clarification question
            
        Returns:
            AIResponse: Either another clarification question, gating notice, or tool execution result
        """
        try:
            if session_id not in self._tool_sessions:
                logging.warning(f'[AIHandler] No tool session found for {session_id}')
                return AIResponse(
                    text="Nessuna sessione tool attiva.",
                    success=False,
                    response_type="error"
                )
            
            session = self._tool_sessions[session_id]
            
            # Check for cancellation keywords
            cancel_keywords = ['annulla', 'cancella', 'stop', 'basta', 'esci']
            if any(keyword in user_input.lower() for keyword in cancel_keywords):
                return self.cancel_tool_session(session_id)
            
            # Extract parameters from user response
            extracted_params = {}
            if self._llm_intent_enabled and self._llm_intent_detector:
                try:
                    extracted_params = self._llm_intent_detector.extract_parameters(
                        user_input,
                        session.tool_name,
                        session.schema
                    )
                    logging.debug(f'[AIHandler] LLM extracted parameters: {extracted_params}')
                except Exception as e:
                    logging.warning(f'[AIHandler] LLM parameter extraction failed: {e}')
            
            # Fallback: try simple pattern matching for common parameters
            if not extracted_params:
                extracted_params = self._fallback_parameter_extraction(user_input, session.missing)
            
            # Normalize parameters (e.g., preferences for navigation)
            extracted_params = self._normalize_parameters(extracted_params, session.tool_name)
            
            # Check if any required parameters were extracted
            relevant_params = {}
            for param_name, param_value in extracted_params.items():
                if param_name in session.missing and param_value:
                    relevant_params[param_name] = param_value
            
            # If no relevant parameters found, send gating notice
            if not relevant_params:
                # This is not pertinent input during tool mode
                gating_message = (
                    f'Sono nel ciclo di vita del Tool "{session.tool_name}" e al momento posso accettare solo:\n'
                    f'- i parametri richiesti: {", ".join(session.missing)}\n'
                    f'- oppure "annulla" per interrompere\n'
                    f'Finché non ricevo {", ".join(session.missing)}, non posso gestire altre richieste. '
                    f'[Modalità Tool attiva: {session.tool_name} | stato: {session.state} | missing: {", ".join(session.missing)}]'
                )
                
                # Emit gating notice event
                self._emit_backend_action('tool_gating_notice', {
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
                self._emit_backend_action('tool_parameter_received', {
                    'session_id': session_id,
                    'tool_name': session.tool_name,
                    'param_name': param_name,
                    'param_value': param_value,
                    'params_partial': session.parameters.copy(),
                    'missing_required': [p for p in session.missing if p != param_name]
                })
            
            # Recalculate missing required parameters
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
            
            # All required parameters collected - execute tool
            logging.info(f'[AIHandler] All parameters collected for {session.tool_name}: {session.parameters}')
            
            # Notify parameters complete and execute directly
            pairs = ", ".join([f'{k} = "{v}"' for k, v in relevant_params.items()])
            param_complete_msg = f'Parametro ricevuto: {pairs}. [Parametri richiesti completi]'
            
            # Execute tool directly
            return self._execute_tool_from_session(session_id, param_complete_msg)
            
        except Exception as e:
            logging.error(f'[AIHandler] Error in tool clarification continuation: {e}')
            
            # Clean up on error
            if session_id in self._tool_sessions:
                self._cleanup_tool_session(session_id, 'error', 'error', f'Error in clarification: {str(e)}')
            
            return AIResponse(
                text="Si è verificato un errore durante il chiarimento dei parametri.",
                success=False,
                response_type="error"
            )
    
    def _execute_tool_from_session(self, session_id: str, prefix_message: str = "") -> AIResponse:
        """
        Execute tool from an existing session.
        """
        if session_id not in self._tool_sessions:
            return AIResponse(
                text="Errore: sessione tool non trovata.",
                success=False,
                response_type="error"
            )
        
        session = self._tool_sessions[session_id]
        
        # Update session state to ready_to_start
        self._update_tool_session_state(session_id, 'ready_to_start')
        self._emit_backend_action('tool_ready_to_start', {
            'session_id': session_id,
            'tool_name': session.tool_name
        })
        
        # Update session state to running
        self._update_tool_session_state(session_id, 'running')
        self._emit_backend_action('tool_started', {
            'session_id': session_id,
            'tool_name': session.tool_name, 
            'parameters': session.parameters
        })
        
        # Execute the tool
        logging.info(f'[AIHandler] Executing tool "{session.tool_name}" with parameters: {session.parameters}')
        tool_result = self._mcp_handler.execute_tool(session.tool_name, session.parameters)
        
        # Emit completion event
        try:
            status_value = getattr(tool_result.status, 'value', str(tool_result.status))
        except Exception:
            status_value = 'unknown'
        
        self._emit_backend_action('tool_finished', {
            'session_id': session_id,
            'tool_name': session.tool_name, 
            'status': status_value
        })
        
        # Clean up session
        self._cleanup_tool_session(session_id, 'finished', status_value, f"Tool {session.tool_name} completed")
        
        # Format result message
        from backend.mcp.mcp_tool import ToolResultStatus
        if tool_result.status == ToolResultStatus.SUCCESS:
            result_message = f"{prefix_message} [tool_ready_to_start → {session.tool_name}] [tool_started → {session.tool_name} | parameters: {session.parameters}] {tool_result.data} [tool_finished → {session.tool_name} | status: {status_value}] [Modalità Tool disattivata: {session.tool_name} | session chiusa]"
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
    
    def cancel_tool_session(self, session_id: str) -> AIResponse:
        """
        Cancel a pending tool clarification session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            AIResponse: Confirmation of cancellation
        """
        try:
            if session_id in self._pending_sessions:
                tool_name = self._pending_sessions[session_id].tool_name
                del self._pending_sessions[session_id]
                
                self._emit_backend_action('tool_canceled', {'tool_name': tool_name})
                
                logging.info(f'[AIHandler] Canceled tool session for {tool_name}')
                return AIResponse(
                    text=f"Operazione {tool_name} annullata.",
                    success=True,
                    response_type="conversational"
                )
            else:
                return AIResponse(
                    text="Nessuna operazione da annullare.",
                    success=True,
                    response_type="conversational"
                )
                
        except Exception as e:
            logging.error(f'[AIHandler] Error canceling tool session: {e}')
            return AIResponse(
                text="Errore durante l'annullamento.",
                success=False,
                response_type="error"
            )
    
    def get_pending_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary of pending session for debugging.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Session summary or None if not found
        """
        if session_id in self._pending_sessions:
            session = self._pending_sessions[session_id]
            return {
                'tool_name': session.tool_name,
                'missing': session.missing,
                'parameters': session.parameters,
                'asked_count': session.asked_count,
                'created_at': session.created_at
            }
        return None
    
    def _generate_clarification_question(self, pending_session: PendingToolSession) -> str:
        """
        Generate a clarification question for missing parameters.
        
        Args:
            pending_session (PendingToolSession): The pending session
            
        Returns:
            str: Clarification question
        """
        try:
            if self._llm_intent_enabled and self._llm_intent_detector:
                # Use LLM to generate contextual question
                try:
                    prompt = get_clarification_prompt(
                        user_input="",  # We don't have the original input here
                        intent=pending_session.tool_name,
                        missing_params=pending_session.missing
                    )
                    
                    response = self._llm_intent_detector._make_llm_request(prompt)
                    if response:
                        # Try to parse the response and extract question
                        import json
                        try:
                            data = json.loads(response)
                            if isinstance(data, dict) and 'questions' in data:
                                return data['questions'][0] if data['questions'] else self._fallback_question(pending_session.missing[0])
                            elif isinstance(data, list) and data:
                                return data[0]
                        except json.JSONDecodeError:
                            pass
                        
                        # If JSON parsing fails, use the response directly if it looks like a question
                        if response.strip().endswith('?'):
                            return response.strip()
                            
                except Exception as e:
                    logging.warning(f'[AIHandler] LLM question generation failed: {e}')
            
            # Fallback to deterministic question for first missing parameter
            return self._fallback_question(pending_session.missing[0])
            
        except Exception as e:
            logging.error(f'[AIHandler] Error generating clarification question: {e}')
            return f"Puoi fornire il parametro mancante: {pending_session.missing[0]}?"
    
    def _fallback_question(self, missing_param: str) -> str:
        """
        Generate a fallback question for a missing parameter.
        
        Args:
            missing_param (str): Name of the missing parameter
            
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
    
    def _fallback_parameter_extraction(self, user_input: str, missing_params: List[str]) -> Dict[str, Any]:
        """
        Fallback parameter extraction using simple pattern matching.
        
        Args:
            user_input (str): User input
            missing_params (List[str]): List of missing parameters
            
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
        
        # Check for toll/highway preferences
        if 'pedaggi' in user_lower or 'toll' in user_lower:
            params['avoid_tolls'] = True
        if 'autostrade' in user_lower or 'highway' in user_lower:
            params['avoid_highways'] = True
        
        return params
    
    def _normalize_parameters(self, params: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """
        Normalize parameters for specific tools (e.g., preferences for navigation).
        
        Args:
            params (Dict[str, Any]): Raw parameters
            tool_name (str): Tool name
            
        Returns:
            Dict[str, Any]: Normalized parameters
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
        
        Args:
            param_name (str): Parameter name (can be nested like 'preferences.avoid_tolls')
            parameters (Dict[str, Any]): Parameters dictionary
            
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

    def shutdown(self) -> None:
        """
        Shutdown the AI handler and clean up resources.
        """
        logging.info('[AIHandler] Shutting down AI handler')
        self._is_enabled = False
        self._tool_detection_enabled = False
        
        if self._mcp_handler:
            try:
                self._mcp_handler.shutdown()
            except Exception as e:
                logging.error(f'[AIHandler] Error shutting down MCP handler: {e}')
    
    def restart_ai_processor(self) -> bool:
        """
        Restart the AI processor.
        """
        try:
            logging.info('[AIHandler] Restarting AI processor')
            self._ai_processor = AIProcessor()
            self._is_enabled = self._ai_processor.is_available()
            
            if self._is_enabled:
                # Re-init detector se necessario
                if self._llm_intent_enabled:
                    try:
                        self._llm_intent_detector = LLMIntentDetector(
                            ai_processor=self._ai_processor,
                            enabled=True
                        )
                    except Exception as e:
                        logging.warning(f'[AIHandler] LLM Intent detector re-init failed: {e}')
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

    #----------------------------------------------------------------
    # TOOL SESSION LIFECYCLE MANAGEMENT METHODS
    #----------------------------------------------------------------
    def is_tool_session_active(self, session_id: str) -> bool:
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
    
    def get_tool_session_state(self, session_id: str) -> Optional[str]:
        """
        Get the current state of a tool session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Optional[str]: Current state or None if session doesn't exist
        """
        if session_id in self._tool_sessions:
            return self._tool_sessions[session_id].state
        return None
    
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
        
        Args:
            session_id (str): Session identifier
            tool_name (str): Name of the tool
            tool_info (Dict[str, Any]): Tool information
            initial_params (Dict[str, Any]): Initial parameters extracted
            missing_required (List[str]): List of missing required parameters
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
            self._emit_backend_action('tool_lifecycle_started', {
                'session_id': session_id,
                'tool_name': tool_name,
                'state': initial_state,
                'missing_required': missing_required,
                'params_partial': initial_params,
                'timestamp': session.created_at
            })
            
            logging.info(f'[AIHandler] Created tool session {session_id} for {tool_name} in state {initial_state}')
            
        except Exception as e:
            logging.error(f'[AIHandler] Error creating tool session: {e}')
    
    def _update_tool_session_state(self, session_id: str, new_state: str, **kwargs) -> None:
        """
        Update the state of a tool session.
        
        Args:
            session_id (str): Session identifier
            new_state (str): New state to set
            **kwargs: Additional data to update in the session
        """
        if session_id not in self._tool_sessions:
            logging.warning(f'[AIHandler] Attempted to update non-existent tool session {session_id}')
            return
        
        session = self._tool_sessions[session_id]
        old_state = session.state
        session.state = new_state
        
        # Update any additional fields passed in kwargs
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        logging.debug(f'[AIHandler] Updated tool session {session_id} state: {old_state} → {new_state}')
    
    def _cleanup_tool_session(self, session_id: str, final_state: str, status: str = "", message: str = "") -> None:
        """
        Clean up and remove a tool session at the end of its lifecycle.
        
        Args:
            session_id (str): Session identifier
            final_state (str): Final state (finished/canceled/error)
            status (str): Final status
            message (str): Final message
        """
        if session_id not in self._tool_sessions:
            return
        
        session = self._tool_sessions[session_id]
        tool_name = session.tool_name
        
        # Emit lifecycle finished event
        self._emit_backend_action('tool_lifecycle_finished', {
            'session_id': session_id,
            'tool_name': tool_name,
            'final_state': final_state,
            'status': status,
            'message': message
        })
        
        # Remove session from memory
        del self._tool_sessions[session_id]
        
        logging.info(f'[AIHandler] Cleaned up tool session {session_id} for {tool_name} with final state {final_state}')
    
    def cancel_tool_session(self, session_id: str) -> AIResponse:
        """
        Cancel an active tool session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            AIResponse: Confirmation of cancellation
        """
        try:
            if session_id not in self._tool_sessions:
                return AIResponse(
                    text="Nessuna operazione da annullare.",
                    success=True,
                    response_type="conversational"
                )
            
            session = self._tool_sessions[session_id]
            tool_name = session.tool_name
            current_state = session.state
            
            # Emit session canceled event
            self._emit_backend_action('tool_session_canceled', {
                'session_id': session_id,
                'tool_name': tool_name,
                'state': current_state,
                'reason': 'user_request',
                'params_partial': session.parameters
            })
            
            # Clean up session
            self._cleanup_tool_session(session_id, 'canceled', 'user_canceled', f'Tool {tool_name} canceled by user')
            
            logging.info(f'[AIHandler] Canceled tool session for {tool_name}')
            return AIResponse(
                text=f'Operazione annullata. Ho terminato il ciclo di vita del Tool "{tool_name}". [tool_session canceled → {tool_name}] [Modalità Tool disattivata: {tool_name} | session chiusa]',
                success=True,
                response_type="conversational"
            )
                
        except Exception as e:
            logging.error(f'[AIHandler] Error canceling tool session: {e}')
            return AIResponse(
                text="Errore durante l'annullamento dell'operazione.",
                success=False,
                response_type="error"
            )
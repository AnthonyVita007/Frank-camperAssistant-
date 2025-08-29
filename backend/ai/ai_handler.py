"""
AI Handler Module for Frank Camper Assistant.

This module provides the integration layer between the AI system and the main controller,
managing AI request validation, processing coordination, and logging.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
from typing import Optional, Dict, Any, List, Union, Callable

from .ai_processor import AIProcessor  # Il processor (può essere single-provider o dual-provider)
from .ai_response import AIResponse
from .llm_intent_detector import LLMIntentDetector, IntentDetectionResult

# Import opzionale dell'Enum AIProvider (presente solo se l'AIProcessor è dual-provider)
try:
    from .ai_processor import AIProvider  # type: ignore
except Exception:
    AIProvider = None  # type: ignore


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
        Handle a request that requires tool execution.
        Ora emette eventi 'backend_action' per mostrare le bubble blu in Debug:
        - tool_selected
        - tool_ready_to_start
        - tool_started
        - tool_finished
        """
        try:
            #----------------------------------------------------------------
            # IDENTIFICAZIONE CATEGORIA E SELEZIONE TOOL
            #----------------------------------------------------------------
            primary_category = tool_intent.get('primary_category')
            logging.info(f'[AIHandler] Processing tool request for category: {primary_category}')
            
            available_tools = self._mcp_handler.get_tools_by_category(primary_category)
            if not available_tools:
                logging.warning(f'[AIHandler] No tools available for category: {primary_category}')
                return self._fallback_to_conversation(user_input, f"Categoria strumenti '{primary_category}' non disponibile")
            
            selected_tool = available_tools[0]
            tool_name = selected_tool.get('name')
            if not tool_name:
                logging.error(f'[AIHandler] Invalid tool info: {selected_tool}')
                return self._fallback_to_conversation(user_input, "Informazioni strumento non valide")
            
            # Notifica selezione tool (bubble blu "Tool selected → <tool>")
            self._emit_backend_action('tool_selected', {'tool_name': tool_name})
            
            #----------------------------------------------------------------
            # ESTRAZIONE PARAMETRI (LLM + fallback) E VALUTAZIONE "READY"
            #----------------------------------------------------------------
            parameters = self._extract_tool_parameters(user_input, tool_name, selected_tool, context)
            
            schema = (selected_tool.get('parameters_schema') or {})
            required = (schema.get('required') or [])
            missing = [r for r in required if r not in parameters]
            if not missing:
                # Notifica che i parametri sono completi (bubble blu "Starting Tool")
                self._emit_backend_action('tool_ready_to_start', {'tool_name': tool_name})
            else:
                logging.debug(f"[AIHandler] Missing required parameters for {tool_name}: {missing}")
                # Nota: la gestione delle domande di chiarimento può essere emessa con 'tool_clarification'
                # quando si implementa il relativo flusso
            
            #----------------------------------------------------------------
            # ESECUZIONE TOOL CON NOTIFICHE CICLO DI VITA
            #----------------------------------------------------------------
            logging.info(f'[AIHandler] Executing tool "{tool_name}" with parameters: {parameters}')
            
            # Notifica avvio tool
            self._emit_backend_action('tool_started', {'tool_name': tool_name, 'parameters': parameters})
            
            # Esecuzione del tool tramite MCP
            tool_result = self._mcp_handler.execute_tool(tool_name, parameters)
            
            # Notifica completamento tool con stato
            try:
                status_value = getattr(tool_result.status, 'value', str(tool_result.status))
            except Exception:
                status_value = 'unknown'
            self._emit_backend_action('tool_finished', {'tool_name': tool_name, 'status': status_value})
            
            #----------------------------------------------------------------
            # CONVERSIONE RISULTATO TOOL → AIResponse
            #----------------------------------------------------------------
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
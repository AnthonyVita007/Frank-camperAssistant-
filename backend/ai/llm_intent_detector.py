"""
LLM Intent Detector Module for Frank Camper Assistant.

This module implements intelligent intent recognition using Large Language Models
to understand natural language requests and extract structured intent information.
It provides a hybrid approach that combines LLM understanding with pattern matching fallback.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
import json
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

from .ai_processor import AIProcessor
from .intent_prompts import (
    get_intent_detection_prompt,
    get_parameter_extraction_prompt,
    get_context_aware_prompt,
    get_multi_intent_prompt,
    get_clarification_prompt
)

#----------------------------------------------------------------
# STRUTTURE DATI PER INTENT DETECTION
#----------------------------------------------------------------

@dataclass
class IntentDetectionResult:
    """
    Structured result from LLM intent detection.
    
    Attributes:
        requires_tool (bool): Whether the request requires tool execution
        primary_intent (Optional[str]): Primary tool category needed
        confidence (float): Confidence score (0.0-1.0)
        extracted_parameters (Dict[str, Any]): Parameters extracted from input
        multi_intent (List[Dict[str, Any]]): Multiple intents if detected
        reasoning (str): LLM reasoning for the decision
        clarification_needed (bool): Whether clarification is needed
        clarification_questions (List[str]): Questions to ask user
        processing_time (float): Time taken for detection
        fallback_used (bool): Whether fallback to pattern matching was used
    """
    requires_tool: bool
    primary_intent: Optional[str]
    confidence: float
    extracted_parameters: Dict[str, Any]
    multi_intent: List[Dict[str, Any]]
    reasoning: str
    clarification_needed: bool
    clarification_questions: List[str] = None
    processing_time: float = 0.0
    fallback_used: bool = False
    
    def __post_init__(self):
        if self.clarification_questions is None:
            self.clarification_questions = []

#----------------------------------------------------------------
# CLASSE PRINCIPALE LLM INTENT DETECTOR
#----------------------------------------------------------------

class LLMIntentDetector:
    """
    LLM-based intent detector for natural language understanding.
    
    This class uses Large Language Models to analyze user requests and extract
    structured intent information, including tool requirements, parameters,
    and confidence scoring. It provides fallback mechanisms and caching
    for improved reliability and performance.
    
    Attributes:
        _ai_processor (AIProcessor): AI processor for LLM communication
        _enabled (bool): Whether LLM intent detection is enabled
        _confidence_threshold_high (float): High confidence threshold
        _confidence_threshold_low (float): Low confidence threshold
        _timeout (float): Maximum time for LLM request
        _cache (Dict): Simple cache for recent results
        _cache_max_size (int): Maximum cache entries
        _cache_ttl (float): Cache time-to-live in seconds
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE LLM INTENT DETECTOR
    #----------------------------------------------------------------
    
    def __init__(
        self,
        ai_processor: Optional[AIProcessor] = None,
        enabled: bool = True,
        confidence_threshold_high: float = 0.8,
        confidence_threshold_low: float = 0.5,
        timeout: float = 5.0,
        cache_max_size: int = 100,
        cache_ttl: float = 300.0  # 5 minutes
    ) -> None:
        """
        Initialize the LLM Intent Detector.
        
        Args:
            ai_processor (Optional[AIProcessor]): AI processor instance
            enabled (bool): Whether LLM detection is enabled
            confidence_threshold_high (float): High confidence threshold (>= this uses LLM result)
            confidence_threshold_low (float): Low confidence threshold (< this uses fallback)
            timeout (float): Maximum time for LLM request in seconds
            cache_max_size (int): Maximum number of cached results
            cache_ttl (float): Cache time-to-live in seconds
        """
        try:
            self._ai_processor = ai_processor or AIProcessor()
            self._enabled = enabled and self._ai_processor.is_available()
            
            # Configuration
            self._confidence_threshold_high = confidence_threshold_high
            self._confidence_threshold_low = confidence_threshold_low
            self._timeout = min(timeout, 5.0)  # Enforce max 5 second timeout
            
            # Simple cache implementation
            self._cache = {}
            self._cache_max_size = cache_max_size
            self._cache_ttl = cache_ttl
            
            # Available tool categories for intent detection
            self._available_categories = ['navigation', 'weather', 'vehicle', 'maintenance']
            
            if self._enabled:
                logging.info('[LLMIntentDetector] Initialized successfully with LLM support')
            else:
                logging.warning('[LLMIntentDetector] Initialized but LLM not available - will use fallback only')
                
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Failed to initialize: {e}')
            self._enabled = False
            self._ai_processor = None
    
    #----------------------------------------------------------------
    # METODI PRINCIPALI PER RICONOSCIMENTO INTENTI
    #----------------------------------------------------------------
    
    def detect_intent(
        self,
        user_input: str,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentDetectionResult:
        """
        Detect intent from user input using LLM analysis.
        
        This is the main entry point for intent detection. It attempts LLM-based
        analysis first, then falls back to pattern matching if needed.
        
        Args:
            user_input (str): The user's input text
            available_tools (Optional[List[str]]): List of available tool names
            context (Optional[Dict[str, Any]]): Conversation context
            
        Returns:
            IntentDetectionResult: Structured intent detection result
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not user_input or not isinstance(user_input, str):
                logging.warning('[LLMIntentDetector] Invalid input received')
                return self._create_error_result("Invalid input", start_time)
            
            user_input = user_input.strip()
            if not user_input:
                logging.warning('[LLMIntentDetector] Empty input received')
                return self._create_error_result("Empty input", start_time)
            
            # Check cache first
            cache_key = self._generate_cache_key(user_input, available_tools, context)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logging.debug('[LLMIntentDetector] Using cached result')
                cached_result.processing_time = time.time() - start_time
                return cached_result
            
            # Attempt LLM-based detection if enabled
            if self._enabled:
                llm_result = self._detect_intent_llm(user_input, available_tools, context)
                
                if llm_result and llm_result.confidence >= self._confidence_threshold_low:
                    # Cache and return LLM result
                    llm_result.processing_time = time.time() - start_time
                    self._cache_result(cache_key, llm_result)
                    
                    logging.info(f'[LLMIntentDetector] LLM detection successful: {llm_result.primary_intent} (confidence: {llm_result.confidence:.2f})')
                    return llm_result
                else:
                    logging.warning(f'[LLMIntentDetector] LLM detection failed or low confidence, using fallback')
            
            # Fallback to pattern matching (this would be the existing method)
            # For now, return a basic result indicating conversational intent
            fallback_result = self._create_conversational_result(user_input, start_time)
            fallback_result.fallback_used = True
            
            self._cache_result(cache_key, fallback_result)
            return fallback_result
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error in intent detection: {e}')
            return self._create_error_result(f"Detection error: {str(e)}", start_time)
    
    def _detect_intent_llm(
        self,
        user_input: str,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentDetectionResult]:
        """
        Perform LLM-based intent detection.
        
        Args:
            user_input (str): The user's input text
            available_tools (Optional[List[str]]): Available tool names
            context (Optional[Dict[str, Any]]): Conversation context
            
        Returns:
            Optional[IntentDetectionResult]: LLM detection result or None if failed
        """
        try:
            # Handle context-aware requests first
            if context and self._is_context_dependent(user_input):
                context_prompt = get_context_aware_prompt(user_input, context)
                context_response = self._make_llm_request(context_prompt)
                
                if context_response:
                    # Parse context response and update user_input if needed
                    try:
                        context_data = json.loads(context_response)
                        if 'interpreted_request' in context_data:
                            user_input = context_data['interpreted_request']
                            logging.debug(f'[LLMIntentDetector] Context resolved: {user_input}')
                    except (json.JSONDecodeError, KeyError):
                        logging.warning('[LLMIntentDetector] Failed to parse context response')
            
            # Generate main intent detection prompt
            prompt = get_intent_detection_prompt(user_input, available_tools, context)
            
            # Make LLM request with timeout
            response = self._make_llm_request(prompt)
            
            if not response:
                logging.warning('[LLMIntentDetector] Empty response from LLM')
                return None
            
            # Parse JSON response
            try:
                intent_data = json.loads(response)
                return self._parse_intent_response(intent_data, user_input)
                
            except json.JSONDecodeError as e:
                logging.error(f'[LLMIntentDetector] Failed to parse LLM JSON response: {e}')
                logging.debug(f'[LLMIntentDetector] Raw response: {response[:200]}...')
                return None
                
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error in LLM intent detection: {e}')
            return None
    
    def extract_parameters(
        self,
        user_input: str,
        tool_name: str,
        tool_schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract parameters for tool execution from natural language input.
        
        Args:
            user_input (str): The user's input text
            tool_name (str): Name of the tool requiring parameters
            tool_schema (Dict[str, Any]): Schema definition for the tool
            context (Optional[Dict[str, Any]]): Additional context
            
        Returns:
            Dict[str, Any]: Extracted parameters for tool execution
        """
        try:
            if not self._enabled:
                logging.debug('[LLMIntentDetector] LLM not enabled for parameter extraction')
                return {}
            
            # Generate parameter extraction prompt
            prompt = get_parameter_extraction_prompt(user_input, tool_name, tool_schema)
            
            # Make LLM request
            response = self._make_llm_request(prompt)
            
            if not response:
                logging.warning('[LLMIntentDetector] Empty response for parameter extraction')
                return {}
            
            # Parse parameter response
            try:
                parameters = json.loads(response)
                
                # Validate parameters against schema if provided
                validated_params = self._validate_parameters(parameters, tool_schema)
                
                logging.debug(f'[LLMIntentDetector] Extracted parameters for {tool_name}: {validated_params}')
                return validated_params
                
            except json.JSONDecodeError as e:
                logging.error(f'[LLMIntentDetector] Failed to parse parameter JSON: {e}')
                return {}
                
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error extracting parameters: {e}')
            return {}
    
    def validate_intent_confidence(self, intent_data: Dict[str, Any]) -> float:
        """
        Validate and potentially adjust confidence score of intent detection.
        
        Args:
            intent_data (Dict[str, Any]): Intent detection data from LLM
            
        Returns:
            float: Validated confidence score (0.0-1.0)
        """
        try:
            confidence = intent_data.get('confidence', 0.0)
            
            # Basic validation
            if not isinstance(confidence, (int, float)):
                logging.warning('[LLMIntentDetector] Invalid confidence type, using 0.0')
                return 0.0
            
            # Clamp to valid range
            confidence = max(0.0, min(1.0, float(confidence)))
            
            # Apply heuristics to adjust confidence
            adjusted_confidence = self._apply_confidence_heuristics(intent_data, confidence)
            
            if adjusted_confidence != confidence:
                logging.debug(f'[LLMIntentDetector] Adjusted confidence from {confidence:.2f} to {adjusted_confidence:.2f}')
            
            return adjusted_confidence
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error validating confidence: {e}')
            return 0.0
    
    #----------------------------------------------------------------
    # METODI HELPER E UTILITY
    #----------------------------------------------------------------
    
    def _make_llm_request(self, prompt: str) -> Optional[str]:
        """
        Make a request to the LLM with timeout and error handling.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Returns:
            Optional[str]: LLM response or None if failed
        """
        try:
            if not self._ai_processor:
                return None
            
            # Create a context with timeout information
            context = {
                'max_tokens': 512,  # Limit response length for structured output
                'temperature': 0.1,  # Low temperature for consistent structured output
                'timeout': self._timeout
            }
            
            # Make the request
            response = self._ai_processor.process_request(prompt, context)
            
            if response.success and response.text:
                return response.text.strip()
            else:
                logging.warning(f'[LLMIntentDetector] LLM request failed: {response.message}')
                return None
                
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error making LLM request: {e}')
            return None
    
    def _parse_intent_response(self, intent_data: Dict[str, Any], user_input: str) -> IntentDetectionResult:
        """
        Parse LLM response into structured IntentDetectionResult.
        
        Args:
            intent_data (Dict[str, Any]): Parsed JSON from LLM
            user_input (str): Original user input
            
        Returns:
            IntentDetectionResult: Structured result
        """
        try:
            # Validate required fields
            requires_tool = intent_data.get('requires_tool', False)
            primary_intent = intent_data.get('primary_intent')
            confidence = self.validate_intent_confidence(intent_data)
            
            # Extract optional fields with defaults
            extracted_parameters = intent_data.get('extracted_parameters', {})
            multi_intent = intent_data.get('multi_intent', [])
            reasoning = intent_data.get('reasoning', 'LLM analysis')
            clarification_needed = intent_data.get('clarification_needed', False)
            clarification_questions = intent_data.get('clarification_questions', [])
            
            return IntentDetectionResult(
                requires_tool=requires_tool,
                primary_intent=primary_intent,
                confidence=confidence,
                extracted_parameters=extracted_parameters,
                multi_intent=multi_intent,
                reasoning=reasoning,
                clarification_needed=clarification_needed,
                clarification_questions=clarification_questions,
                fallback_used=False
            )
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error parsing intent response: {e}')
            # Return low-confidence fallback result
            return IntentDetectionResult(
                requires_tool=False,
                primary_intent=None,
                confidence=0.1,
                extracted_parameters={},
                multi_intent=[],
                reasoning=f"Parsing error: {str(e)}",
                clarification_needed=False,
                fallback_used=True
            )
    
    def _validate_parameters(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted parameters against tool schema.
        
        Args:
            parameters (Dict[str, Any]): Extracted parameters
            schema (Dict[str, Any]): Tool parameter schema
            
        Returns:
            Dict[str, Any]: Validated parameters
        """
        try:
            if not schema:
                return parameters
            
            validated = {}
            schema_props = schema.get('properties', {})
            required = schema.get('required', [])
            
            # Validate each parameter
            for param_name, param_value in parameters.items():
                if param_name in schema_props:
                    # Basic type validation could be added here
                    validated[param_name] = param_value
                else:
                    logging.debug(f'[LLMIntentDetector] Unknown parameter ignored: {param_name}')
            
            # Check for missing required parameters
            missing_required = [req for req in required if req not in validated]
            if missing_required:
                logging.warning(f'[LLMIntentDetector] Missing required parameters: {missing_required}')
            
            return validated
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error validating parameters: {e}')
            return parameters
    
    def _apply_confidence_heuristics(self, intent_data: Dict[str, Any], base_confidence: float) -> float:
        """
        Apply heuristics to adjust confidence score based on various factors.
        
        Args:
            intent_data (Dict[str, Any]): Intent detection data
            base_confidence (float): Base confidence from LLM
            
        Returns:
            float: Adjusted confidence score
        """
        try:
            adjusted = base_confidence
            
            # Reduce confidence if clarification is needed
            if intent_data.get('clarification_needed', False):
                adjusted *= 0.8
            
            # Reduce confidence if no reasoning provided
            reasoning = intent_data.get('reasoning', '')
            if not reasoning or len(reasoning.strip()) < 10:
                adjusted *= 0.9
            
            # Adjust based on parameter extraction quality
            params = intent_data.get('extracted_parameters', {})
            if intent_data.get('requires_tool', False) and not params:
                adjusted *= 0.7  # Tool needed but no parameters extracted
            
            # Boost confidence for clear tool requirements
            if intent_data.get('requires_tool', False) and intent_data.get('primary_intent'):
                if intent_data['primary_intent'] in self._available_categories:
                    adjusted = min(1.0, adjusted * 1.1)
            
            return max(0.0, min(1.0, adjusted))
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error applying confidence heuristics: {e}')
            return base_confidence
    
    def _is_context_dependent(self, user_input: str) -> bool:
        """
        Check if user input appears to be context-dependent.
        
        Args:
            user_input (str): User input text
            
        Returns:
            bool: True if input seems context-dependent
        """
        # Simple heuristics for context dependency
        context_indicators = [
            'e per', 'e domani', 'e oggi', 'anche', 'pure',
            'come va', 'come sta', 'e quello', 'e questo',
            'e dopo', 'e prima', 'e poi'
        ]
        
        input_lower = user_input.lower()
        return any(indicator in input_lower for indicator in context_indicators)
    
    #----------------------------------------------------------------
    # METODI PER CACHING
    #----------------------------------------------------------------
    
    def _generate_cache_key(
        self,
        user_input: str,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key for intent detection result.
        
        Args:
            user_input (str): User input
            available_tools (Optional[List[str]]): Available tools
            context (Optional[Dict[str, Any]]): Context
            
        Returns:
            str: Cache key
        """
        # Simple cache key generation
        tools_str = ','.join(sorted(available_tools)) if available_tools else ''
        context_str = str(hash(str(context))) if context else ''
        
        # Use hash to keep key length manageable
        key_data = f"{user_input}|{tools_str}|{context_str}"
        return str(hash(key_data))
    
    def _get_cached_result(self, cache_key: str) -> Optional[IntentDetectionResult]:
        """
        Get cached intent detection result if available and not expired.
        
        Args:
            cache_key (str): Cache key
            
        Returns:
            Optional[IntentDetectionResult]: Cached result or None
        """
        try:
            if cache_key not in self._cache:
                return None
            
            cached_entry = self._cache[cache_key]
            timestamp = cached_entry.get('timestamp', 0)
            
            # Check if expired
            if time.time() - timestamp > self._cache_ttl:
                del self._cache[cache_key]
                return None
            
            return cached_entry.get('result')
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error getting cached result: {e}')
            return None
    
    def _cache_result(self, cache_key: str, result: IntentDetectionResult) -> None:
        """
        Cache intent detection result.
        
        Args:
            cache_key (str): Cache key
            result (IntentDetectionResult): Result to cache
        """
        try:
            # Clean cache if it's getting too large
            if len(self._cache) >= self._cache_max_size:
                self._clean_cache()
            
            self._cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error caching result: {e}')
    
    def _clean_cache(self) -> None:
        """Clean expired entries from cache."""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self._cache.items():
                if current_time - entry.get('timestamp', 0) > self._cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            logging.debug(f'[LLMIntentDetector] Cleaned {len(expired_keys)} expired cache entries')
            
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error cleaning cache: {e}')
    
    #----------------------------------------------------------------
    # METODI PER RISULTATI DI FALLBACK
    #----------------------------------------------------------------
    
    def _create_error_result(self, error_message: str, start_time: float) -> IntentDetectionResult:
        """
        Create an error result for intent detection.
        
        Args:
            error_message (str): Error message
            start_time (float): Detection start time
            
        Returns:
            IntentDetectionResult: Error result
        """
        return IntentDetectionResult(
            requires_tool=False,
            primary_intent=None,
            confidence=0.0,
            extracted_parameters={},
            multi_intent=[],
            reasoning=f"Error: {error_message}",
            clarification_needed=False,
            processing_time=time.time() - start_time,
            fallback_used=True
        )
    
    def _create_conversational_result(self, user_input: str, start_time: float) -> IntentDetectionResult:
        """
        Create a conversational result (no tool needed).
        
        Args:
            user_input (str): User input
            start_time (float): Detection start time
            
        Returns:
            IntentDetectionResult: Conversational result
        """
        return IntentDetectionResult(
            requires_tool=False,
            primary_intent=None,
            confidence=0.8,  # High confidence for conversational
            extracted_parameters={},
            multi_intent=[],
            reasoning="Conversational request, no tools needed",
            clarification_needed=False,
            processing_time=time.time() - start_time,
            fallback_used=True
        )
    
    #----------------------------------------------------------------
    # CONFIGURAZIONE E STATUS
    #----------------------------------------------------------------
    
    def is_enabled(self) -> bool:
        """
        Check if LLM intent detection is enabled and available.
        
        Returns:
            bool: True if enabled and available
        """
        return self._enabled and self._ai_processor is not None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the LLM intent detector.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'enabled': self._enabled,
            'ai_processor_available': self._ai_processor is not None,
            'confidence_threshold_high': self._confidence_threshold_high,
            'confidence_threshold_low': self._confidence_threshold_low,
            'timeout': self._timeout,
            'cache_size': len(self._cache),
            'cache_max_size': self._cache_max_size,
            'available_categories': self._available_categories
        }
    
    def enable(self) -> bool:
        """
        Enable LLM intent detection.
        
        Returns:
            bool: True if successfully enabled
        """
        try:
            if self._ai_processor and self._ai_processor.is_available():
                self._enabled = True
                logging.info('[LLMIntentDetector] LLM intent detection enabled')
                return True
            else:
                logging.warning('[LLMIntentDetector] Cannot enable - AI processor not available')
                return False
        except Exception as e:
            logging.error(f'[LLMIntentDetector] Error enabling: {e}')
            return False
    
    def disable(self) -> None:
        """Disable LLM intent detection."""
        self._enabled = False
        logging.info('[LLMIntentDetector] LLM intent detection disabled')
    
    def clear_cache(self) -> None:
        """Clear the intent detection cache."""
        self._cache.clear()
        logging.info('[LLMIntentDetector] Cache cleared')
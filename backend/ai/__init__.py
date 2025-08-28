"""
AI Module for Frank Camper Assistant.

This module provides artificial intelligence capabilities using Ollama
for processing non-command text inputs from users. It includes both
traditional pattern matching and advanced LLM-based intent recognition
with configuration management.
"""

from .ai_response import AIResponse
from .ai_processor import AIProcessor
from .ai_handler import AIHandler
from .llm_intent_detector import LLMIntentDetector, IntentDetectionResult
from .llm_intent_config import load_llm_intent_config, create_llm_intent_detector_from_config, get_config_summary

__all__ = [
    'AIResponse', 
    'AIProcessor', 
    'AIHandler', 
    'LLMIntentDetector', 
    'IntentDetectionResult',
    'load_llm_intent_config',
    'create_llm_intent_detector_from_config',
    'get_config_summary'
]
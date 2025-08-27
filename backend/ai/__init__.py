"""
AI Module for Frank Camper Assistant.

This module provides artificial intelligence capabilities using Ollama
for processing non-command text inputs from users.
"""

from .ai_response import AIResponse
from .ai_processor import AIProcessor
from .ai_handler import AIHandler

__all__ = ['AIResponse', 'AIProcessor', 'AIHandler']
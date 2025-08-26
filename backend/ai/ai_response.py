"""
AI Response Module for Frank Camper Assistant.

This module defines the AIResponse class, which structures AI-generated responses
similar to CommandResult but specifically for AI interactions.
"""

import logging
from typing import Dict, Any, Optional, List


class AIResponse:
    """
    Represents the result of processing an AI request.
    
    This class encapsulates the outcome of AI processing using Google Gemini,
    including the response text, metadata, and any suggested actions.
    
    Attributes:
        text (str): The AI-generated response text
        response_type (str): Type of response (e.g., 'conversational', 'informational')
        metadata (Dict[str, Any]): Additional metadata about the response
        suggested_actions (List[str]): Optional suggested actions for the user
        success (bool): Whether the AI request was processed successfully
        message (str): Human-readable message about the result
    """
    
    def __init__(
        self, 
        text: str, 
        response_type: str = 'conversational',
        metadata: Optional[Dict[str, Any]] = None,
        suggested_actions: Optional[List[str]] = None,
        success: bool = True, 
        message: str = ""
    ) -> None:
        """
        Initialize an AIResponse.
        
        Args:
            text (str): The AI-generated response text
            response_type (str): Type of response (default: 'conversational')
            metadata (Optional[Dict[str, Any]]): Additional metadata (default: None)
            suggested_actions (Optional[List[str]]): Suggested actions (default: None)
            success (bool): Whether the request was successful (default: True)
            message (str): Human-readable message (default: "")
        """
        self.text = text
        self.response_type = response_type
        self.metadata = metadata or {}
        self.suggested_actions = suggested_actions or []
        self.success = success
        self.message = message
        
        logging.debug(f'[AIResponse] Created AI response: success={success}, type={response_type}')
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the AIResponse to a dictionary for JSON serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the response
        """
        return {
            'text': self.text,
            'response_type': self.response_type,
            'metadata': self.metadata,
            'suggested_actions': self.suggested_actions,
            'success': self.success,
            'message': self.message
        }
    
    def __str__(self) -> str:
        """
        String representation of the AIResponse.
        
        Returns:
            str: Human-readable string representation
        """
        status = "SUCCESS" if self.success else "ERROR"
        return f"AIResponse[{status}]: {self.text[:100]}{'...' if len(self.text) > 100 else ''}"
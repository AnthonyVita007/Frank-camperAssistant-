"""
Base MCP Tool Module for Frank Camper Assistant.

This module defines the base classes for MCP tools and their results,
providing a structured interface for AI-tool interactions.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import json


class ToolResultType(Enum):
    """
    Enumeration of tool result types.
    
    Defines the possible outcomes of tool execution:
    - SUCCESS: Operation completed successfully
    - ERROR: Operation failed
    - WARNING: Operation succeeded with warnings
    - INFO: Informational result
    """
    SUCCESS = "success"
    ERROR = "error" 
    WARNING = "warning"
    INFO = "info"


class ToolResult:
    """
    Represents the result of executing an MCP tool.
    
    This class encapsulates the outcome of tool execution with structured
    data, messages, and metadata for the AI to process.
    
    Attributes:
        result_type (ToolResultType): Type of result
        data (Dict[str, Any]): Structured data payload
        message (str): Human-readable message
        metadata (Dict[str, Any]): Additional metadata
        success (bool): Whether the operation was successful
    """
    
    def __init__(
        self,
        result_type: ToolResultType,
        data: Optional[Dict[str, Any]] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a ToolResult.
        
        Args:
            result_type (ToolResultType): Type of the result
            data (Optional[Dict[str, Any]]): Structured data payload
            message (str): Human-readable message
            metadata (Optional[Dict[str, Any]]): Additional metadata
        """
        self.result_type = result_type
        self.data = data or {}
        self.message = message
        self.metadata = metadata or {}
        self.success = result_type in [ToolResultType.SUCCESS, ToolResultType.INFO]
        
        logging.debug(f'[ToolResult] Created tool result: type={result_type.value}, success={self.success}')
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ToolResult to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the result
        """
        return {
            'result_type': self.result_type.value,
            'data': self.data,
            'message': self.message,
            'metadata': self.metadata,
            'success': self.success
        }
    
    def __str__(self) -> str:
        """
        String representation of the ToolResult.
        
        Returns:
            str: Human-readable string representation
        """
        return f"ToolResult[{self.result_type.value.upper()}]: {self.message}"


class MCPTool(ABC):
    """
    Abstract base class for MCP tools.
    
    This class defines the interface that all MCP tools must implement,
    providing schema definition, parameter validation, and execution methods.
    
    Attributes:
        name (str): The tool name
        description (str): Tool description
    """
    
    def __init__(self, name: str, description: str) -> None:
        """
        Initialize the MCPTool.
        
        Args:
            name (str): The tool name
            description (str): Tool description
        """
        self.name = name
        self.description = description
        
        logging.debug(f'[MCPTool] Initialized tool: {name}')
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for the tool's parameters.
        
        Returns:
            Dict[str, Any]: JSON schema defining the tool's input parameters
        """
        pass
    
    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters (Dict[str, Any]): Tool parameters
            
        Returns:
            ToolResult: Result of tool execution
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Validate the given parameters against the tool's schema.
        
        Args:
            parameters (Dict[str, Any]): Parameters to validate
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        schema = self.get_schema()
        
        # Basic validation - check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in parameters:
                errors.append(f"Missing required parameter: {field}")
        
        # Type validation for present fields
        properties = schema.get('properties', {})
        for field, value in parameters.items():
            if field in properties:
                field_type = properties[field].get('type')
                if field_type and not self._validate_type(value, field_type):
                    errors.append(f"Invalid type for parameter '{field}': expected {field_type}")
        
        return errors
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate a value against an expected JSON schema type.
        
        Args:
            value (Any): Value to validate
            expected_type (str): Expected JSON schema type
            
        Returns:
            bool: True if value matches expected type
        """
        type_mapping = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'object': dict,
            'array': list
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, assume valid
        
        return isinstance(value, expected_python_type)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get tool information including name, description, and schema.
        
        Returns:
            Dict[str, Any]: Tool information dictionary
        """
        return {
            'name': self.name,
            'description': self.description,
            'schema': self.get_schema()
        }
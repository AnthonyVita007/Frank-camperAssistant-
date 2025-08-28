"""
MCP Tool Base Module for Frank Camper Assistant.

This module defines the base class for all MCP tools and the standard interface
that tools must implement to be compatible with the MCP system.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ToolResultStatus(Enum):
    """
    Enumeration of possible tool execution results.
    """
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    REQUIRES_CONFIRMATION = "requires_confirmation"


@dataclass
class ToolResult:
    """
    Represents the result of a tool execution.
    
    Attributes:
        status (ToolResultStatus): The execution status
        data (Any): The result data or output
        message (str): Human-readable message about the result
        metadata (Dict[str, Any]): Additional metadata
        requires_action (bool): Whether this result requires user action
        confirmation_message (str): Message to show for confirmation requests
    """
    status: ToolResultStatus
    data: Any = None
    message: str = ""
    metadata: Optional[Dict[str, Any]] = None
    requires_action: bool = False
    confirmation_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ToolResult to dictionary format."""
        return {
            'status': self.status.value,
            'data': self.data,
            'message': self.message,
            'metadata': self.metadata or {},
            'requires_action': self.requires_action,
            'confirmation_message': self.confirmation_message
        }


class MCPTool(ABC):
    """
    Abstract base class for all MCP tools.
    
    This class defines the standard interface that all tools must implement
    to be compatible with the MCP system in Frank Camper Assistant.
    
    Attributes:
        name (str): Unique identifier for the tool
        description (str): Human-readable description of what the tool does
        category (str): Category this tool belongs to
        parameters_schema (Dict[str, Any]): JSON schema for tool parameters
        requires_confirmation (bool): Whether tool actions need user confirmation
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE E METADATI TOOL
    #----------------------------------------------------------------
    def __init__(self, name: str, description: str, category: str = "general") -> None:
        """
        Initialize the MCP tool.
        
        Args:
            name (str): Unique tool identifier
            description (str): Tool description
            category (str): Tool category (default: "general")
        """
        self.name = name
        self.description = description
        self.category = category
        self.requires_confirmation = False
        self._is_enabled = True
        
        logging.debug(f'[MCPTool] Initialized tool: {name} ({category})')
    
    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """
        Define the JSON schema for tool parameters.
        
        This property must be implemented by each tool to define
        what parameters it accepts and their validation rules.
        
        Returns:
            Dict[str, Any]: JSON schema for parameters
        """
        pass
    
    #----------------------------------------------------------------
    # ESECUZIONE TOOL PRINCIPALE
    #----------------------------------------------------------------
    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        This is the main method that performs the tool's action.
        Must be implemented by each concrete tool.
        
        Args:
            parameters (Dict[str, Any]): Validated parameters for execution
            
        Returns:
            ToolResult: The result of the tool execution
        """
        pass
    
    #----------------------------------------------------------------
    # VALIDAZIONE E UTILITÀ
    #----------------------------------------------------------------
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters against the tool's schema.
        
        Args:
            parameters (Dict[str, Any]): Parameters to validate
            
        Returns:
            bool: True if parameters are valid, False otherwise
        """
        try:
            # Implementazione base di validazione
            # I tool concreti possono sovrascrivere per validazioni specifiche
            required_params = self._get_required_parameters()
            
            # Verifica parametri obbligatori
            for param in required_params:
                if param not in parameters:
                    logging.warning(f'[MCPTool] Missing required parameter: {param}')
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f'[MCPTool] Error validating parameters: {e}')
            return False
    
    def _get_required_parameters(self) -> List[str]:
        """
        Extract required parameters from schema.
        
        Returns:
            List[str]: List of required parameter names
        """
        schema = self.parameters_schema
        return schema.get('required', [])
    
    #----------------------------------------------------------------
    # GESTIONE STATO E DISPONIBILITÀ
    #----------------------------------------------------------------
    def is_available(self) -> bool:
        """
        Check if the tool is available for use.
        
        Returns:
            bool: True if tool is available, False otherwise
        """
        return self._is_enabled
    
    def enable(self) -> None:
        """Enable the tool for use."""
        self._is_enabled = True
        logging.debug(f'[MCPTool] Enabled tool: {self.name}')
    
    def disable(self) -> None:
        """Disable the tool from use."""
        self._is_enabled = False
        logging.debug(f'[MCPTool] Disabled tool: {self.name}')
    
    #----------------------------------------------------------------
    # METADATA E DOCUMENTAZIONE
    #----------------------------------------------------------------
    def get_tool_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the tool.
        
        Returns:
            Dict[str, Any]: Tool information including schema and metadata
        """
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'parameters_schema': self.parameters_schema,
            'requires_confirmation': self.requires_confirmation,
            'is_available': self.is_available(),
            'required_parameters': self._get_required_parameters()
        }
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """
        Get usage examples for the tool.
        
        Override this method in concrete tools to provide helpful examples.
        
        Returns:
            List[Dict[str, Any]]: List of usage examples
        """
        return [
            {
                'description': f'Example usage of {self.name}',
                'parameters': {},
                'expected_result': 'Tool execution result'
            }
        ]
    
    #----------------------------------------------------------------
    # RAPPRESENTAZIONE STRINGA
    #----------------------------------------------------------------
    def __str__(self) -> str:
        """String representation of the tool."""
        status = "ENABLED" if self.is_available() else "DISABLED"
        return f"MCPTool[{self.name}]: {self.description} ({status})"
    
    def __repr__(self) -> str:
        """Detailed representation of the tool."""
        return f"MCPTool(name='{self.name}', category='{self.category}', enabled={self.is_available()})"
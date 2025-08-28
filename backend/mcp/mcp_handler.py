"""
MCP Handler Module for Frank Camper Assistant.

This module provides the main orchestration layer for the MCP system,
coordinating between AI requests, tool execution, and response generation.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
from typing import Dict, Any, Optional, List
from .mcp_tool import MCPTool, ToolResult, ToolResultStatus
from .tool_registry import ToolRegistry


class MCPHandler:
    """
    Main handler for MCP (Model Context Protocol) operations.
    
    This class serves as the central coordinator for the MCP system,
    managing the interaction between AI requests, tool discovery,
    parameter extraction, and tool execution.
    
    Attributes:
        _tool_registry (ToolRegistry): Registry of available tools
        _is_enabled (bool): Whether MCP processing is enabled
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE MCP HANDLER
    #----------------------------------------------------------------
    def __init__(self, tool_registry: Optional[ToolRegistry] = None) -> None:
        """
        Initialize the MCP handler.
        
        Args:
            tool_registry (Optional[ToolRegistry]): Custom tool registry.
                                                   If None, creates a default one.
        """
        try:
            self._tool_registry = tool_registry or ToolRegistry()
            self._is_enabled = True
            
            logging.info('[MCPHandler] MCP handler initialized successfully')
            
        except Exception as e:
            logging.error(f'[MCPHandler] Failed to initialize MCP handler: {e}')
            self._tool_registry = ToolRegistry()
            self._is_enabled = False
    
    #----------------------------------------------------------------
    # REGISTRAZIONE E GESTIONE TOOL
    #----------------------------------------------------------------
    def register_tool(self, tool: MCPTool, enable_by_default: bool = True) -> bool:
        """
        Register a tool with the MCP system.
        
        Args:
            tool (MCPTool): The tool to register
            enable_by_default (bool): Whether to enable the tool by default
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        if not self._is_enabled:
            logging.warning('[MCPHandler] Cannot register tool - MCP handler is disabled')
            return False
        
        return self._tool_registry.register_tool(tool, enable_by_default)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get information about all available tools.
        
        Returns:
            List[Dict[str, Any]]: List of tool information dictionaries
        """
        if not self._is_enabled:
            return []
        
        return self._tool_registry.list_enabled_tools()
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get tools filtered by category.
        
        Args:
            category (str): Category to filter by
            
        Returns:
            List[Dict[str, Any]]: List of tools in the specified category
        """
        if not self._is_enabled:
            return []
        
        tools = self._tool_registry.get_tools_by_category(category)
        return [tool.get_tool_info() for tool in tools]
    
    #----------------------------------------------------------------
    # ESECUZIONE TOOL PRINCIPALE
    #----------------------------------------------------------------
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name (str): Name of the tool to execute
            parameters (Dict[str, Any]): Parameters for tool execution
            
        Returns:
            ToolResult: Result of tool execution
        """
        if not self._is_enabled:
            logging.warning('[MCPHandler] Tool execution requested but MCP handler is disabled')
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message="MCP system is not enabled",
                data=None
            )
        
        logging.info(f'[MCPHandler] Executing tool: {tool_name}')
        logging.debug(f'[MCPHandler] Tool parameters: {parameters}')
        
        try:
            result = self._tool_registry.execute_tool(tool_name, parameters)
            
            # Log execution results
            if result.status == ToolResultStatus.SUCCESS:
                logging.info(f'[MCPHandler] Tool execution successful: {tool_name}')
            elif result.status == ToolResultStatus.ERROR:
                logging.warning(f'[MCPHandler] Tool execution failed: {tool_name} - {result.message}')
            elif result.status == ToolResultStatus.REQUIRES_CONFIRMATION:
                logging.info(f'[MCPHandler] Tool requires confirmation: {tool_name}')
            
            return result
            
        except Exception as e:
            logging.error(f'[MCPHandler] Unexpected error executing tool {tool_name}: {e}')
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Unexpected error executing tool: {str(e)}",
                data=None
            )
    
    #----------------------------------------------------------------
    # RICERCA E DISCOVERY TOOL
    #----------------------------------------------------------------
    def find_tools_for_intent(self, intent_description: str) -> List[Dict[str, Any]]:
        """
        Find tools that might be suitable for a given intent.
        
        Args:
            intent_description (str): Description of the user's intent
            
        Returns:
            List[Dict[str, Any]]: List of potentially suitable tools
        """
        if not self._is_enabled:
            return []
        
        # Use registry search functionality
        matching_tools = self._tool_registry.search_tools(intent_description)
        return [tool.get_tool_info() for tool in matching_tools]
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name (str): Name of the tool
            
        Returns:
            Optional[Dict[str, Any]]: Tool information or None if not found
        """
        if not self._is_enabled:
            return None
        
        tool = self._tool_registry.get_tool(tool_name)
        if tool:
            return tool.get_tool_info()
        return None
    
    #----------------------------------------------------------------
    # GESTIONE CATEGORIE E STATISTICHE
    #----------------------------------------------------------------
    def get_categories(self) -> List[str]:
        """
        Get all available tool categories.
        
        Returns:
            List[str]: List of category names
        """
        if not self._is_enabled:
            return []
        
        return self._tool_registry.get_categories()
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the MCP system.
        
        Returns:
            Dict[str, Any]: System status information
        """
        status = {
            'mcp_enabled': self._is_enabled,
            'registry_status': 'unknown',
            'tools': [],
            'categories': [],
            'stats': {}
        }
        
        if self._is_enabled and self._tool_registry:
            try:
                status['registry_status'] = 'active'
                status['tools'] = self.get_available_tools()
                status['categories'] = self.get_categories()
                status['stats'] = self._tool_registry.get_registry_stats()
            except Exception as e:
                logging.error(f'[MCPHandler] Error getting system status: {e}')
                status['registry_status'] = f'error: {str(e)}'
        
        return status
    
    #----------------------------------------------------------------
    # VALIDAZIONE E MANUTENZIONE
    #----------------------------------------------------------------
    def validate_system(self) -> Dict[str, Any]:
        """
        Validate the entire MCP system.
        
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            'overall_status': 'unknown',
            'mcp_handler': self._is_enabled,
            'tool_registry': False,
            'tool_validations': {},
            'errors': []
        }
        
        try:
            if not self._is_enabled:
                validation_results['errors'].append('MCP handler is disabled')
                validation_results['overall_status'] = 'disabled'
                return validation_results
            
            # Validate tool registry
            if self._tool_registry:
                validation_results['tool_registry'] = True
                validation_results['tool_validations'] = self._tool_registry.validate_all_tools()
            else:
                validation_results['errors'].append('Tool registry is not available')
            
            # Determine overall status
            if validation_results['tool_registry'] and not validation_results['errors']:
                validation_results['overall_status'] = 'healthy'
            elif validation_results['errors']:
                validation_results['overall_status'] = 'error'
            else:
                validation_results['overall_status'] = 'degraded'
            
        except Exception as e:
            logging.error(f'[MCPHandler] Error during system validation: {e}')
            validation_results['errors'].append(f'Validation error: {str(e)}')
            validation_results['overall_status'] = 'error'
        
        return validation_results
    
    #----------------------------------------------------------------
    # ABILITAZIONE E CONTROLLO SISTEMA
    #----------------------------------------------------------------
    def enable_mcp(self) -> bool:
        """
        Enable the MCP system.
        
        Returns:
            bool: True if successfully enabled, False otherwise
        """
        try:
            self._is_enabled = True
            logging.info('[MCPHandler] MCP system enabled')
            return True
        except Exception as e:
            logging.error(f'[MCPHandler] Error enabling MCP system: {e}')
            return False
    
    def disable_mcp(self) -> bool:
        """
        Disable the MCP system.
        
        Returns:
            bool: True if successfully disabled, False otherwise
        """
        try:
            self._is_enabled = False
            logging.info('[MCPHandler] MCP system disabled')
            return True
        except Exception as e:
            logging.error(f'[MCPHandler] Error disabling MCP system: {e}')
            return False
    
    def is_enabled(self) -> bool:
        """
        Check if the MCP system is enabled.
        
        Returns:
            bool: True if enabled, False otherwise
        """
        return self._is_enabled
    
    #----------------------------------------------------------------
    # SHUTDOWN E CLEANUP
    #----------------------------------------------------------------
    def shutdown(self) -> None:
        """
        Shutdown the MCP handler and clean up resources.
        """
        try:
            logging.info('[MCPHandler] Shutting down MCP handler')
            self._is_enabled = False
            # Tool registry doesn't need explicit cleanup in current implementation
            
        except Exception as e:
            logging.error(f'[MCPHandler] Error during shutdown: {e}')
    
    #----------------------------------------------------------------
    # RAPPRESENTAZIONE STRINGA
    #----------------------------------------------------------------
    def __str__(self) -> str:
        """String representation of the MCP handler."""
        status = "ENABLED" if self._is_enabled else "DISABLED"
        tool_count = len(self.get_available_tools()) if self._is_enabled else 0
        return f"MCPHandler[{status}]: {tool_count} tools available"
    
    def __repr__(self) -> str:
        """Detailed representation of the MCP handler."""
        return f"MCPHandler(enabled={self._is_enabled}, registry={self._tool_registry is not None})"
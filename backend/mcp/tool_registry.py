"""
Tool Registry Module for Frank Camper Assistant.

This module manages the registration, discovery, and lifecycle of MCP tools,
providing a centralized catalog of available capabilities.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
from typing import Dict, List, Any, Optional, Type
from collections import defaultdict
from .mcp_tool import MCPTool, ToolResult


class ToolRegistry:
    """
    Central registry for managing MCP tools in Frank Camper Assistant.
    
    This class provides a centralized way to register, discover, and manage
    all available MCP tools in the system. It handles tool lifecycle,
    categorization, and provides search capabilities.
    
    Attributes:
        _tools (Dict[str, MCPTool]): Registry of tools by name
        _categories (Dict[str, List[str]]): Tools organized by category
        _enabled_tools (Dict[str, bool]): Enable/disable status of tools
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE REGISTRY
    #----------------------------------------------------------------
    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: Dict[str, MCPTool] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)
        self._enabled_tools: Dict[str, bool] = {}
        
        logging.debug('[ToolRegistry] Tool registry initialized')
    
    #----------------------------------------------------------------
    # REGISTRAZIONE E GESTIONE TOOL
    #----------------------------------------------------------------
    def register_tool(self, tool: MCPTool, enable_by_default: bool = True) -> bool:
        """
        Register a new tool in the registry.
        
        Args:
            tool (MCPTool): The tool to register
            enable_by_default (bool): Whether to enable the tool by default
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            if not isinstance(tool, MCPTool):
                logging.error(f'[ToolRegistry] Invalid tool type: {type(tool)}')
                return False
            
            tool_name = tool.name
            
            # Check for name conflicts
            if tool_name in self._tools:
                logging.warning(f'[ToolRegistry] Tool already registered: {tool_name}')
                return False
            
            # Register the tool
            self._tools[tool_name] = tool
            self._enabled_tools[tool_name] = enable_by_default
            
            # Add to category index
            category = tool.category
            if tool_name not in self._categories[category]:
                self._categories[category].append(tool_name)
            
            logging.info(f'[ToolRegistry] Registered tool: {tool_name} ({category})')
            return True
            
        except Exception as e:
            logging.error(f'[ToolRegistry] Error registering tool: {e}')
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name (str): Name of the tool to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        try:
            if tool_name not in self._tools:
                logging.warning(f'[ToolRegistry] Tool not found for unregistration: {tool_name}')
                return False
            
            # Get tool info before removal
            tool = self._tools[tool_name]
            category = tool.category
            
            # Remove from main registry
            del self._tools[tool_name]
            del self._enabled_tools[tool_name]
            
            # Remove from category index
            if tool_name in self._categories[category]:
                self._categories[category].remove(tool_name)
            
            # Clean up empty categories
            if not self._categories[category]:
                del self._categories[category]
            
            logging.info(f'[ToolRegistry] Unregistered tool: {tool_name}')
            return True
            
        except Exception as e:
            logging.error(f'[ToolRegistry] Error unregistering tool: {e}')
            return False
    
    #----------------------------------------------------------------
    # RICERCA E ACCESSO TOOL
    #----------------------------------------------------------------
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name (str): Name of the tool to retrieve
            
        Returns:
            Optional[MCPTool]: The tool if found and enabled, None otherwise
        """
        if tool_name not in self._tools:
            logging.debug(f'[ToolRegistry] Tool not found: {tool_name}')
            return None
        
        if not self._enabled_tools.get(tool_name, False):
            logging.debug(f'[ToolRegistry] Tool disabled: {tool_name}')
            return None
        
        return self._tools[tool_name]
    
    def get_tools_by_category(self, category: str) -> List[MCPTool]:
        """
        Get all enabled tools in a specific category.
        
        Args:
            category (str): Category to search for
            
        Returns:
            List[MCPTool]: List of enabled tools in the category
        """
        tools = []
        tool_names = self._categories.get(category, [])
        
        for tool_name in tool_names:
            if self._enabled_tools.get(tool_name, False):
                tool = self._tools.get(tool_name)
                if tool:
                    tools.append(tool)
        
        return tools
    
    def search_tools(self, query: str) -> List[MCPTool]:
        """
        Search tools by name or description.
        
        Args:
            query (str): Search query
            
        Returns:
            List[MCPTool]: List of matching enabled tools
        """
        matching_tools = []
        query_lower = query.lower()
        
        for tool_name, tool in self._tools.items():
            if not self._enabled_tools.get(tool_name, False):
                continue
            
            # Search in name and description
            if (query_lower in tool_name.lower() or 
                query_lower in tool.description.lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    #----------------------------------------------------------------
    # GESTIONE ABILITAZIONE TOOL
    #----------------------------------------------------------------
    def enable_tool(self, tool_name: str) -> bool:
        """
        Enable a tool.
        
        Args:
            tool_name (str): Name of the tool to enable
            
        Returns:
            bool: True if successfully enabled, False otherwise
        """
        if tool_name not in self._tools:
            logging.warning(f'[ToolRegistry] Cannot enable non-existent tool: {tool_name}')
            return False
        
        self._enabled_tools[tool_name] = True
        self._tools[tool_name].enable()
        logging.info(f'[ToolRegistry] Enabled tool: {tool_name}')
        return True
    
    def disable_tool(self, tool_name: str) -> bool:
        """
        Disable a tool.
        
        Args:
            tool_name (str): Name of the tool to disable
            
        Returns:
            bool: True if successfully disabled, False otherwise
        """
        if tool_name not in self._tools:
            logging.warning(f'[ToolRegistry] Cannot disable non-existent tool: {tool_name}')
            return False
        
        self._enabled_tools[tool_name] = False
        self._tools[tool_name].disable()
        logging.info(f'[ToolRegistry] Disabled tool: {tool_name}')
        return True
    
    #----------------------------------------------------------------
    # INFORMAZIONI E STATISTICHE REGISTRY
    #----------------------------------------------------------------
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools with their information.
        
        Returns:
            List[Dict[str, Any]]: List of tool information dictionaries
        """
        tools_info = []
        for tool_name, tool in self._tools.items():
            tool_info = tool.get_tool_info()
            tool_info['enabled_in_registry'] = self._enabled_tools.get(tool_name, False)
            tools_info.append(tool_info)
        
        return tools_info
    
    def list_enabled_tools(self) -> List[Dict[str, Any]]:
        """
        List only enabled tools with their information.
        
        Returns:
            List[Dict[str, Any]]: List of enabled tool information dictionaries
        """
        enabled_tools = []
        for tool_name, is_enabled in self._enabled_tools.items():
            if is_enabled and tool_name in self._tools:
                tool_info = self._tools[tool_name].get_tool_info()
                tool_info['enabled_in_registry'] = True
                enabled_tools.append(tool_info)
        
        return enabled_tools
    
    def get_categories(self) -> List[str]:
        """
        Get all available categories.
        
        Returns:
            List[str]: List of category names
        """
        return list(self._categories.keys())
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the tool registry.
        
        Returns:
            Dict[str, Any]: Registry statistics
        """
        total_tools = len(self._tools)
        enabled_tools = sum(1 for enabled in self._enabled_tools.values() if enabled)
        
        return {
            'total_tools': total_tools,
            'enabled_tools': enabled_tools,
            'disabled_tools': total_tools - enabled_tools,
            'categories': len(self._categories),
            'category_breakdown': {
                category: len(tool_names) 
                for category, tool_names in self._categories.items()
            }
        }
    
    #----------------------------------------------------------------
    # ESECUZIONE TOOL TRAMITE REGISTRY
    #----------------------------------------------------------------
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name with given parameters.
        
        Args:
            tool_name (str): Name of the tool to execute
            parameters (Dict[str, Any]): Parameters for tool execution
            
        Returns:
            ToolResult: Result of tool execution
        """
        # Get the tool
        tool = self.get_tool(tool_name)
        if not tool:
            from .mcp_tool import ToolResult, ToolResultStatus
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Tool '{tool_name}' not found or not enabled",
                data=None
            )
        
        # Validate parameters
        if not tool.validate_parameters(parameters):
            from .mcp_tool import ToolResult, ToolResultStatus
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Invalid parameters for tool '{tool_name}'",
                data=parameters
            )
        
        # Execute the tool
        try:
            logging.info(f'[ToolRegistry] Executing tool: {tool_name}')
            result = tool.execute(parameters)
            logging.debug(f'[ToolRegistry] Tool execution completed: {tool_name} -> {result.status.value}')
            return result
            
        except Exception as e:
            logging.error(f'[ToolRegistry] Error executing tool {tool_name}: {e}')
            from .mcp_tool import ToolResult, ToolResultStatus
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Execution error in tool '{tool_name}': {str(e)}",
                data=None
            )
    
    #----------------------------------------------------------------
    # UTILITÀ DEBUGGING E MANUTENZIONE
    #----------------------------------------------------------------
    def validate_all_tools(self) -> Dict[str, bool]:
        """
        Validate all tools and their configurations.
        
        Returns:
            Dict[str, bool]: Dictionary mapping tool names to validation results
        """
        validation_results = {}
        
        for tool_name, tool in self._tools.items():
            try:
                # Test basic tool functionality
                tool_info = tool.get_tool_info()
                schema = tool.parameters_schema
                available = tool.is_available()
                
                # Basic validation checks
                validation_results[tool_name] = (
                    bool(tool_info) and 
                    isinstance(schema, dict) and 
                    isinstance(available, bool)
                )
                
            except Exception as e:
                logging.error(f'[ToolRegistry] Validation failed for tool {tool_name}: {e}')
                validation_results[tool_name] = False
        
        return validation_results
    
    def clear_registry(self) -> None:
        """
        Clear all tools from the registry.
        Warning: This will remove all registered tools!
        """
        logging.warning('[ToolRegistry] Clearing all tools from registry')
        self._tools.clear()
        self._categories.clear()
        self._enabled_tools.clear()
    
    #----------------------------------------------------------------
    # RAPPRESENTAZIONE STRINGA
    #----------------------------------------------------------------
    def __str__(self) -> str:
        """String representation of the registry."""
        stats = self.get_registry_stats()
        return f"ToolRegistry: {stats['enabled_tools']}/{stats['total_tools']} tools enabled, {stats['categories']} categories"
    
    def __repr__(self) -> str:
        """Detailed representation of the registry."""
        return f"ToolRegistry(tools={len(self._tools)}, categories={len(self._categories)})"
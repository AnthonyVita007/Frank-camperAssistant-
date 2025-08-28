"""
MCP Server Module for Frank Camper Assistant.

This module provides the server-side implementation for the MCP protocol,
exposing tools as standardized services that can be consumed by MCP clients.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from .mcp_tool import MCPTool, ToolResult, ToolResultStatus


class MCPServerStatus(Enum):
    """
    Enumeration of possible MCP server statuses.
    """
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class MCPCapability:
    """
    Represents a capability exposed by an MCP server.
    
    Attributes:
        name (str): Capability name
        version (str): Capability version
        description (str): Capability description
        parameters (Dict[str, Any]): Capability parameters
    """
    name: str
    version: str = "1.0"
    description: str = ""
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class MCPServer:
    """
    MCP (Model Context Protocol) Server implementation.
    
    This server exposes registered tools as standardized MCP services,
    handles protocol-compliant communication, and manages tool lifecycle.
    
    Attributes:
        _server_name (str): Unique server name
        _server_description (str): Server description
        _tools (Dict[str, MCPTool]): Registered tools
        _capabilities (List[MCPCapability]): Server capabilities
        _status (MCPServerStatus): Current server status
        _request_handlers (Dict[str, Callable]): MCP request handlers
        _server_id (str): Unique server instance ID
        _start_time (Optional[float]): Server start timestamp
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE SERVER MCP
    #----------------------------------------------------------------
    def __init__(
        self, 
        server_name: str, 
        server_description: str = "",
        capabilities: Optional[List[MCPCapability]] = None
    ) -> None:
        """
        Initialize the MCP server.
        
        Args:
            server_name (str): Unique name for this server
            server_description (str): Description of server's purpose
            capabilities (Optional[List[MCPCapability]]): Server capabilities
        """
        self._server_name = server_name
        self._server_description = server_description
        self._tools: Dict[str, MCPTool] = {}
        self._capabilities = capabilities or []
        self._status = MCPServerStatus.STOPPED
        self._server_id = self._generate_server_id()
        self._start_time: Optional[float] = None
        
        # Setup request handlers
        self._request_handlers: Dict[str, Callable] = {
            'initialize': self._handle_initialize,
            'tools/list': self._handle_tools_list,
            'tools/call': self._handle_tools_call,
            'capabilities': self._handle_capabilities,
            'ping': self._handle_ping
        }
        
        # Add default capabilities
        self._add_default_capabilities()
        
        logging.info(f'[MCPServer] MCP server "{server_name}" initialized with ID: {self._server_id}')
    
    def _generate_server_id(self) -> str:
        """
        Generate a unique server ID.
        
        Returns:
            str: Unique server identifier
        """
        return f"mcp-server-{uuid.uuid4().hex[:8]}"
    
    def _add_default_capabilities(self) -> None:
        """
        Add default MCP capabilities supported by this server.
        """
        default_capabilities = [
            MCPCapability(
                name="tools",
                version="1.0",
                description="Tool discovery and execution",
                parameters={"supports_streaming": False}
            ),
            MCPCapability(
                name="logging",
                version="1.0", 
                description="Request logging and monitoring"
            )
        ]
        
        for capability in default_capabilities:
            if capability.name not in [c.name for c in self._capabilities]:
                self._capabilities.append(capability)
    
    #----------------------------------------------------------------
    # REGISTRAZIONE E GESTIONE TOOL
    #----------------------------------------------------------------
    def register_tool(self, tool: MCPTool) -> bool:
        """
        Register a tool with the MCP server.
        
        Args:
            tool (MCPTool): The tool to register
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            if not isinstance(tool, MCPTool):
                logging.error(f'[MCPServer] Invalid tool type: {type(tool)}')
                return False
            
            tool_name = tool.name
            
            # Check for name conflicts
            if tool_name in self._tools:
                logging.warning(f'[MCPServer] Tool already registered: {tool_name}')
                return False
            
            # Validate tool before registration
            if not self._validate_tool(tool):
                logging.error(f'[MCPServer] Tool validation failed: {tool_name}')
                return False
            
            # Register the tool
            self._tools[tool_name] = tool
            
            logging.info(f'[MCPServer] Registered tool: {tool_name} ({tool.category})')
            return True
            
        except Exception as e:
            logging.error(f'[MCPServer] Error registering tool: {e}')
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool from the MCP server.
        
        Args:
            tool_name (str): Name of the tool to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        try:
            if tool_name not in self._tools:
                logging.warning(f'[MCPServer] Tool not found for unregistration: {tool_name}')
                return False
            
            # Remove the tool
            del self._tools[tool_name]
            
            logging.info(f'[MCPServer] Unregistered tool: {tool_name}')
            return True
            
        except Exception as e:
            logging.error(f'[MCPServer] Error unregistering tool: {e}')
            return False
    
    def _validate_tool(self, tool: MCPTool) -> bool:
        """
        Validate a tool before registration.
        
        Args:
            tool (MCPTool): Tool to validate
            
        Returns:
            bool: True if tool is valid, False otherwise
        """
        try:
            # Check basic attributes
            if not tool.name or not tool.description:
                logging.error('[MCPServer] Tool missing required name or description')
                return False
            
            # Check if tool has valid schema
            schema = tool.parameters_schema
            if not isinstance(schema, dict):
                logging.error(f'[MCPServer] Tool {tool.name} has invalid parameters schema')
                return False
            
            # Check if tool is available
            if not tool.is_available():
                logging.warning(f'[MCPServer] Tool {tool.name} is not available')
                # Continue anyway - tool might become available later
            
            return True
            
        except Exception as e:
            logging.error(f'[MCPServer] Error validating tool: {e}')
            return False
    
    #----------------------------------------------------------------
    # AVVIO E ARRESTO SERVER
    #----------------------------------------------------------------
    def start_server(self) -> bool:
        """
        Start the MCP server.
        
        Returns:
            bool: True if server started successfully, False otherwise
        """
        try:
            if self._status == MCPServerStatus.RUNNING:
                logging.warning('[MCPServer] Server is already running')
                return True
            
            logging.info(f'[MCPServer] Starting MCP server: {self._server_name}')
            self._status = MCPServerStatus.STARTING
            
            # Perform startup checks
            if not self._perform_startup_checks():
                self._status = MCPServerStatus.ERROR
                return False
            
            # Start server
            self._start_time = time.time()
            self._status = MCPServerStatus.RUNNING
            
            logging.info(f'[MCPServer] MCP server "{self._server_name}" started successfully')
            return True
            
        except Exception as e:
            logging.error(f'[MCPServer] Error starting server: {e}')
            self._status = MCPServerStatus.ERROR
            return False
    
    def stop_server(self) -> bool:
        """
        Stop the MCP server.
        
        Returns:
            bool: True if server stopped successfully, False otherwise
        """
        try:
            if self._status == MCPServerStatus.STOPPED:
                logging.warning('[MCPServer] Server is already stopped')
                return True
            
            logging.info(f'[MCPServer] Stopping MCP server: {self._server_name}')
            self._status = MCPServerStatus.STOPPING
            
            # Perform cleanup
            self._perform_cleanup()
            
            # Stop server
            self._status = MCPServerStatus.STOPPED
            self._start_time = None
            
            logging.info(f'[MCPServer] MCP server "{self._server_name}" stopped successfully')
            return True
            
        except Exception as e:
            logging.error(f'[MCPServer] Error stopping server: {e}')
            self._status = MCPServerStatus.ERROR
            return False
    
    def _perform_startup_checks(self) -> bool:
        """
        Perform startup validation checks.
        
        Returns:
            bool: True if all checks pass, False otherwise
        """
        try:
            # Check if at least one tool is registered
            if not self._tools:
                logging.warning('[MCPServer] No tools registered - server will start but have limited functionality')
            
            # Validate all registered tools
            invalid_tools = []
            for tool_name, tool in self._tools.items():
                if not self._validate_tool(tool):
                    invalid_tools.append(tool_name)
            
            if invalid_tools:
                logging.warning(f'[MCPServer] Some tools failed validation: {invalid_tools}')
                # Continue anyway - tools might become available later
            
            return True
            
        except Exception as e:
            logging.error(f'[MCPServer] Startup checks failed: {e}')
            return False
    
    def _perform_cleanup(self) -> None:
        """
        Perform cleanup operations during server shutdown.
        """
        try:
            # No specific cleanup needed for tools in current implementation
            # but this method is here for future extensibility
            logging.debug('[MCPServer] Cleanup operations completed')
            
        except Exception as e:
            logging.error(f'[MCPServer] Error during cleanup: {e}')
    
    #----------------------------------------------------------------
    # GESTIONE RICHIESTE MCP
    #----------------------------------------------------------------
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request and return a structured response.
        
        Args:
            request (Dict[str, Any]): The MCP request
            
        Returns:
            Dict[str, Any]: The MCP response
        """
        try:
            # Validate basic request structure
            if not isinstance(request, dict):
                return self._create_error_response("Invalid request format", "INVALID_REQUEST")
            
            # Extract request components
            method = request.get('method')
            params = request.get('params', {})
            request_id = request.get('id')
            
            if not method:
                return self._create_error_response("Missing request method", "MISSING_METHOD", request_id)
            
            logging.debug(f'[MCPServer] Handling request: {method}')
            
            # Check server status
            if self._status != MCPServerStatus.RUNNING:
                return self._create_error_response(
                    f"Server not available (status: {self._status.value})", 
                    "SERVER_UNAVAILABLE", 
                    request_id
                )
            
            # Route to appropriate handler
            handler = self._request_handlers.get(method)
            if not handler:
                return self._create_error_response(
                    f"Unsupported method: {method}", 
                    "METHOD_NOT_FOUND", 
                    request_id
                )
            
            # Execute handler
            result = handler(params)
            
            # Create success response
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
            logging.debug(f'[MCPServer] Request handled successfully: {method}')
            return response
            
        except Exception as e:
            logging.error(f'[MCPServer] Error handling request: {e}')
            return self._create_error_response(
                f"Internal server error: {str(e)}", 
                "INTERNAL_ERROR", 
                request.get('id') if isinstance(request, dict) else None
            )
    
    def _create_error_response(
        self, 
        message: str, 
        code: str, 
        request_id: Any = None
    ) -> Dict[str, Any]:
        """
        Create a standard MCP error response.
        
        Args:
            message (str): Error message
            code (str): Error code
            request_id (Any): Request ID if available
            
        Returns:
            Dict[str, Any]: MCP error response
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
                "data": {
                    "server_id": self._server_id,
                    "server_name": self._server_name,
                    "timestamp": time.time()
                }
            }
        }
    
    #----------------------------------------------------------------
    # HANDLER SPECIFICI PER RICHIESTE MCP
    #----------------------------------------------------------------
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP initialize request.
        
        Args:
            params (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Initialization response
        """
        return {
            "protocolVersion": "1.0",
            "capabilities": [asdict(cap) for cap in self._capabilities],
            "serverInfo": {
                "name": self._server_name,
                "version": "1.0",
                "description": self._server_description,
                "server_id": self._server_id
            }
        }
    
    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tools list request.
        
        Args:
            params (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Tools list response
        """
        tools = []
        
        for tool_name, tool in self._tools.items():
            if tool.is_available():
                tool_info = {
                    "name": tool_name,
                    "description": tool.description,
                    "category": tool.category,
                    "inputSchema": tool.parameters_schema,
                    "requires_confirmation": tool.requires_confirmation
                }
                tools.append(tool_info)
        
        return {
            "tools": tools,
            "server_info": {
                "name": self._server_name,
                "total_tools": len(self._tools),
                "available_tools": len(tools)
            }
        }
    
    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tool call request.
        
        Args:
            params (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Tool execution response
        """
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self._tools[tool_name]
        
        if not tool.is_available():
            raise ValueError(f"Tool not available: {tool_name}")
        
        # Validate parameters
        if not tool.validate_parameters(arguments):
            raise ValueError(f"Invalid parameters for tool: {tool_name}")
        
        # Execute tool
        logging.info(f'[MCPServer] Executing tool: {tool_name}')
        result = tool.execute(arguments)
        
        # Convert ToolResult to MCP response format
        return {
            "content": [
                {
                    "type": "text",
                    "text": result.data if isinstance(result.data, str) else str(result.data)
                }
            ],
            "isError": result.status == ToolResultStatus.ERROR,
            "metadata": {
                "tool_name": tool_name,
                "status": result.status.value,
                "message": result.message,
                "requires_action": result.requires_action,
                "confirmation_message": result.confirmation_message,
                "tool_metadata": result.metadata or {}
            }
        }
    
    def _handle_capabilities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle capabilities request.
        
        Args:
            params (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Capabilities response
        """
        return {
            "capabilities": [asdict(cap) for cap in self._capabilities],
            "server_info": {
                "name": self._server_name,
                "description": self._server_description,
                "server_id": self._server_id,
                "status": self._status.value,
                "uptime": time.time() - self._start_time if self._start_time else 0
            }
        }
    
    def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle ping request for health checking.
        
        Args:
            params (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Ping response
        """
        return {
            "pong": True,
            "timestamp": time.time(),
            "server_id": self._server_id,
            "status": self._status.value,
            "tools_count": len(self._tools),
            "available_tools_count": len([t for t in self._tools.values() if t.is_available()])
        }
    
    #----------------------------------------------------------------
    # INFORMAZIONI E STATISTICHE SERVER
    #----------------------------------------------------------------
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get comprehensive server information.
        
        Returns:
            Dict[str, Any]: Server information
        """
        return {
            "server_id": self._server_id,
            "name": self._server_name,
            "description": self._server_description,
            "status": self._status.value,
            "start_time": self._start_time,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "capabilities": [asdict(cap) for cap in self._capabilities],
            "tools": {
                "total": len(self._tools),
                "available": len([t for t in self._tools.values() if t.is_available()]),
                "categories": list(set(tool.category for tool in self._tools.values()))
            }
        }
    
    def get_server_status(self) -> MCPServerStatus:
        """
        Get the current server status.
        
        Returns:
            MCPServerStatus: Current status
        """
        return self._status
    
    def is_running(self) -> bool:
        """
        Check if the server is currently running.
        
        Returns:
            bool: True if server is running, False otherwise
        """
        return self._status == MCPServerStatus.RUNNING
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """
        Get a list of all registered tools with their information.
        
        Returns:
            List[Dict[str, Any]]: List of tool information
        """
        tools = []
        
        for tool_name, tool in self._tools.items():
            tool_info = tool.get_tool_info()
            tool_info["registered_name"] = tool_name
            tools.append(tool_info)
        
        return tools
    
    #----------------------------------------------------------------
    # HEALTH CHECK E DIAGNOSTICHE
    #----------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the server.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        health_status = {
            "server_healthy": True,
            "status": self._status.value,
            "checks": {},
            "timestamp": time.time()
        }
        
        try:
            # Check server status
            health_status["checks"]["server_status"] = {
                "healthy": self._status == MCPServerStatus.RUNNING,
                "current_status": self._status.value
            }
            
            # Check tools
            tool_health = {
                "total_tools": len(self._tools),
                "available_tools": 0,
                "unavailable_tools": 0,
                "tool_details": {}
            }
            
            for tool_name, tool in self._tools.items():
                is_available = tool.is_available()
                if is_available:
                    tool_health["available_tools"] += 1
                else:
                    tool_health["unavailable_tools"] += 1
                
                tool_health["tool_details"][tool_name] = {
                    "available": is_available,
                    "category": tool.category
                }
            
            health_status["checks"]["tools"] = tool_health
            
            # Overall health determination
            if (self._status != MCPServerStatus.RUNNING or 
                tool_health["available_tools"] == 0):
                health_status["server_healthy"] = False
            
        except Exception as e:
            logging.error(f'[MCPServer] Error during health check: {e}')
            health_status["server_healthy"] = False
            health_status["error"] = str(e)
        
        return health_status
    
    #----------------------------------------------------------------
    # RAPPRESENTAZIONE STRINGA
    #----------------------------------------------------------------
    def __str__(self) -> str:
        """String representation of the MCP server."""
        return f'MCPServer[{self._server_name}]: {self._status.value}, {len(self._tools)} tools'
    
    def __repr__(self) -> str:
        """Detailed representation of the MCP server."""
        return f'MCPServer(name="{self._server_name}", id="{self._server_id}", status="{self._status.value}")'
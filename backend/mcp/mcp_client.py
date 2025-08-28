"""
MCP Client Module for Frank Camper Assistant.

This module provides the client-side implementation for the MCP protocol,
handling communication with MCP servers and tool orchestration.
"""

#----------------------------------------------------------------
# IMPORT E TIPOLOGIE BASE
#----------------------------------------------------------------
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import time

from .mcp_tool import MCPTool, ToolResult, ToolResultStatus


class MCPProtocolVersion(Enum):
    """
    Supported MCP protocol versions.
    """
    V1_0 = "1.0"
    V1_1 = "1.1"


@dataclass
class MCPServerInfo:
    """
    Information about an MCP server connection.
    
    Attributes:
        name (str): Server name
        url (str): Server URL or connection string
        protocol_version (MCPProtocolVersion): Protocol version
        capabilities (List[str]): Server capabilities
        is_connected (bool): Connection status
        last_ping (float): Last ping timestamp
    """
    name: str
    url: str
    protocol_version: MCPProtocolVersion = MCPProtocolVersion.V1_0
    capabilities: List[str] = None
    is_connected: bool = False
    last_ping: float = 0.0
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class MCPClient:
    """
    MCP (Model Context Protocol) Client implementation.
    
    This client manages connections to MCP servers, handles tool discovery,
    parameter marshalling, and coordinates tool execution across multiple servers.
    
    Attributes:
        _servers (Dict[str, MCPServerInfo]): Connected MCP servers
        _tool_mappings (Dict[str, str]): Tool name to server name mapping
        _protocol_version (MCPProtocolVersion): Client protocol version
        _request_timeout (float): Default request timeout
        _max_retries (int): Maximum retry attempts
    """
    
    #----------------------------------------------------------------
    # INIZIALIZZAZIONE CLIENT MCP
    #----------------------------------------------------------------
    def __init__(
        self, 
        protocol_version: MCPProtocolVersion = MCPProtocolVersion.V1_0,
        request_timeout: float = 30.0,
        max_retries: int = 3
    ) -> None:
        """
        Initialize the MCP client.
        
        Args:
            protocol_version (MCPProtocolVersion): Protocol version to use
            request_timeout (float): Default timeout for requests
            max_retries (int): Maximum retry attempts for failed requests
        """
        self._servers: Dict[str, MCPServerInfo] = {}
        self._tool_mappings: Dict[str, str] = {}
        self._protocol_version = protocol_version
        self._request_timeout = request_timeout
        self._max_retries = max_retries
        self._session_id = self._generate_session_id()
        
        logging.info(f'[MCPClient] MCP client initialized with protocol {protocol_version.value}')
        logging.debug(f'[MCPClient] Session ID: {self._session_id}')
    
    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID for this client instance.
        
        Returns:
            str: Unique session identifier
        """
        import uuid
        return f"frank-mcp-{uuid.uuid4().hex[:8]}"
    
    #----------------------------------------------------------------
    # GESTIONE SERVER MCP
    #----------------------------------------------------------------
    def register_server(
        self, 
        server_name: str, 
        server_url: str,
        capabilities: Optional[List[str]] = None
    ) -> bool:
        """
        Register an MCP server with the client.
        
        Args:
            server_name (str): Unique name for the server
            server_url (str): Server URL or connection string
            capabilities (Optional[List[str]]): Server capabilities
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            if server_name in self._servers:
                logging.warning(f'[MCPClient] Server already registered: {server_name}')
                return False
            
            server_info = MCPServerInfo(
                name=server_name,
                url=server_url,
                protocol_version=self._protocol_version,
                capabilities=capabilities or [],
                is_connected=False
            )
            
            self._servers[server_name] = server_info
            logging.info(f'[MCPClient] Registered MCP server: {server_name} at {server_url}')
            
            return True
            
        except Exception as e:
            logging.error(f'[MCPClient] Error registering server {server_name}: {e}')
            return False
    
    def unregister_server(self, server_name: str) -> bool:
        """
        Unregister an MCP server from the client.
        
        Args:
            server_name (str): Name of the server to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        try:
            if server_name not in self._servers:
                logging.warning(f'[MCPClient] Server not found for unregistration: {server_name}')
                return False
            
            # Disconnect if connected
            if self._servers[server_name].is_connected:
                self.disconnect_server(server_name)
            
            # Remove tool mappings for this server
            tools_to_remove = [
                tool_name for tool_name, mapped_server 
                in self._tool_mappings.items() 
                if mapped_server == server_name
            ]
            
            for tool_name in tools_to_remove:
                del self._tool_mappings[tool_name]
            
            # Remove server
            del self._servers[server_name]
            
            logging.info(f'[MCPClient] Unregistered MCP server: {server_name}')
            return True
            
        except Exception as e:
            logging.error(f'[MCPClient] Error unregistering server {server_name}: {e}')
            return False
    
    #----------------------------------------------------------------
    # CONNESSIONE E DISCOVERY
    #----------------------------------------------------------------
    def connect_server(self, server_name: str) -> bool:
        """
        Establish connection to an MCP server.
        
        Args:
            server_name (str): Name of the server to connect to
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            if server_name not in self._servers:
                logging.error(f'[MCPClient] Cannot connect to unregistered server: {server_name}')
                return False
            
            server_info = self._servers[server_name]
            
            if server_info.is_connected:
                logging.debug(f'[MCPClient] Server already connected: {server_name}')
                return True
            
            # Attempt connection (simplified for this implementation)
            # In a real MCP implementation, this would establish actual network connection
            logging.info(f'[MCPClient] Connecting to MCP server: {server_name}')
            
            # Simulate connection process
            connection_successful = self._establish_connection(server_info)
            
            if connection_successful:
                server_info.is_connected = True
                server_info.last_ping = time.time()
                
                # Discover available tools on the server
                self._discover_server_tools(server_name)
                
                logging.info(f'[MCPClient] Successfully connected to server: {server_name}')
                return True
            else:
                logging.error(f'[MCPClient] Failed to connect to server: {server_name}')
                return False
                
        except Exception as e:
            logging.error(f'[MCPClient] Error connecting to server {server_name}: {e}')
            return False
    
    def disconnect_server(self, server_name: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            server_name (str): Name of the server to disconnect from
            
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        try:
            if server_name not in self._servers:
                logging.warning(f'[MCPClient] Cannot disconnect from unregistered server: {server_name}')
                return False
            
            server_info = self._servers[server_name]
            
            if not server_info.is_connected:
                logging.debug(f'[MCPClient] Server already disconnected: {server_name}')
                return True
            
            # Perform disconnection
            server_info.is_connected = False
            server_info.last_ping = 0.0
            
            logging.info(f'[MCPClient] Disconnected from MCP server: {server_name}')
            return True
            
        except Exception as e:
            logging.error(f'[MCPClient] Error disconnecting from server {server_name}: {e}')
            return False
    
    def _establish_connection(self, server_info: MCPServerInfo) -> bool:
        """
        Establish the actual connection to an MCP server.
        
        This is a simplified implementation. In a real MCP client,
        this would handle protocol negotiation, authentication, etc.
        
        Args:
            server_info (MCPServerInfo): Server to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Simplified connection logic
            # In reality, this would involve:
            # 1. Opening network connection (WebSocket, HTTP, etc.)
            # 2. Protocol version negotiation
            # 3. Authentication if required
            # 4. Capability exchange
            
            logging.debug(f'[MCPClient] Establishing connection to {server_info.url}')
            
            # For now, we simulate a successful connection
            # This would be replaced with actual networking code
            time.sleep(0.1)  # Simulate connection delay
            
            return True
            
        except Exception as e:
            logging.error(f'[MCPClient] Failed to establish connection: {e}')
            return False
    
    def _discover_server_tools(self, server_name: str) -> List[str]:
        """
        Discover available tools on a connected MCP server.
        
        Args:
            server_name (str): Name of the server
            
        Returns:
            List[str]: List of discovered tool names
        """
        try:
            logging.debug(f'[MCPClient] Discovering tools on server: {server_name}')
            
            # In a real implementation, this would send a tool discovery request
            # For now, we simulate tool discovery based on server capabilities
            server_info = self._servers[server_name]
            
            # Simulate discovered tools based on server capabilities
            discovered_tools = []
            
            # This is where we would parse the actual MCP tool discovery response
            # For now, we'll simulate some tools based on server name
            if 'navigation' in server_name.lower():
                discovered_tools = ['set_route', 'get_current_location', 'find_poi']
            elif 'weather' in server_name.lower():
                discovered_tools = ['get_weather', 'get_forecast', 'get_weather_alerts']
            elif 'vehicle' in server_name.lower():
                discovered_tools = ['get_vehicle_status', 'get_diagnostics', 'get_fuel_level']
            
            # Update tool mappings
            for tool_name in discovered_tools:
                self._tool_mappings[tool_name] = server_name
            
            logging.info(f'[MCPClient] Discovered {len(discovered_tools)} tools on {server_name}: {discovered_tools}')
            return discovered_tools
            
        except Exception as e:
            logging.error(f'[MCPClient] Error discovering tools on server {server_name}: {e}')
            return []
    
    #----------------------------------------------------------------
    # ESECUZIONE TOOL TRAMITE MCP
    #----------------------------------------------------------------
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool through the MCP protocol.
        
        Args:
            tool_name (str): Name of the tool to execute
            parameters (Dict[str, Any]): Parameters for tool execution
            
        Returns:
            ToolResult: Result of tool execution
        """
        try:
            # Find which server hosts this tool
            server_name = self._tool_mappings.get(tool_name)
            if not server_name:
                logging.error(f'[MCPClient] Tool not found: {tool_name}')
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    message=f"Tool '{tool_name}' not found in any connected server",
                    data=None
                )
            
            # Check if server is connected
            server_info = self._servers.get(server_name)
            if not server_info or not server_info.is_connected:
                logging.error(f'[MCPClient] Server not connected: {server_name}')
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    message=f"Server '{server_name}' is not connected",
                    data=None
                )
            
            logging.info(f'[MCPClient] Executing tool {tool_name} on server {server_name}')
            logging.debug(f'[MCPClient] Tool parameters: {parameters}')
            
            # Execute tool with retry logic
            result = self._execute_tool_with_retry(server_name, tool_name, parameters)
            
            logging.info(f'[MCPClient] Tool execution completed: {tool_name} -> {result.status.value}')
            return result
            
        except Exception as e:
            logging.error(f'[MCPClient] Unexpected error executing tool {tool_name}: {e}')
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Unexpected error executing tool: {str(e)}",
                data=None
            )
    
    def _execute_tool_with_retry(
        self, 
        server_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute tool with retry logic for resilience.
        
        Args:
            server_name (str): Name of the server hosting the tool
            tool_name (str): Name of the tool to execute
            parameters (Dict[str, Any]): Tool parameters
            
        Returns:
            ToolResult: Result of tool execution
        """
        last_error = None
        
        for attempt in range(self._max_retries):
            try:
                logging.debug(f'[MCPClient] Tool execution attempt {attempt + 1}/{self._max_retries}')
                
                # Send MCP request to server
                result = self._send_mcp_request(server_name, tool_name, parameters)
                
                if result.status != ToolResultStatus.ERROR:
                    return result
                
                # If error, log and potentially retry
                last_error = result.message
                if attempt < self._max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logging.warning(f'[MCPClient] Tool execution failed, retrying in {wait_time}s: {last_error}')
                    time.sleep(wait_time)
                
            except Exception as e:
                last_error = str(e)
                logging.error(f'[MCPClient] Error in tool execution attempt {attempt + 1}: {e}')
                
                if attempt < self._max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        # All retries failed
        return ToolResult(
            status=ToolResultStatus.ERROR,
            message=f"Tool execution failed after {self._max_retries} attempts. Last error: {last_error}",
            data=None
        )
    
    def _send_mcp_request(
        self, 
        server_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolResult:
        """
        Send an MCP request to a specific server.
        
        This method handles the actual MCP protocol communication.
        In a real implementation, this would serialize the request
        according to MCP specification and handle the response.
        
        Args:
            server_name (str): Target server name
            tool_name (str): Tool to execute
            parameters (Dict[str, Any]): Tool parameters
            
        Returns:
            ToolResult: Parsed result from MCP response
        """
        try:
            # Create MCP request message
            mcp_request = {
                "jsonrpc": "2.0",
                "id": self._generate_request_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            logging.debug(f'[MCPClient] Sending MCP request: {json.dumps(mcp_request, indent=2)}')
            
            # In a real implementation, this would be sent over the network
            # For now, we simulate the server response
            mcp_response = self._simulate_mcp_server_response(server_name, tool_name, parameters)
            
            # Parse MCP response into ToolResult
            return self._parse_mcp_response(mcp_response)
            
        except Exception as e:
            logging.error(f'[MCPClient] Error sending MCP request: {e}')
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"MCP request failed: {str(e)}",
                data=None
            )
    
    def _generate_request_id(self) -> str:
        """
        Generate a unique request ID for MCP requests.
        
        Returns:
            str: Unique request identifier
        """
        import uuid
        return f"req-{uuid.uuid4().hex[:8]}"
    
    def _simulate_mcp_server_response(
        self, 
        server_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate an MCP server response for testing purposes.
        
        This method will be replaced with actual network communication
        in the real implementation.
        
        Args:
            server_name (str): Server name
            tool_name (str): Tool name
            parameters (Dict[str, Any]): Parameters
            
        Returns:
            Dict[str, Any]: Simulated MCP response
        """
        # Simulate different responses based on tool name
        if tool_name == 'set_route':
            return {
                "jsonrpc": "2.0",
                "id": "req-12345",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Rotta impostata per: {parameters.get('destination', 'destinazione sconosciuta')}"
                        }
                    ]
                }
            }
        elif tool_name == 'get_weather':
            return {
                "jsonrpc": "2.0",
                "id": "req-12345",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Meteo per {parameters.get('location', 'località sconosciuta')}: Soleggiato, 22°C"
                        }
                    ]
                }
            }
        elif tool_name == 'get_vehicle_status':
            return {
                "jsonrpc": "2.0",
                "id": "req-12345",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Stato veicolo: Tutto OK. Carburante: 75%, Pressione pneumatici: Normale"
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": "req-12345",
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }
    
    def _parse_mcp_response(self, mcp_response: Dict[str, Any]) -> ToolResult:
        """
        Parse an MCP response into a ToolResult.
        
        Args:
            mcp_response (Dict[str, Any]): Raw MCP response
            
        Returns:
            ToolResult: Parsed tool result
        """
        try:
            # Check for error in response
            if "error" in mcp_response:
                error_info = mcp_response["error"]
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    message=error_info.get("message", "Unknown MCP error"),
                    data=error_info
                )
            
            # Parse successful response
            if "result" in mcp_response:
                result_data = mcp_response["result"]
                
                # Extract text content from MCP response
                text_content = ""
                if "content" in result_data:
                    for content_item in result_data["content"]:
                        if content_item.get("type") == "text":
                            text_content += content_item.get("text", "")
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    message="Tool executed successfully via MCP",
                    data=text_content,
                    metadata={
                        "mcp_response": result_data,
                        "protocol_version": self._protocol_version.value
                    }
                )
            
            # Unexpected response format
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message="Unexpected MCP response format",
                data=mcp_response
            )
            
        except Exception as e:
            logging.error(f'[MCPClient] Error parsing MCP response: {e}')
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Failed to parse MCP response: {str(e)}",
                data=mcp_response
            )
    
    #----------------------------------------------------------------
    # QUERY E INFORMAZIONI SISTEMA
    #----------------------------------------------------------------
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get information about all available tools across connected servers.
        
        Returns:
            List[Dict[str, Any]]: List of tool information
        """
        tools_info = []
        
        for tool_name, server_name in self._tool_mappings.items():
            server_info = self._servers.get(server_name)
            if server_info and server_info.is_connected:
                tools_info.append({
                    'name': tool_name,
                    'server': server_name,
                    'server_url': server_info.url,
                    'protocol_version': server_info.protocol_version.value,
                    'capabilities': server_info.capabilities
                })
        
        return tools_info
    
    def get_connected_servers(self) -> List[Dict[str, Any]]:
        """
        Get information about connected servers.
        
        Returns:
            List[Dict[str, Any]]: List of connected server information
        """
        connected_servers = []
        
        for server_name, server_info in self._servers.items():
            if server_info.is_connected:
                connected_servers.append({
                    'name': server_name,
                    'url': server_info.url,
                    'protocol_version': server_info.protocol_version.value,
                    'capabilities': server_info.capabilities,
                    'last_ping': server_info.last_ping,
                    'tools_count': len([t for t, s in self._tool_mappings.items() if s == server_name])
                })
        
        return connected_servers
    
    def get_client_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the MCP client.
        
        Returns:
            Dict[str, Any]: Client status information
        """
        return {
            'session_id': self._session_id,
            'protocol_version': self._protocol_version.value,
            'total_servers': len(self._servers),
            'connected_servers': len([s for s in self._servers.values() if s.is_connected]),
            'total_tools': len(self._tool_mappings),
            'request_timeout': self._request_timeout,
            'max_retries': self._max_retries,
            'servers': [
                {
                    'name': name,
                    'connected': info.is_connected,
                    'url': info.url
                }
                for name, info in self._servers.items()
            ]
        }
    
    #----------------------------------------------------------------
    # HEALTH CHECK E MANUTENZIONE
    #----------------------------------------------------------------
    def ping_all_servers(self) -> Dict[str, bool]:
        """
        Ping all connected servers to check their health.
        
        Returns:
            Dict[str, bool]: Server name to ping result mapping
        """
        ping_results = {}
        
        for server_name, server_info in self._servers.items():
            if server_info.is_connected:
                try:
                    # Simulate ping - in real implementation would send actual ping
                    ping_successful = True  # Simplified
                    
                    if ping_successful:
                        server_info.last_ping = time.time()
                        ping_results[server_name] = True
                    else:
                        ping_results[server_name] = False
                        logging.warning(f'[MCPClient] Ping failed for server: {server_name}')
                        
                except Exception as e:
                    ping_results[server_name] = False
                    logging.error(f'[MCPClient] Error pinging server {server_name}: {e}')
            else:
                ping_results[server_name] = False
        
        return ping_results
    
    def shutdown(self) -> None:
        """
        Shutdown the MCP client and disconnect from all servers.
        """
        try:
            logging.info('[MCPClient] Shutting down MCP client')
            
            # Disconnect from all servers
            for server_name in list(self._servers.keys()):
                self.disconnect_server(server_name)
            
            # Clear all mappings
            self._servers.clear()
            self._tool_mappings.clear()
            
            logging.info('[MCPClient] MCP client shutdown completed')
            
        except Exception as e:
            logging.error(f'[MCPClient] Error during MCP client shutdown: {e}')
    
    #----------------------------------------------------------------
    # RAPPRESENTAZIONE STRINGA
    #----------------------------------------------------------------
    def __str__(self) -> str:
        """String representation of the MCP client."""
        connected_count = len([s for s in self._servers.values() if s.is_connected])
        total_count = len(self._servers)
        tools_count = len(self._tool_mappings)
        
        return f"MCPClient[{self._protocol_version.value}]: {connected_count}/{total_count} servers connected, {tools_count} tools available"
    
    def __repr__(self) -> str:
        """Detailed representation of the MCP client."""
        return f"MCPClient(session_id='{self._session_id}', protocol='{self._protocol_version.value}', servers={len(self._servers)})"
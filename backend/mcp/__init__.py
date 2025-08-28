"""
MCP (Model Context Protocol) Module for Frank Camper Assistant.

This module implements the MCP architecture for tool-based interactions,
allowing the AI system to execute concrete actions through structured protocols.
"""

from .mcp_client import MCPClient
from .mcp_server import MCPServer
from .mcp_tool import MCPTool
from .tool_registry import ToolRegistry
from .mcp_handler import MCPHandler

__all__ = ['MCPClient', 'MCPServer', 'MCPTool', 'ToolRegistry', 'MCPHandler']
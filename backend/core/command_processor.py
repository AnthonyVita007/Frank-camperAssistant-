"""
Command Processor Module for Frank Camper Assistant.

This module handles the processing of user commands, specifically the three
allowed commands: /clear, /debugmode, and /usermode.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum


class CommandType(Enum):
    """
    Enumeration of supported command types.
    
    This enum defines the three commands that the system supports:
    - CLEAR: Clear the console/log
    - DEBUG_MODE: Switch to debug mode  
    - USER_MODE: Switch to user mode
    - UNKNOWN: Any command not recognized
    """
    CLEAR = "clear"
    DEBUG_MODE = "debugmode" 
    USER_MODE = "usermode"
    UNKNOWN = "unknown"


class CommandResult:
    """
    Represents the result of processing a command.
    
    This class encapsulates the outcome of command processing,
    including the action to take and any associated data.
    
    Attributes:
        action (str): The action to perform (e.g., 'clear_log', 'navigate')
        data (str): Additional data for the action
        success (bool): Whether the command was processed successfully
        message (str): Human-readable message about the result
    """
    
    def __init__(self, action: str, data: str, success: bool = True, message: str = "") -> None:
        """
        Initialize a CommandResult.
        
        Args:
            action (str): The action to perform
            data (str): Additional data for the action
            success (bool): Whether the command was successful (default: True)
            message (str): Human-readable message (default: "")
        """
        self.action = action
        self.data = data
        self.success = success
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the CommandResult to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the result
        """
        return {
            'action': self.action,
            'data': self.data,
            'success': self.success,
            'message': self.message
        }


class CommandProcessor:
    """
    Processes user commands and determines appropriate actions.
    
    This class is responsible for parsing user input and determining
    what action should be taken based on the command received.
    Only handles the three allowed commands: /clear, /debugmode, /usermode.
    """
    
    def __init__(self) -> None:
        """Initialize the CommandProcessor."""
        logging.debug('[CommandProcessor] Command processor initialized')
    
    def process_command(self, command: str) -> Tuple[CommandResult, bool]:
        """
        Process a user command and return the appropriate result.
        
        Args:
            command (str): The command string received from the user
            
        Returns:
            Tuple[CommandResult, bool]: A tuple containing:
                - CommandResult: The result of processing the command
                - bool: True if this was a recognized command, False otherwise
        """
        if not command or not isinstance(command, str):
            logging.warning('[CommandProcessor] Received empty or invalid command')
            return self._create_unknown_command_result(), False
        
        # Clean and normalize the command
        normalized_command = command.strip().lower()
        command_type = self._identify_command(normalized_command)
        
        logging.info(f'[CommandProcessor] Processing command: "{command}" (type: {command_type.value})')
        
        # Process based on command type
        if command_type == CommandType.CLEAR:
            return self._process_clear_command(), True
        elif command_type == CommandType.DEBUG_MODE:
            return self._process_debug_mode_command(), True
        elif command_type == CommandType.USER_MODE:
            return self._process_user_mode_command(), True
        else:
            return self._create_unknown_command_result(), False
    
    def _identify_command(self, command: str) -> CommandType:
        """
        Identify the type of command from the input string.
        
        Args:
            command (str): The normalized command string
            
        Returns:
            CommandType: The identified command type
        """
        if command.startswith('/clear'):
            return CommandType.CLEAR
        elif command.startswith('/debugmode'):
            return CommandType.DEBUG_MODE
        elif command.startswith('/usermode'):
            return CommandType.USER_MODE
        else:
            return CommandType.UNKNOWN
    
    def _process_clear_command(self) -> CommandResult:
        """
        Process the /clear command.
        
        Returns:
            CommandResult: Result indicating the log should be cleared
        """
        logging.debug('[CommandProcessor] Processing clear command')
        return CommandResult(
            action='clear_log',
            data='Console pulita su richiesta.',
            success=True,
            message='Log cleared successfully'
        )
    
    def _process_debug_mode_command(self) -> CommandResult:
        """
        Process the /debugmode command.
        
        Returns:
            CommandResult: Result indicating navigation to debug mode
        """
        logging.debug('[CommandProcessor] Processing debug mode command')
        return CommandResult(
            action='navigate',
            data='/debug',
            success=True,
            message='Navigating to debug mode'
        )
    
    def _process_user_mode_command(self) -> CommandResult:
        """
        Process the /usermode command.
        
        Returns:
            CommandResult: Result indicating navigation to user mode
        """
        logging.debug('[CommandProcessor] Processing user mode command')
        return CommandResult(
            action='navigate',
            data='/user',
            success=True,
            message='Navigating to user mode'
        )
    
    def _create_unknown_command_result(self) -> CommandResult:
        """
        Create a result for unknown commands.
        
        Returns:
            CommandResult: Result indicating the command was not recognized
        """
        return CommandResult(
            action='error',
            data='Comando non riconosciuto. Comandi disponibili: /clear, /debugmode, /usermode',
            success=False,
            message='Unknown command'
        )
    
    def get_available_commands(self) -> Dict[str, str]:
        """
        Get a dictionary of available commands and their descriptions.
        
        Returns:
            Dict[str, str]: Dictionary mapping command names to descriptions
        """
        return {
            '/clear': 'Pulisce la console/log',
            '/debugmode': 'Passa alla modalità debug',
            '/usermode': 'Passa alla modalità utente'
        }
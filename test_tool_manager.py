"""
Test module for ToolLifecycleManager.

This module provides isolated testing for the ToolLifecycleManager class
using mocks for input() and Gemini API calls.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the root directory to path to import our modules
sys.path.insert(0, os.path.dirname(__file__))

from tool_lifecycle_manager import ToolLifecycleManager

class TestToolLifecycleManager(unittest.TestCase):
    """Test cases for ToolLifecycleManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = None
    
    def tearDown(self):
        """Clean up after tests."""
        if self.manager:
            self.manager = None
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    def test_manager_initialization(self, mock_model):
        """Test ToolLifecycleManager initialization."""
        # Setup
        function_name = "get_weather_sample"
        initial_args = {"forecast": "soleggiato"}
        
        # Execute
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Verify
        self.assertEqual(manager.function_name, function_name)
        self.assertEqual(manager.initial_args, initial_args)
        self.assertIn(function_name, manager.tool_schemas)
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    @patch('builtins.input', side_effect=['Roma'])
    @patch('builtins.print')
    def test_parameter_collection_success(self, mock_print, mock_input, mock_model):
        """Test successful parameter collection."""
        # Setup
        mock_model_instance = MagicMock()
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        function_name = "get_weather_sample"
        initial_args = {"forecast": "soleggiato"}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['name'], function_name)
        self.assertIn('Roma', result['response'])
        
        # Verify that input was called for location
        mock_input.assert_called_once()
        
        # Verify that the question was printed
        mock_print.assert_called()
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    @patch('builtins.input', side_effect=['annulla'])
    @patch('builtins.print')
    def test_parameter_collection_cancellation(self, mock_print, mock_input, mock_model):
        """Test parameter collection cancellation."""
        # Setup
        mock_model_instance = MagicMock()
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        function_name = "get_weather_sample"
        initial_args = {}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'cancelled')
        
        # Verify that input was called
        mock_input.assert_called_once()
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    def test_immediate_execution_no_missing_params(self, mock_model):
        """Test immediate execution when no parameters are missing."""
        # Setup
        mock_model_instance = MagicMock()
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        function_name = "get_weather_sample"
        initial_args = {"location": "Milano"}  # All required params present
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['name'], function_name)
        self.assertIn('Milano', result['response'])
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    @patch('builtins.input', side_effect=['', 'Roma'])  # Empty input first, then valid input
    @patch('builtins.print')
    def test_parameter_collection_with_retry(self, mock_print, mock_input, mock_model):
        """Test parameter collection with retry for empty input."""
        # Setup
        mock_model_instance = MagicMock()
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        function_name = "get_weather_sample"
        initial_args = {}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['name'], function_name)
        self.assertIn('Roma', result['response'])
        
        # Verify that input was called twice (empty input + valid input)
        self.assertEqual(mock_input.call_count, 2)
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', False)
    def test_gemini_not_available(self):
        """Test behavior when Gemini API is not available."""
        # Setup
        function_name = "get_weather_sample"
        initial_args = {}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'error')
        self.assertIn('Gemini API not available', result['error'])
    
    def test_unknown_function(self):
        """Test behavior with unknown function name."""
        # Setup
        function_name = "unknown_function"
        initial_args = {}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager._execute_tool()
        
        # Verify
        self.assertEqual(result['status'], 'error')
        self.assertIn('Unknown function', result['error'])
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    @patch('builtins.input', side_effect=['Milano'])
    @patch('builtins.print')
    def test_navigation_tool(self, mock_print, mock_input, mock_model):
        """Test navigation tool parameter collection."""
        # Setup
        mock_model_instance = MagicMock()
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        function_name = "set_route_sample"
        initial_args = {}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['name'], function_name)
        self.assertIn('Milano', result['response'])
        
        # Verify that input was called for destination
        mock_input.assert_called_once()
    
    @patch('tool_lifecycle_manager.GEMINI_AVAILABLE', True)
    @patch('tool_lifecycle_manager.genai.GenerativeModel')
    def test_vehicle_status_tool_no_required_params(self, mock_model):
        """Test vehicle status tool which has no required parameters."""
        # Setup
        mock_model_instance = MagicMock()
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        function_name = "get_vehicle_status_sample"
        initial_args = {}
        
        manager = ToolLifecycleManager(function_name, initial_args)
        
        # Execute
        result = manager.run()
        
        # Verify
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['name'], function_name)
        self.assertIn('Stato veicolo', result['response'])

def run_isolated_tests():
    """Run the tests in isolation."""
    print("Running ToolLifecycleManager isolated tests...")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestToolLifecycleManager)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_isolated_tests()
    exit(0 if success else 1)
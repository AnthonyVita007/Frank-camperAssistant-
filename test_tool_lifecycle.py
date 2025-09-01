#!/usr/bin/env python3
"""
Test script for the rigorous tool lifecycle management system.
Validates the conversation scenarios described in the problem statement.
"""

import sys
import os
import time
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ai.ai_handler import AIHandler, ToolSessionState
from backend.mcp.mcp_handler import MCPHandler
from backend.mcp.tool_registry import ToolRegistry

class MockAIProcessor:
    """Mock AI processor for testing"""
    def is_available(self):
        return True

class MockTool:
    """Mock tool for testing"""
    def __init__(self, name, category, required_params=None):
        self.name = name
        self.category = category
        self.required = required_params or []
        
    def get_tool_info(self):
        return {
            'name': self.name,
            'category': self.category,
            'parameters_schema': {
                'required': self.required
            }
        }
    
    def execute(self, parameters):
        from backend.mcp.mcp_tool import ToolResult, ToolResultStatus
        if self.name == 'set_route_sample':
            return ToolResult(True, f"Rotta impostata per: {parameters.get('destination', 'unknown')}", ToolResultStatus.SUCCESS)
        elif self.name == 'get_weather_sample':
            return ToolResult(True, f"Meteo per {parameters.get('location', 'unknown')}: Soleggiato", ToolResultStatus.SUCCESS)
        elif self.name == 'get_vehicle_status_sample':
            return ToolResult(True, "Veicolo in buone condizioni", ToolResultStatus.SUCCESS)
        return ToolResult(False, "Tool not implemented", ToolResultStatus.ERROR)

class TestToolLifecycle:
    def __init__(self):
        self.events_emitted = []
        self.setup_test_environment()
    
    def event_emitter(self, action: str, data: dict):
        """Capture emitted events for testing"""
        self.events_emitted.append({'action': action, 'data': data})
        print(f"[EVENT] {action}: {data}")
    
    def setup_test_environment(self):
        """Setup test environment with mock components"""
        # Setup MCP system
        self.tool_registry = ToolRegistry()
        self.mcp_handler = MCPHandler(self.tool_registry)
        
        # Register mock tools directly to the handler's internal registry
        # This bypasses the validation but allows testing
        nav_tool_info = {
            'name': 'set_route_sample',
            'category': 'navigation',
            'parameters_schema': {
                'required': ['destination']
            }
        }
        
        weather_tool_info = {
            'name': 'get_weather_sample',
            'category': 'weather',
            'parameters_schema': {
                'required': ['location']
            }
        }
        
        vehicle_tool_info = {
            'name': 'get_vehicle_status_sample',
            'category': 'vehicle',
            'parameters_schema': {
                'required': []
            }
        }
        
        # Directly inject tools for testing
        self.mcp_handler._tool_registry._tools = {
            'set_route_sample': nav_tool_info,
            'get_weather_sample': weather_tool_info,
            'get_vehicle_status_sample': vehicle_tool_info
        }
        
        # Mock execute_tool method
        def mock_execute_tool(name, parameters):
            from backend.mcp.mcp_tool import ToolResult, ToolResultStatus
            if name == 'set_route_sample':
                return ToolResult(True, f"Rotta impostata per: {parameters.get('destination', 'unknown')}", ToolResultStatus.SUCCESS)
            elif name == 'get_weather_sample':
                return ToolResult(True, f"Meteo per {parameters.get('location', 'unknown')}: Soleggiato", ToolResultStatus.SUCCESS)
            elif name == 'get_vehicle_status_sample':
                return ToolResult(True, "Veicolo in buone condizioni", ToolResultStatus.SUCCESS)
            return ToolResult(False, "Tool not implemented", ToolResultStatus.ERROR)
        
        self.mcp_handler.execute_tool = mock_execute_tool
        
        # Setup AI handler with event emitter
        self.ai_handler = AIHandler(
            ai_processor=MockAIProcessor(),
            mcp_handler=self.mcp_handler,
            event_emitter=self.event_emitter
        )
        
        available_tools = self.mcp_handler.get_available_tools()
        print(f"[SETUP] MCP tools available: {[t.get('name') for t in available_tools]}")
    
    def test_conversation_a_navigation_scenario(self):
        """Test Conversation A: Navigation tool with missing destination parameter"""
        print("\n" + "="*60)
        print("TESTING CONVERSATION A: Navigation Tool (Missing Destination)")
        print("="*60)
        
        self.events_emitted = []
        session_id = "test_session_a"
        
        # Step 1: User says "Imposta la rotta"
        print("\n[USER] Imposta la rotta")
        
        # Simulate tool detection and handling
        tool_intent = {
            'primary_category': 'navigation',
            'confidence': 0.9,
            'detection_method': 'pattern'
        }
        
        context = {'session_id': session_id}
        
        # Mock parameter extraction to return empty parameters (missing destination)
        original_extract = self.ai_handler._extract_tool_parameters
        def mock_extract_empty(*args, **kwargs):
            return {}
        
        self.ai_handler._extract_tool_parameters = mock_extract_empty
        
        response = self.ai_handler._handle_tool_request("Imposta la rotta", tool_intent, context)
        
        print(f"[FRANK] {response.text}")
        
        # Verify session was created and events emitted
        assert self.ai_handler.is_tool_session_active(session_id), "Tool session should be active"
        assert any(e['action'] == 'tool_lifecycle_started' for e in self.events_emitted), "Should emit tool_lifecycle_started"
        assert any(e['action'] == 'tool_selected' for e in self.events_emitted), "Should emit tool_selected"
        assert any(e['action'] == 'tool_clarification' for e in self.events_emitted), "Should emit tool_clarification"
        
        # Step 2: User asks something else - should get gating notice
        print("\n[USER] Come stai?")
        response = self.ai_handler.continue_tool_clarification(session_id, "Come stai?")
        print(f"[FRANK] {response.text}")
        
        # Verify gating notice was emitted
        assert any(e['action'] == 'tool_gating_notice' for e in self.events_emitted), "Should emit tool_gating_notice"
        assert "Modalità Tool attiva" in response.text, "Should mention tool mode is active"
        
        # Step 3: User provides destination
        print("\n[USER] Roma")
        
        # Mock parameter extraction to return destination
        def mock_extract_destination(*args, **kwargs):
            return {'destination': 'Roma'}
        
        self.ai_handler._extract_tool_parameters = mock_extract_destination
        
        response = self.ai_handler.continue_tool_clarification(session_id, "Roma")
        print(f"[FRANK] {response.text}")
        
        # Restore original method
        self.ai_handler._extract_tool_parameters = original_extract
        
        # Verify parameter received and tool execution
        assert any(e['action'] == 'tool_parameter_received' for e in self.events_emitted), "Should emit tool_parameter_received"
        assert any(e['action'] == 'tool_ready_to_start' for e in self.events_emitted), "Should emit tool_ready_to_start"
        assert any(e['action'] == 'tool_started' for e in self.events_emitted), "Should emit tool_started"
        assert any(e['action'] == 'tool_finished' for e in self.events_emitted), "Should emit tool_finished"
        assert any(e['action'] == 'tool_lifecycle_finished' for e in self.events_emitted), "Should emit tool_lifecycle_finished"
        
        # Verify session is cleaned up
        assert not self.ai_handler.is_tool_session_active(session_id), "Tool session should be cleaned up"
        
        print("\n✅ Conversation A test passed!")
        return True
    
    def test_conversation_b_weather_cancellation(self):
        """Test Conversation B: Weather tool with cancellation"""
        print("\n" + "="*60)
        print("TESTING CONVERSATION B: Weather Tool (Cancellation)")
        print("="*60)
        
        self.events_emitted = []
        session_id = "test_session_b"
        
        # Step 1: User says "Mostrami il meteo"
        print("\n[USER] Mostrami il meteo")
        
        # Simulate tool detection and handling
        tool_intent = {
            'primary_category': 'weather',
            'confidence': 0.9,
            'detection_method': 'pattern'
        }
        
        context = {'session_id': session_id}
        
        # Mock parameter extraction to return empty parameters (missing location)
        original_extract = self.ai_handler._extract_tool_parameters
        def mock_extract_empty(*args, **kwargs):
            return {}
        
        self.ai_handler._extract_tool_parameters = mock_extract_empty
        
        response = self.ai_handler._handle_tool_request("Mostrami il meteo", tool_intent, context)
        
        print(f"[FRANK] {response.text}")
        
        # Verify session was created
        assert self.ai_handler.is_tool_session_active(session_id), "Tool session should be active"
        
        # Step 2: User tries to change topic
        print("\n[USER] Non importa, parliamo d'altro")
        response = self.ai_handler.continue_tool_clarification(session_id, "Non importa, parliamo d'altro")
        print(f"[FRANK] {response.text}")
        
        # Verify gating notice
        assert any(e['action'] == 'tool_gating_notice' for e in self.events_emitted), "Should emit tool_gating_notice"
        
        # Step 3: User cancels
        print("\n[USER] annulla")
        response = self.ai_handler.continue_tool_clarification(session_id, "annulla")
        print(f"[FRANK] {response.text}")
        
        # Restore original method
        self.ai_handler._extract_tool_parameters = original_extract
        
        # Verify cancellation events
        assert any(e['action'] == 'tool_session_canceled' for e in self.events_emitted), "Should emit tool_session_canceled"
        assert any(e['action'] == 'tool_lifecycle_finished' for e in self.events_emitted), "Should emit tool_lifecycle_finished"
        
        # Verify session is cleaned up
        assert not self.ai_handler.is_tool_session_active(session_id), "Tool session should be cleaned up"
        
        print("\n✅ Conversation B test passed!")
        return True
    
    def test_immediate_execution(self):
        """Test tool with all parameters provided immediately"""
        print("\n" + "="*60)
        print("TESTING IMMEDIATE EXECUTION: Tool with complete parameters")
        print("="*60)
        
        self.events_emitted = []
        session_id = "test_session_immediate"
        
        # Mock a tool request where all parameters are already present
        # This would happen if the LLM successfully extracts all required params
        print("\n[USER] Get vehicle status")
        
        tool_intent = {
            'primary_category': 'vehicle',
            'confidence': 0.9,
            'detection_method': 'pattern'
        }
        
        context = {'session_id': session_id}
        
        # Mock parameter extraction to return complete parameters
        original_extract = self.ai_handler._extract_tool_parameters
        def mock_extract_complete(*args, **kwargs):
            # Return empty params (vehicle status tool has no required params)
            return {}
        
        self.ai_handler._extract_tool_parameters = mock_extract_complete
        
        response = self.ai_handler._handle_tool_request("Get vehicle status", tool_intent, context)
        
        print(f"[FRANK] {response.text}")
        
        # Restore original method
        self.ai_handler._extract_tool_parameters = original_extract
        
        # Verify immediate execution events
        assert any(e['action'] == 'tool_lifecycle_started' for e in self.events_emitted), "Should emit tool_lifecycle_started"
        assert any(e['action'] == 'tool_selected' for e in self.events_emitted), "Should emit tool_selected"
        assert any(e['action'] == 'tool_ready_to_start' for e in self.events_emitted), "Should emit tool_ready_to_start"
        assert any(e['action'] == 'tool_started' for e in self.events_emitted), "Should emit tool_started"
        assert any(e['action'] == 'tool_finished' for e in self.events_emitted), "Should emit tool_finished"
        assert any(e['action'] == 'tool_lifecycle_finished' for e in self.events_emitted), "Should emit tool_lifecycle_finished"
        
        # Verify session is cleaned up
        assert not self.ai_handler.is_tool_session_active(session_id), "Tool session should be cleaned up"
        
        print("\n✅ Immediate execution test passed!")
        return True
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("Starting Tool Lifecycle Management Tests...")
        
        try:
            test_a_result = self.test_conversation_a_navigation_scenario()
            test_b_result = self.test_conversation_b_weather_cancellation()
            test_immediate_result = self.test_immediate_execution()
            
            if test_a_result and test_b_result and test_immediate_result:
                print("\n" + "="*60)
                print("🎉 ALL TESTS PASSED! Tool lifecycle management is working correctly.")
                print("The following key features have been validated:")
                print("- Tool session creation at detection time")
                print("- Rigorous message gating during active tool sessions")
                print("- Parameter collection with validation")
                print("- Comprehensive event emission for debug visualization")
                print("- Proper session cleanup after completion/cancellation")
                print("- Support for immediate execution when parameters are complete")
                print("="*60)
                return True
            else:
                print("\n❌ Some tests failed!")
                return False
                
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise during testing
    
    tester = TestToolLifecycle()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
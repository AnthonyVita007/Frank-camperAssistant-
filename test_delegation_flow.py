#!/usr/bin/env python3
"""
Test script for the ToolLifecycleAgent delegation system.
Validates the delegation flow as described in the problem statement.
"""

import sys
import os
import time
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ai.ai_handler import AIHandler
from backend.ai.tool_lifecycle_agent import ToolLifecycleAgent
from backend.mcp.mcp_handler import MCPHandler
from backend.mcp.tool_registry import ToolRegistry

class MockAIProcessor:
    """Mock AI processor for testing"""
    def is_available(self):
        return True
    
    def process_request(self, text, context=None):
        from backend.ai.ai_response import AIResponse
        return AIResponse(
            text=f"Mock conversational response to: {text}",
            success=True,
            response_type="conversational"
        )

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
                'required': self.required,
                'properties': {param: {'type': 'string'} for param in self.required}
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

class MockLLMIntentDetector:
    """Mock LLM Intent Detector with confidence levels"""
    def __init__(self):
        self.enabled = True
    
    def is_enabled(self):
        return self.enabled
    
    def detect_intent(self, user_input, available_tools=None, context=None):
        from backend.ai.llm_intent_detector import IntentDetectionResult
        
        # Mock high confidence for specific tool requests
        if "rotta" in user_input.lower() or "navigazione" in user_input.lower():
            return IntentDetectionResult(
                requires_tool=True,
                primary_intent="navigation",
                confidence=0.9,  # High confidence
                reasoning="Clear navigation request",
                extracted_parameters={},
                multi_intent=False,
                clarification_needed=False,
                clarification_questions=[]
            )
        elif "meteo" in user_input.lower() or "tempo" in user_input.lower():
            return IntentDetectionResult(
                requires_tool=True,
                primary_intent="weather",
                confidence=0.85,  # High confidence
                reasoning="Clear weather request",
                extracted_parameters={},
                multi_intent=False,
                clarification_needed=False,
                clarification_questions=[]
            )
        elif "come stai" in user_input.lower() or "ciao" in user_input.lower():
            return IntentDetectionResult(
                requires_tool=False,
                primary_intent="conversational",
                confidence=0.95,  # High confidence for conversation
                reasoning="Conversational greeting",
                extracted_parameters={},
                multi_intent=False,
                clarification_needed=False,
                clarification_questions=[]
            )
        else:
            # Low confidence
            return IntentDetectionResult(
                requires_tool=False,
                primary_intent=None,
                confidence=0.2,  # Low confidence
                reasoning="Unclear intent",
                extracted_parameters={},
                multi_intent=False,
                clarification_needed=False,
                clarification_questions=[]
            )

class TestDelegationFlow:
    def __init__(self):
        self.events = []
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up the test environment with mocks"""
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
        
        # Create mock AI processor
        self.mock_ai_processor = MockAIProcessor()
        
        # Create mock MCP system
        self.tool_registry = ToolRegistry()
        self.mcp_handler = MCPHandler(self.tool_registry)
        
        # Register mock tools
        nav_tool = MockTool('set_route_sample', 'navigation', ['destination'])
        weather_tool = MockTool('get_weather_sample', 'weather', ['location'])
        vehicle_tool = MockTool('get_vehicle_status_sample', 'vehicle', [])
        
        # Mock the registry methods
        self.tool_registry._tools = {
            'set_route_sample': nav_tool,
            'get_weather_sample': weather_tool,
            'get_vehicle_status_sample': vehicle_tool
        }
        
        # Mock the MCP handler methods
        def mock_get_tools_by_category(category):
            tools = []
            for tool in self.tool_registry._tools.values():
                if tool.category == category:
                    tools.append(tool.get_tool_info())
            return tools
        
        def mock_execute_tool(tool_name, parameters):
            if tool_name in self.tool_registry._tools:
                return self.tool_registry._tools[tool_name].execute(parameters)
            else:
                from backend.mcp.mcp_tool import ToolResult, ToolResultStatus
                return ToolResult(False, f"Tool {tool_name} not found", ToolResultStatus.ERROR)
        
        self.mcp_handler.get_tools_by_category = mock_get_tools_by_category
        self.mcp_handler.execute_tool = mock_execute_tool
        
        # Create event emitter
        def event_emitter(action, data):
            event = {'action': action, 'data': data}
            self.events.append(event)
            print(f"[EVENT] {action}: {data}")
        
        # Create AI handler with delegation support
        self.ai_handler = AIHandler(
            ai_processor=self.mock_ai_processor,
            mcp_handler=self.mcp_handler,
            event_emitter=event_emitter
        )
        
        # Replace the LLM intent detector with our mock
        mock_detector = MockLLMIntentDetector()
        self.ai_handler._llm_intent_detector = mock_detector
        self.ai_handler._llm_intent_enabled = True
        
        print("✅ Test environment set up successfully!")
    
    def clear_events(self):
        """Clear the events list"""
        self.events = []
    
    def test_high_confidence_delegation(self):
        """Test high confidence tool request triggers immediate delegation"""
        print("\n--- Test: High Confidence Delegation ---")
        self.clear_events()
        
        # High confidence navigation request
        response = self.ai_handler.route_user_message("test_session", "Impostami una rotta per Roma")
        
        # Check for delegation events
        delegation_events = [e for e in self.events if e['action'] in ['delegation_main_to_agent', 'delegation_agent_to_main']]
        tool_events = [e for e in self.events if e['action'].startswith('tool_')]
        
        assert len(delegation_events) >= 1, f"Expected delegation events, got: {delegation_events}"
        assert len(tool_events) >= 1, f"Expected tool events, got: {tool_events}"
        
        # Verify delegation_main_to_agent was emitted
        main_to_agent = [e for e in self.events if e['action'] == 'delegation_main_to_agent']
        assert len(main_to_agent) >= 1, "Should emit delegation_main_to_agent"
        
        print("✅ High confidence delegation works!")
        
    def test_conversational_no_delegation(self):
        """Test conversational request doesn't trigger delegation"""
        print("\n--- Test: Conversational No Delegation ---")
        self.clear_events()
        
        # Conversational request
        response = self.ai_handler.route_user_message("test_session_conv", "Ciao, come stai?")
        
        # Check for no delegation events
        delegation_events = [e for e in self.events if e['action'] in ['delegation_main_to_agent', 'delegation_agent_to_main']]
        tool_events = [e for e in self.events if e['action'].startswith('tool_')]
        
        assert len(delegation_events) == 0, f"Should not have delegation events, got: {delegation_events}"
        assert len(tool_events) == 0, f"Should not have tool events, got: {tool_events}"
        assert response.response_type == "conversational", f"Should be conversational response, got: {response.response_type}"
        
        print("✅ Conversational no delegation works!")
    
    def test_delegation_with_clarification(self):
        """Test delegation with parameter clarification"""
        print("\n--- Test: Delegation with Clarification ---")
        self.clear_events()
        
        # Request that requires clarification (missing destination)
        response1 = self.ai_handler.route_user_message("test_clarify", "Impostami una rotta")
        
        # Check delegation started
        main_to_agent = [e for e in self.events if e['action'] == 'delegation_main_to_agent']
        assert len(main_to_agent) >= 1, "Should emit delegation_main_to_agent"
        
        # Check if clarification is active
        assert self.ai_handler.has_active_delegation("test_clarify"), "Delegation should be active"
        
        # Provide destination parameter
        response2 = self.ai_handler.route_user_message("test_clarify", "Milano")
        
        # Should have parameter received and completion events
        param_events = [e for e in self.events if e['action'] == 'tool_parameter_received']
        assert len(param_events) >= 1, "Should receive parameter events"
        
        print("✅ Delegation with clarification works!")
    
    def test_delegation_cancellation(self):
        """Test cancellation during delegation"""
        print("\n--- Test: Delegation Cancellation ---")
        self.clear_events()
        
        # Start delegation
        response1 = self.ai_handler.route_user_message("test_cancel", "Impostami una rotta")
        
        # Verify delegation is active
        assert self.ai_handler.has_active_delegation("test_cancel"), "Delegation should be active"
        
        # Cancel the operation
        response2 = self.ai_handler.route_user_message("test_cancel", "annulla")
        
        # Check for cancellation and delegation return events
        canceled_events = [e for e in self.events if e['action'] == 'tool_session_canceled']
        agent_to_main = [e for e in self.events if e['action'] == 'delegation_agent_to_main']
        
        assert len(canceled_events) >= 1, "Should emit tool_session_canceled"
        assert len(agent_to_main) >= 1, "Should emit delegation_agent_to_main"
        
        # Verify delegation is no longer active
        assert not self.ai_handler.has_active_delegation("test_cancel"), "Delegation should be inactive after cancellation"
        
        print("✅ Delegation cancellation works!")
    
    def test_gating_during_delegation(self):
        """Test that non-relevant input is gated during delegation"""
        print("\n--- Test: Gating During Delegation ---")
        self.clear_events()
        
        # Start delegation that needs clarification
        response1 = self.ai_handler.route_user_message("test_gate", "Impostami una rotta")
        
        # Try to send unrelated message
        response2 = self.ai_handler.route_user_message("test_gate", "Come stai?")
        
        # Should get gating notice
        gating_events = [e for e in self.events if e['action'] == 'tool_gating_notice']
        assert len(gating_events) >= 1, "Should emit tool_gating_notice for unrelated input"
        
        assert "gating" in response2.response_type or "Modalità Tool attiva" in response2.text, "Should indicate gating is active"
        
        print("✅ Gating during delegation works!")
    
    def run_all_tests(self):
        """Run all delegation tests"""
        print("Testing ToolLifecycleAgent Delegation System...")
        print("=" * 60)
        
        try:
            self.test_high_confidence_delegation()
            self.test_conversational_no_delegation()
            self.test_delegation_with_clarification()
            self.test_delegation_cancellation()
            self.test_gating_during_delegation()
            
            print("\n" + "=" * 60)
            print("🎉 ALL DELEGATION TESTS PASSED!")
            print("Key delegation features validated:")
            print("- High confidence tool requests trigger immediate delegation")
            print("- Conversational requests bypass delegation")
            print("- Delegation supports parameter clarification")
            print("- Cancellation works properly during delegation")
            print("- Gating prevents unrelated input during delegation")
            print("- Red delegation bubbles events are emitted correctly")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    test = TestDelegationFlow()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
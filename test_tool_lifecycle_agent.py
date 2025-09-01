#!/usr/bin/env python3

"""
Test script for ToolLifecycleAgent functionality.
This script tests the new delegation system without requiring full app setup.
"""

import sys
import os
import logging

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backend.ai.tool_lifecycle_agent import ToolLifecycleAgent
from backend.ai.ai_response import AIResponse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockAIProcessor:
    def process_request(self, prompt, context=None):
        # Simple mock that returns a basic clarification question
        if "destination" in prompt.lower():
            return AIResponse(
                text="Qual è la destinazione del viaggio?",
                success=True,
                response_type="ai_response"
            )
        return AIResponse(
            text="Fornisci i parametri mancanti.",
            success=True,
            response_type="ai_response"
        )

class MockMCPHandler:
    def execute_tool(self, tool_name, parameters):
        # Simple mock tool execution
        class MockResult:
            def __init__(self):
                self.success = True
                self.data = f"Executed {tool_name} with parameters: {parameters}"
        
        return MockResult()

class TestToolLifecycleAgent:
    def __init__(self):
        self.events_emitted = []
        self.completion_callbacks = []
        
    def event_emitter(self, action: str, data: dict):
        """Capture emitted events for testing"""
        self.events_emitted.append({'action': action, 'data': data})
        print(f"[EVENT] {action}: {data}")
    
    def on_complete_callback(self, session_id: str, outcome: dict):
        """Capture completion callbacks"""
        self.completion_callbacks.append({'session_id': session_id, 'outcome': outcome})
        print(f"[COMPLETION] Session {session_id}: {outcome}")
    
    def test_basic_functionality(self):
        """Test basic ToolLifecycleAgent functionality"""
        print("\n" + "="*60)
        print("TESTING TOOL LIFECYCLE AGENT - BASIC FUNCTIONALITY")
        print("="*60)
        
        # Create the agent
        agent = ToolLifecycleAgent(
            ai_processor=MockAIProcessor(),
            mcp_handler=MockMCPHandler(),
            event_emitter=self.event_emitter,
            on_complete=self.on_complete_callback
        )
        
        # Test 1: Start a tool with missing parameters
        print("\n--- Test 1: Start tool with missing parameters ---")
        self.events_emitted = []
        
        tool_info = {
            'name': 'set_route_sample',
            'description': 'Set navigation route',
            'parameters_schema': {
                'type': 'object',
                'properties': {
                    'destination': {'type': 'string', 'description': 'Destination'}
                },
                'required': ['destination']
            }
        }
        
        agent.start('test_session', 'set_route_sample', tool_info, {})
        
        # Verify events
        assert any(e['action'] == 'tool_lifecycle_started' for e in self.events_emitted), "Should emit tool_lifecycle_started"
        assert any(e['action'] == 'tool_selected' for e in self.events_emitted), "Should emit tool_selected"
        print("✅ Tool start with missing parameters works!")
        
        # Test 2: Provide parameter
        print("\n--- Test 2: Provide missing parameter ---")
        response = agent.handle_user_message('test_session', 'Roma')
        
        assert response.success, f"Should succeed, got: {response.text}"
        assert any(e['action'] == 'tool_parameter_received' for e in self.events_emitted), "Should emit tool_parameter_received"
        assert any(e['action'] == 'tool_started' for e in self.events_emitted), "Should emit tool_started"
        assert any(e['action'] == 'tool_finished' for e in self.events_emitted), "Should emit tool_finished"
        print("✅ Parameter provision and execution works!")
        
        # Test 3: Cancellation
        print("\n--- Test 3: Tool cancellation ---")
        self.events_emitted = []
        self.completion_callbacks = []
        
        # Start new session
        agent.start('test_session_2', 'set_route_sample', tool_info, {})
        
        # Cancel it
        response = agent.cancel('test_session_2', 'user_request')
        
        assert response.success, f"Cancellation should succeed, got: {response.text}"
        assert any(e['action'] == 'tool_session_canceled' for e in self.events_emitted), "Should emit tool_session_canceled"
        assert any(e['action'] == 'tool_lifecycle_finished' for e in self.events_emitted), "Should emit tool_lifecycle_finished"
        assert len(self.completion_callbacks) > 0, "Should call completion callback"
        print("✅ Tool cancellation works!")
        
        # Test 4: Immediate execution (no missing parameters)
        print("\n--- Test 4: Immediate execution ---")
        self.events_emitted = []
        self.completion_callbacks = []
        
        # Start with complete parameters
        complete_params = {'destination': 'Milano'}
        agent.start('test_session_3', 'set_route_sample', tool_info, complete_params)
        
        # Should execute immediately
        assert any(e['action'] == 'tool_parameters_ready' for e in self.events_emitted), "Should emit tool_parameters_ready"
        assert any(e['action'] == 'tool_started' for e in self.events_emitted), "Should emit tool_started"
        assert any(e['action'] == 'tool_finished' for e in self.events_emitted), "Should emit tool_finished"
        assert len(self.completion_callbacks) > 0, "Should call completion callback"
        print("✅ Immediate execution works!")
        
        print("\n🎉 All ToolLifecycleAgent tests passed!")
        return True

def main():
    """Run the tests"""
    try:
        tester = TestToolLifecycleAgent()
        success = tester.test_basic_functionality()
        
        if success:
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED!")
            print("The ToolLifecycleAgent is working correctly.")
            print("Key features validated:")
            print("- Tool lifecycle management with state transitions")
            print("- Parameter collection and validation")
            print("- Event emission (blue events) for UI compatibility")
            print("- Tool execution via MCP")
            print("- Cancellation handling")
            print("- Completion callbacks for delegation release")
            print("="*60)
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
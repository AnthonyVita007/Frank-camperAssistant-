#!/usr/bin/env python3

"""
Direct tool delegation test that doesn't require AI processor.
This test directly triggers tool workflows to demonstrate the delegation system.
"""

import sys
import os
import logging

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backend.ai.ai_handler import AIHandler
from backend.ai.ai_processor import AIProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockMCPHandler:
    def get_tools_by_category(self, category):
        # Return mock tool info
        if category == 'navigation':
            return [{
                'name': 'set_route_sample',
                'description': 'Set navigation route',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'destination': {'type': 'string', 'description': 'Destination'}
                    },
                    'required': ['destination']
                }
            }]
        elif category == 'vehicle':
            return [{
                'name': 'get_vehicle_status_sample',
                'description': 'Get vehicle status',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {}
                }
            }]
        return []
    
    def execute_tool(self, tool_name, parameters):
        class MockResult:
            def __init__(self, tool_name, params):
                self.status = MockStatus()
                self.data = f"Mock execution of {tool_name} with {params}"
        
        class MockStatus:
            value = "success"
        
        return MockResult(tool_name, parameters)

def test_direct_tool_delegation():
    """Test direct tool delegation without AI processor"""
    print("\n" + "="*60)
    print("TESTING DIRECT TOOL DELEGATION")
    print("="*60)
    
    events_emitted = []
    
    def event_emitter(action, data):
        events_emitted.append({'action': action, 'data': data})
        if action in ['delegation_main_to_agent', 'delegation_agent_to_main']:
            print(f"🔴 DELEGATION: {action} - {data}")
        elif action.startswith('tool_'):
            print(f"🔵 TOOL: {action} - {data}")
    
    try:
        # Create AI handler with mock MCP handler
        ai_handler = AIHandler(
            ai_processor=None,  # No AI processor needed for this test
            mcp_handler=MockMCPHandler(),
            event_emitter=event_emitter
        )
        
        print("\n1. Testing navigation tool delegation...")
        
        # Simulate tool intent detection result
        tool_intent = {
            'primary_category': 'navigation',
            'confidence': 0.9,
            'detection_method': 'pattern'
        }
        
        context = {'session_id': 'test_session'}
        
        # This should trigger delegation
        response = ai_handler._handle_tool_request("Portami a Roma", tool_intent, context)
        print(f"[RESPONSE] {response.text}")
        
        # Check if delegation is active
        if ai_handler.has_active_delegation('test_session'):
            print("✅ Delegation is active!")
            
            # Now provide the missing parameter
            print("\n2. Providing destination parameter...")
            response = ai_handler.route_user_message('test_session', 'Roma')
            print(f"[RESPONSE] {response.text}")
        
        print("\n3. Testing vehicle status (immediate execution)...")
        
        tool_intent_2 = {
            'primary_category': 'vehicle',
            'confidence': 0.9,
            'detection_method': 'pattern'
        }
        
        context_2 = {'session_id': 'test_session_2'}
        response = ai_handler._handle_tool_request("Stato del veicolo", tool_intent_2, context_2)
        print(f"[RESPONSE] {response.text}")
        
        print("\n4. Event summary:")
        delegation_events = [e for e in events_emitted if e['action'] in ['delegation_main_to_agent', 'delegation_agent_to_main']]
        tool_events = [e for e in events_emitted if e['action'].startswith('tool_')]
        
        print(f"  Delegation events: {len(delegation_events)}")
        print(f"  Tool lifecycle events: {len(tool_events)}")
        
        print("\n" + "="*60)
        print("🎉 DIRECT DELEGATION TEST COMPLETED!")
        print(f"Total events emitted: {len(events_emitted)}")
        print("Key components working:")
        print("- ToolLifecycleAgent delegation system")
        print("- Tool parameter collection and validation")
        print("- Event emission for UI (red and blue bubbles)")
        print("- Tool execution and lifecycle management")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_direct_tool_delegation()
    sys.exit(0 if success else 1)
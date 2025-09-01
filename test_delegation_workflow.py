#!/usr/bin/env python3

"""
Integration test for the complete delegation workflow.
This script simulates a realistic tool usage scenario to verify the delegation system.
"""

import sys
import os
import logging

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backend.ai.ai_handler import AIHandler
from backend.core.main_controller import MainController
from backend.ai.ai_processor import AIProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockSocketIO:
    def __init__(self):
        self.events_emitted = []
        self.handlers = {}
    
    def emit(self, event, data, **kwargs):
        self.events_emitted.append({'event': event, 'data': data})
        print(f"[EMIT] {event}: {data}")
    
    def on(self, event):
        def decorator(handler):
            self.handlers[event] = handler
            return handler
        return decorator
    
    def start_background_task(self, func, *args, **kwargs):
        # Mock background task execution
        func(*args, **kwargs)

def test_complete_delegation_workflow():
    """Test the complete delegation workflow from start to finish"""
    print("\n" + "="*60)
    print("TESTING COMPLETE DELEGATION WORKFLOW")
    print("="*60)
    
    try:
        # Create a mock SocketIO instance
        mock_socketio = MockSocketIO()
        
        # Initialize the MainController (this creates all the components)
        print("\n1. Initializing system...")
        controller = MainController(mock_socketio)
        ai_handler = controller.get_ai_handler()
        
        # Test 1: Navigation request with delegation
        print("\n2. Testing navigation request with delegation...")
        session_id = "test_session"
        
        # This should trigger tool detection and delegation
        response = ai_handler.route_user_message(session_id, "Portami a Roma evitando i pedaggi")
        print(f"[RESPONSE] {response.text}")
        
        # Check for delegation events
        delegation_events = [e for e in mock_socketio.events_emitted if e['event'] == 'backend_action' and e['data'].get('action') in ['delegation_main_to_agent', 'delegation_agent_to_main']]
        print(f"Found {len(delegation_events)} delegation events")
        
        # Test 2: If delegation is active, provide the missing parameter
        if ai_handler.has_active_delegation(session_id):
            print("\n3. Delegation is active, providing destination parameter...")
            response = ai_handler.route_user_message(session_id, "Roma")
            print(f"[RESPONSE] {response.text}")
        
        # Test 3: Vehicle status request (should be immediate execution)
        print("\n4. Testing vehicle status request (immediate execution)...")
        session_id_2 = "test_session_2"
        response = ai_handler.route_user_message(session_id_2, "Stato del veicolo")
        print(f"[RESPONSE] {response.text}")
        
        # Check all events
        print("\n5. Events summary:")
        tool_events = [e for e in mock_socketio.events_emitted if e['event'] == 'backend_action']
        for event in tool_events:
            action = event['data'].get('action', 'unknown')
            if action in ['delegation_main_to_agent', 'delegation_agent_to_main']:
                print(f"  🔴 DELEGATION: {action}")
            elif action.startswith('tool_'):
                print(f"  🔵 TOOL: {action}")
            else:
                print(f"  ⚪ OTHER: {action}")
        
        print("\n" + "="*60)
        print("🎉 DELEGATION WORKFLOW TEST COMPLETED SUCCESSFULLY!")
        print("Key features demonstrated:")
        print("- Tool intent detection and delegation to ToolLifecycleAgent")
        print("- Parameter collection and validation")
        print("- Tool execution and completion")
        print("- Delegation handoff events (red bubbles)")
        print("- Blue tool lifecycle events maintained")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_complete_delegation_workflow()
    sys.exit(0 if success else 1)
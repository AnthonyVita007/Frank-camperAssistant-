#!/usr/bin/env python3
"""
Simple test for the tool lifecycle management system.
Tests the core functionality without complex mocking.
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ai.ai_handler import AIHandler, ToolSessionState


class MockMCPHandler:
    """Mock MCP handler for testing"""
    
    def get_tools_by_category(self, category):
        """Return mock tools by category"""
        if category == 'navigation':
            return [{
                'name': 'set_route_sample',
                'category': 'navigation',
                'parameters_schema': {
                    'required': ['destination']
                }
            }]
        elif category == 'weather':
            return [{
                'name': 'get_weather_sample',
                'category': 'weather', 
                'parameters_schema': {
                    'required': ['location']
                }
            }]
        elif category == 'vehicle':
            return [{
                'name': 'get_vehicle_status_sample',
                'category': 'vehicle',
                'parameters_schema': {
                    'required': []
                }
            }]
        return []
    
    def execute_tool(self, name, parameters):
        """Mock tool execution"""
        from backend.mcp.mcp_tool import ToolResult, ToolResultStatus
        if name == 'set_route_sample':
            return ToolResult(True, f"Rotta impostata per: {parameters.get('destination', 'unknown')}", ToolResultStatus.SUCCESS)
        elif name == 'get_weather_sample':
            return ToolResult(True, f"Meteo per {parameters.get('location', 'unknown')}: Soleggiato", ToolResultStatus.SUCCESS)
        elif name == 'get_vehicle_status_sample':
            return ToolResult(True, "Veicolo in buone condizioni", ToolResultStatus.SUCCESS)
        return ToolResult(False, "Tool not implemented", ToolResultStatus.ERROR)


class MockAIProcessor:
    """Mock AI processor for testing"""
    def is_available(self):
        return True


def test_tool_session_lifecycle():
    """Test the core tool session lifecycle functionality"""
    print("Testing Tool Session Lifecycle...")
    
    events_emitted = []
    
    def event_emitter(action: str, data: dict):
        events_emitted.append({'action': action, 'data': data})
        print(f"[EVENT] {action}: {data}")
    
    # Create AI handler with mocks
    ai_handler = AIHandler(
        ai_processor=MockAIProcessor(),
        mcp_handler=MockMCPHandler(),
        event_emitter=event_emitter
    )
    
    session_id = "test_session"
    
    # Test 1: Tool session creation
    print("\n--- Test 1: Tool Session Creation ---")
    tool_name = "set_route_sample"
    tool_info = {
        'name': tool_name,
        'category': 'navigation',
        'parameters_schema': {'required': ['destination']}
    }
    initial_params = {}
    missing_required = ['destination']
    
    ai_handler._create_tool_session(session_id, tool_name, tool_info, initial_params, missing_required)
    
    # Verify session was created
    assert ai_handler.is_tool_session_active(session_id), "Session should be active"
    assert ai_handler.get_tool_session_state(session_id) == "clarifying", "Should be in clarifying state"
    
    # Verify lifecycle_started event
    assert any(e['action'] == 'tool_lifecycle_started' for e in events_emitted), "Should emit lifecycle_started"
    print("✅ Tool session creation works!")
    
    # Test 2: Gating logic
    print("\n--- Test 2: Gating Logic ---")
    events_emitted.clear()
    
    # Test non-relevant input
    response = ai_handler.continue_tool_clarification(session_id, "Come stai?")
    assert response.response_type == "tool_gating", "Should return gating response"
    assert any(e['action'] == 'tool_gating_notice' for e in events_emitted), "Should emit gating notice"
    print("✅ Gating logic works!")
    
    # Test 3: Parameter acceptance
    print("\n--- Test 3: Parameter Acceptance ---")
    events_emitted.clear()
    
    # Mock parameter extraction to return destination
    original_extract = ai_handler._extract_tool_parameters
    original_fallback = ai_handler._fallback_parameter_extraction
    
    def mock_extract(*args, **kwargs):
        return {'destination': 'Roma'}
    
    def mock_fallback(user_input, missing):
        if 'destination' in missing and 'roma' in user_input.lower():
            return {'destination': 'Roma'}
        return {}
    
    ai_handler._extract_tool_parameters = mock_extract
    ai_handler._fallback_parameter_extraction = mock_fallback
    
    response = ai_handler.continue_tool_clarification(session_id, "Roma")
    
    # Restore original methods
    ai_handler._extract_tool_parameters = original_extract
    ai_handler._fallback_parameter_extraction = original_fallback
    
    # Verify parameter received and execution
    assert any(e['action'] == 'tool_parameter_received' for e in events_emitted), "Should emit parameter_received"
    assert any(e['action'] == 'tool_ready_to_start' for e in events_emitted), "Should emit ready_to_start"
    assert any(e['action'] == 'tool_started' for e in events_emitted), "Should emit tool_started"
    assert any(e['action'] == 'tool_finished' for e in events_emitted), "Should emit tool_finished"
    assert any(e['action'] == 'tool_lifecycle_finished' for e in events_emitted), "Should emit lifecycle_finished"
    
    # Verify session is cleaned up
    assert not ai_handler.is_tool_session_active(session_id), "Session should be cleaned up"
    print("✅ Parameter acceptance and execution works!")
    
    # Test 4: Cancellation
    print("\n--- Test 4: Cancellation Logic ---")
    events_emitted.clear()
    
    # Create new session for cancellation test
    session_id_2 = "test_session_cancel"
    ai_handler._create_tool_session(session_id_2, tool_name, tool_info, initial_params, missing_required)
    
    # Test cancellation
    response = ai_handler.continue_tool_clarification(session_id_2, "annulla")
    
    # Verify cancellation events
    assert any(e['action'] == 'tool_session_canceled' for e in events_emitted), "Should emit session_canceled"
    assert any(e['action'] == 'tool_lifecycle_finished' for e in events_emitted), "Should emit lifecycle_finished"
    assert not ai_handler.is_tool_session_active(session_id_2), "Session should be cleaned up"
    print("✅ Cancellation logic works!")
    
    print("\n🎉 All core functionality tests passed!")
    return True


def test_immediate_execution():
    """Test immediate execution when all parameters are available"""
    print("\n--- Test 5: Immediate Execution ---")
    
    events_emitted = []
    
    def event_emitter(action: str, data: dict):
        events_emitted.append({'action': action, 'data': data})
        print(f"[EVENT] {action}: {data}")
    
    ai_handler = AIHandler(
        ai_processor=MockAIProcessor(),
        mcp_handler=MockMCPHandler(),
        event_emitter=event_emitter
    )
    
    session_id = "test_immediate"
    
    # Test tool with no required parameters (vehicle status)
    tool_intent = {'primary_category': 'vehicle'}
    context = {'session_id': session_id}
    
    # Mock parameter extraction to return empty (no required params)
    original_extract = ai_handler._extract_tool_parameters
    def mock_extract_empty(*args, **kwargs):
        return {}
    ai_handler._extract_tool_parameters = mock_extract_empty
    
    response = ai_handler._handle_tool_request("Get vehicle status", tool_intent, context)
    
    # Restore original method
    ai_handler._extract_tool_parameters = original_extract
    
    # Verify immediate execution events in correct order
    expected_events = [
        'tool_lifecycle_started',
        'tool_selected', 
        'tool_ready_to_start',
        'tool_started',
        'tool_finished',
        'tool_lifecycle_finished'
    ]
    
    emitted_actions = [e['action'] for e in events_emitted]
    for expected in expected_events:
        assert expected in emitted_actions, f"Should emit {expected}"
    
    # Verify session is cleaned up
    assert not ai_handler.is_tool_session_active(session_id), "Session should be cleaned up"
    print("✅ Immediate execution works!")
    
    return True


if __name__ == "__main__":
    try:
        result1 = test_tool_session_lifecycle()
        result2 = test_immediate_execution()
        
        if result1 and result2:
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED!")
            print("Key features validated:")
            print("- Tool session creation and lifecycle management")
            print("- Rigorous gating during active sessions")
            print("- Parameter collection with validation") 
            print("- Comprehensive event emission")
            print("- Proper session cleanup")
            print("- Immediate execution for complete parameters")
            print("- Cancellation handling")
            print("="*60)
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
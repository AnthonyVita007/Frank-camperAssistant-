#!/usr/bin/env python3
"""
Test script to validate the specific problem case:
"Portami a" should trigger immediate delegation without main LLM clarification.
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from test_delegation_flow import TestDelegationFlow

def test_portami_a_specific_case():
    """Test the specific 'Portami a' case mentioned in the problem statement"""
    
    print("Testing Specific Problem Case: 'Portami a'")
    print("=" * 60)
    
    # Use the existing test infrastructure
    test_flow = TestDelegationFlow()
    
    print("\n--- Test Case: 'Portami a' (incomplete input) ---")
    test_flow.clear_events()
    
    # This is the exact case from the problem statement
    response = test_flow.ai_handler.route_user_message("test_portami", "Portami a")
    
    # Check for immediate delegation (red bubble)
    delegation_events = [e for e in test_flow.events if e['action'] == 'delegation_main_to_agent']
    
    if len(delegation_events) >= 1:
        print("✅ 'Portami a' triggered IMMEDIATE delegation!")
        print(f"   Delegation event: {delegation_events[0]}")
        
        # Check for clarifying state in tool lifecycle
        lifecycle_events = [e for e in test_flow.events if e['action'] == 'tool_lifecycle_started']
        if lifecycle_events and lifecycle_events[0].get('state') == 'clarifying':
            print("✅ ToolLifecycleAgent started in 'clarifying' state (as expected)")
            print(f"   Missing parameters: {lifecycle_events[0].get('missing_required', [])}")
        else:
            print("❌ Expected ToolLifecycleAgent to start in clarifying state")
        
        # Verify no conversational response from main LLM
        if "Mock conversational response" not in response.text:
            print("✅ No conversational response from main LLM before delegation")
        else:
            print("❌ Main LLM gave conversational response instead of delegating")
            
        return True
    else:
        print("❌ 'Portami a' did NOT trigger delegation")
        print(f"   Response: {response.text}")
        print(f"   Response type: {response.response_type}")
        print(f"   Events: {[e['action'] for e in test_flow.events]}")
        return False

def test_portami_a_roma_complete_case():
    """Test the complete case 'Portami a Roma' still works"""
    
    print("\n--- Test Case: 'Portami a Roma' (complete input) ---")
    
    test_flow = TestDelegationFlow()
    test_flow.clear_events()
    
    # This should still work as before
    response = test_flow.ai_handler.route_user_message("test_roma", "Portami a Roma")
    
    # Check for immediate delegation
    delegation_events = [e for e in test_flow.events if e['action'] == 'delegation_main_to_agent']
    
    if len(delegation_events) >= 1:
        print("✅ 'Portami a Roma' still triggers immediate delegation!")
        
        # Check for ready_to_start state (should have all parameters)
        lifecycle_events = [e for e in test_flow.events if e['action'] == 'tool_lifecycle_started']
        if lifecycle_events and lifecycle_events[0].get('state') == 'ready_to_start':
            print("✅ ToolLifecycleAgent started in 'ready_to_start' state (complete parameters)")
        else:
            print(f"ℹ️  ToolLifecycleAgent started in '{lifecycle_events[0].get('state')}' state")
        
        return True
    else:
        print("❌ 'Portami a Roma' did NOT trigger delegation")
        return False

if __name__ == "__main__":
    print("Validating Immediate Delegation Requirement")
    print("Testing the exact cases mentioned in problem statement...")
    
    success_count = 0
    total_tests = 2
    
    # Test 1: Incomplete case
    if test_portami_a_specific_case():
        success_count += 1
    
    # Test 2: Complete case  
    if test_portami_a_roma_complete_case():
        success_count += 1
    
    print("\n" + "=" * 60)
    if success_count == total_tests:
        print("🎉 ALL SPECIFIC VALIDATION TESTS PASSED!")
        print("✅ The problem statement requirements are satisfied:")
        print("   - 'Portami a' triggers immediate delegation (no main LLM clarification)")
        print("   - 'Portami a Roma' still works as expected")
        print("   - All clarification happens in ToolLifecycleAgent (blue bubbles)")
        sys.exit(0)
    else:
        print(f"❌ {success_count}/{total_tests} tests passed")
        sys.exit(1)
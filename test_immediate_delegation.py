#!/usr/bin/env python3
"""
Test script specifically for immediate delegation requirement.
Validates that ANY tool intent triggers immediate delegation regardless of confidence.
"""

import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Let's test the core issue directly - modify the confidence logic
# and check if low confidence tool intents can trigger delegation

def test_confidence_logic():
    """Test the confidence logic change we need to make"""
    
    print("Testing Confidence Logic...")
    print("=" * 50)
    
    # Simulate current behavior
    def current_logic(tool_intent):
        if not tool_intent:
            return "no_delegation", "No tool intent detected"
        
        confidence = tool_intent.get('confidence', 0.0)
        
        # Current logic
        if confidence >= 0.8:
            return "delegate", "High confidence delegation"
        elif confidence >= 0.5:
            return "delegate", "Medium confidence delegation"
        else:
            return "conversation", f"Low confidence ({confidence:.2f}), continuing conversation"
    
    # Proposed new logic
    def new_logic(tool_intent):
        if not tool_intent:
            return "no_delegation", "No tool intent detected"
        
        # NEW: Immediate delegation for ANY tool intent
        return "delegate", f"Immediate delegation (confidence: {tool_intent.get('confidence', 0.0):.2f})"
    
    # Test cases
    test_cases = [
        {"confidence": 0.9, "primary_category": "navigation", "desc": "High confidence navigation"},
        {"confidence": 0.6, "primary_category": "navigation", "desc": "Medium confidence navigation"},
        {"confidence": 0.3, "primary_category": "navigation", "desc": "LOW confidence navigation (the problem case)"},
        {"confidence": 0.1, "primary_category": "weather", "desc": "Very low confidence weather"},
        {"confidence": None, "desc": "No tool intent"},
    ]
    
    print("\nTesting confidence logic changes:")
    print("-" * 50)
    
    for i, case in enumerate(test_cases):
        tool_intent = case if case.get("confidence") is not None else None
        desc = case["desc"]
        
        current_action, current_reason = current_logic(tool_intent)
        new_action, new_reason = new_logic(tool_intent)
        
        print(f"\nTest {i+1}: {desc}")
        print(f"  Current: {current_action} - {current_reason}")
        print(f"  New:     {new_action} - {new_reason}")
        
        if tool_intent and current_action != new_action:
            print(f"  ✨ CHANGE: {current_action} → {new_action}")
    
    print("\n" + "=" * 50)
    print("Key change: LOW confidence tool intents will now trigger delegation!")
    print("This solves the 'Portami a' problem - immediate delegation instead of clarification from main LLM.")

if __name__ == "__main__":
    test_confidence_logic()
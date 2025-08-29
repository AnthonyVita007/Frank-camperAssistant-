#!/usr/bin/env python3
"""
Test script for enhanced parameter extraction improvements.

This script tests the enhanced parameter extraction logic for the Frank Camper Assistant,
focusing on the improvements made to handle LLM parameter extraction failures.
"""

import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ai.ai_handler import AIHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_navigation_parameter_extraction():
    """Test navigation parameter extraction with enhanced fallback."""
    print("\n=== Testing Navigation Parameter Extraction ===")
    
    # Initialize AI Handler
    handler = AIHandler()
    
    # Test cases for navigation parameter extraction
    test_cases = [
        {
            'input': 'puoi portarmi a roma?',
            'expected_destination': 'Roma',
            'description': 'Basic navigation request to Rome'
        },
        {
            'input': 'Portami a Milano evitando i pedaggi',
            'expected_destination': 'Milano',
            'expected_avoid_tolls': True,
            'description': 'Navigation with toll avoidance'
        },
        {
            'input': 'Navigazione per Firenze senza autostrade',
            'expected_destination': 'Firenze',
            'expected_avoid_highways': True,
            'description': 'Navigation with highway avoidance'
        },
        {
            'input': 'Strada più veloce per Napoli',
            'expected_destination': 'Napoli',
            'expected_route_type': 'fastest',
            'description': 'Navigation with route preference'
        }
    ]
    
    # Mock tool info for navigation
    tool_info = {
        'name': 'navigation_tool',
        'parameters_schema': {
            'type': 'object',
            'properties': {
                'destination': {'type': 'string'},
                'avoid_tolls': {'type': 'boolean'},
                'avoid_highways': {'type': 'boolean'},
                'route_type': {'type': 'string'}
            }
        }
    }
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        print(f"\n--- Test: {test_case['description']} ---")
        print(f"Input: '{test_case['input']}'")
        
        # Extract parameters using enhanced fallback
        params = handler._extract_parameters_fallback(
            user_input=test_case['input'],
            tool_info=tool_info
        )
        
        print(f"Extracted parameters: {params}")
        
        # Check results
        success = True
        
        if 'expected_destination' in test_case:
            if params.get('destination') == test_case['expected_destination']:
                print(f"✓ Destination correctly extracted: {params.get('destination')}")
            else:
                print(f"✗ Expected destination '{test_case['expected_destination']}', got '{params.get('destination')}'")
                success = False
        
        if 'expected_avoid_tolls' in test_case:
            if params.get('avoid_tolls') == test_case['expected_avoid_tolls']:
                print(f"✓ Toll avoidance correctly extracted: {params.get('avoid_tolls')}")
            else:
                print(f"✗ Expected avoid_tolls '{test_case['expected_avoid_tolls']}', got '{params.get('avoid_tolls')}'")
                success = False
        
        if 'expected_avoid_highways' in test_case:
            if params.get('avoid_highways') == test_case['expected_avoid_highways']:
                print(f"✓ Highway avoidance correctly extracted: {params.get('avoid_highways')}")
            else:
                print(f"✗ Expected avoid_highways '{test_case['expected_avoid_highways']}', got '{params.get('avoid_highways')}'")
                success = False
        
        if 'expected_route_type' in test_case:
            if params.get('route_type') == test_case['expected_route_type']:
                print(f"✓ Route type correctly extracted: {params.get('route_type')}")
            else:
                print(f"✗ Expected route_type '{test_case['expected_route_type']}', got '{params.get('route_type')}'")
                success = False
        
        if success:
            print("✓ Test PASSED")
            passed += 1
        else:
            print("✗ Test FAILED")
    
    print(f"\n=== Navigation Parameter Extraction Results ===")
    print(f"Passed: {passed}/{total}")
    return passed == total

def test_other_category_extraction():
    """Test parameter extraction for other categories."""
    print("\n=== Testing Other Category Parameter Extraction ===")
    
    handler = AIHandler()
    
    test_cases = [
        {
            'category': 'weather',
            'input': 'Che tempo farà domani a Bologna?',
            'tool_info': {
                'name': 'weather_tool',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'location': {'type': 'string'},
                        'time_range': {'type': 'string'},
                        'weather_type': {'type': 'string'}
                    }
                }
            },
            'expected': {'location': 'Bologna', 'time_range': 'tomorrow'},
            'description': 'Weather forecast request'
        },
        {
            'category': 'vehicle',
            'input': 'Come va il motore?',
            'tool_info': {
                'name': 'vehicle_tool',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'system': {'type': 'string'},
                        'check_type': {'type': 'string'},
                        'urgency': {'type': 'string'}
                    }
                }
            },
            'expected': {'system': 'engine', 'check_type': 'status'},
            'description': 'Vehicle status check'
        },
        {
            'category': 'maintenance',
            'input': 'Cambio olio urgente',
            'tool_info': {
                'name': 'maintenance_tool',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'maintenance_type': {'type': 'string'},
                        'urgency': {'type': 'string'}
                    }
                }
            },
            'expected': {'maintenance_type': 'oil_change', 'urgency': 'high'},
            'description': 'Urgent oil change request'
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        print(f"\n--- Test: {test_case['description']} ---")
        print(f"Input: '{test_case['input']}'")
        
        params = handler._extract_parameters_fallback(
            user_input=test_case['input'],
            tool_info=test_case['tool_info']
        )
        
        print(f"Extracted parameters: {params}")
        
        success = True
        for key, expected_value in test_case['expected'].items():
            if params.get(key) == expected_value:
                print(f"✓ {key} correctly extracted: {params.get(key)}")
            else:
                print(f"✗ Expected {key} '{expected_value}', got '{params.get(key)}'")
                success = False
        
        if success:
            print("✓ Test PASSED")
            passed += 1
        else:
            print("✗ Test FAILED")
    
    print(f"\n=== Other Category Parameter Extraction Results ===")
    print(f"Passed: {passed}/{total}")
    return passed == total

def test_json_cleaning():
    """Test the enhanced JSON response cleaning."""
    print("\n=== Testing Enhanced JSON Response Cleaning ===")
    
    # Import the LLMIntentDetector to test JSON cleaning
    from ai.llm_intent_detector import LLMIntentDetector
    from ai.ai_processor import AIProcessor
    
    # Create a detector instance
    processor = AIProcessor()
    detector = LLMIntentDetector(processor)
    
    test_cases = [
        {
            'input': 'Here are the parameters: {"destination": "Roma"}',
            'expected': {"destination": "Roma"},
            'description': 'JSON in natural text'
        },
        {
            'input': '```json\n{"destination": "Milano", "avoid_tolls": true}\n```',
            'expected': {"destination": "Milano", "avoid_tolls": True},
            'description': 'JSON in code block'
        },
        {
            'input': 'I found these parameters:\nResult: {"location": "Bologna", "time_range": "tomorrow"}\nThat should work.',
            'expected': {"location": "Bologna", "time_range": "tomorrow"},
            'description': 'JSON mixed with text'
        },
        {
            'input': '{"system": "engine"}',
            'expected': {"system": "engine"},
            'description': 'Pure JSON'
        },
        {
            'input': 'The analysis shows that the user wants navigation.\njson: {"destination": "Firenze"}\nThis is the result.',
            'expected': {"destination": "Firenze"},
            'description': 'JSON after prefix'
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        print(f"\n--- Test: {test_case['description']} ---")
        print(f"Input: '{test_case['input']}'")
        
        try:
            cleaned = detector._clean_json_response(test_case['input'])
            print(f"Cleaned: '{cleaned}'")
            
            import json
            parsed = json.loads(cleaned)
            print(f"Parsed: {parsed}")
            
            if parsed == test_case['expected']:
                print("✓ Test PASSED")
                passed += 1
            else:
                print(f"✗ Expected {test_case['expected']}, got {parsed}")
        except Exception as e:
            print(f"✗ Test FAILED with error: {e}")
    
    print(f"\n=== JSON Cleaning Results ===")
    print(f"Passed: {passed}/{total}")
    return passed == total

def main():
    """Run all parameter extraction tests."""
    print("Starting Enhanced Parameter Extraction Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(test_navigation_parameter_extraction())
    results.append(test_other_category_extraction())
    results.append(test_json_cleaning())
    
    # Summary
    print("\n" + "=" * 60)
    print("OVERALL TEST RESULTS")
    print("=" * 60)
    
    test_names = [
        "Navigation Parameter Extraction",
        "Other Category Parameter Extraction", 
        "Enhanced JSON Response Cleaning"
    ]
    
    total_passed = sum(results)
    total_tests = len(results)
    
    for i, (name, passed) in enumerate(zip(test_names, results)):
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
    
    print(f"\nOverall: {total_passed}/{total_tests} test suites passed")
    
    if total_passed == total_tests:
        print("🎉 All tests passed! The enhanced parameter extraction is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
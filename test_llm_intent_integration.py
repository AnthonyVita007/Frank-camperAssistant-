#!/usr/bin/env python3
"""
Test script for LLM Intent Detection Integration.

This script tests the new LLM-based intent recognition system
with various natural language scenarios to ensure it works correctly
and falls back appropriately to pattern matching.
"""

import os
import sys
import time
import json
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai import AIHandler, LLMIntentDetector, IntentDetectionResult
from backend.ai.ai_processor import AIProcessor

#----------------------------------------------------------------
# TEST CONFIGURATION
#----------------------------------------------------------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

#----------------------------------------------------------------
# TEST SCENARIOS
#----------------------------------------------------------------

# Test cases for different types of intent recognition
TEST_SCENARIOS = [
    # Navigation scenarios
    {
        'input': 'Portami a Roma evitando i pedaggi',
        'expected_category': 'navigation',
        'expected_params': ['Roma', 'pedaggi'],
        'description': 'Navigation with destination and preferences'
    },
    {
        'input': 'Che strada faccio per arrivare a Firenze?',
        'expected_category': 'navigation',
        'expected_params': ['Firenze'],
        'description': 'Natural navigation question'
    },
    {
        'input': 'Imposta rotta per Milano senza autostrade',
        'expected_category': 'navigation',
        'expected_params': ['Milano', 'autostrade'],
        'description': 'Route with highway avoidance'
    },
    
    # Weather scenarios
    {
        'input': 'Che tempo farà domani a Bologna?',
        'expected_category': 'weather',
        'expected_params': ['Bologna', 'domani'],
        'description': 'Weather forecast for specific location'
    },
    {
        'input': 'Pioverà nel weekend?',
        'expected_category': 'weather',
        'expected_params': ['weekend', 'pioggia'],
        'description': 'Weather question with time reference'
    },
    {
        'input': 'Come è il meteo ora?',
        'expected_category': 'weather',
        'expected_params': ['ora'],
        'description': 'Current weather inquiry'
    },
    
    # Vehicle scenarios
    {
        'input': 'Come sta il camper?',
        'expected_category': 'vehicle',
        'expected_params': ['generale'],
        'description': 'General vehicle status'
    },
    {
        'input': 'Controlla il livello del carburante',
        'expected_category': 'vehicle',
        'expected_params': ['carburante'],
        'description': 'Specific fuel check'
    },
    {
        'input': 'Fammi vedere lo stato del motore',
        'expected_category': 'vehicle',
        'expected_params': ['motore'],
        'description': 'Engine status request'
    },
    
    # Maintenance scenarios
    {
        'input': 'Quando devo fare il tagliando?',
        'expected_category': 'maintenance',
        'expected_params': ['tagliando'],
        'description': 'Maintenance schedule inquiry'
    },
    {
        'input': 'Ricordami il cambio olio',
        'expected_category': 'maintenance',
        'expected_params': ['olio'],
        'description': 'Oil change reminder'
    },
    
    # Multi-intent scenarios  
    {
        'input': 'Portami a Roma e dimmi che tempo farà',
        'expected_category': 'navigation',  # Primary intent
        'expected_params': ['Roma', 'tempo'],
        'description': 'Multi-intent: navigation + weather'
    },
    {
        'input': 'Prima controlla il motore, poi imposta la rotta per Milano',
        'expected_category': 'vehicle',  # Primary intent
        'expected_params': ['motore', 'Milano'],
        'description': 'Multi-intent: vehicle + navigation'
    },
    
    # Context-dependent scenarios
    {
        'input': 'Come va?',
        'expected_category': None,  # Ambiguous without context
        'expected_params': [],
        'description': 'Context-dependent question',
        'context': {'last_topic': 'vehicle'}
    },
    {
        'input': 'E per domani?',
        'expected_category': None,  # Needs context
        'expected_params': [],
        'description': 'Context-dependent time reference',
        'context': {'last_topic': 'weather', 'last_location': 'Milano'}
    },
    
    # Conversational scenarios (no tools needed)
    {
        'input': 'Ciao Frank, come stai?',
        'expected_category': None,
        'expected_params': [],
        'description': 'Conversational greeting'
    },
    {
        'input': 'Grazie per l\'aiuto',
        'expected_category': None,
        'expected_params': [],
        'description': 'Conversational gratitude'
    },
    
    # Edge cases
    {
        'input': 'Roma',
        'expected_category': 'navigation',  # Might be navigation
        'expected_params': ['Roma'],
        'description': 'Single word location'
    },
    {
        'input': 'Aiuto!',
        'expected_category': None,
        'expected_params': [],
        'description': 'Emergency/help request'
    }
]

#----------------------------------------------------------------
# TEST FUNCTIONS
#----------------------------------------------------------------

def test_llm_intent_detector_standalone():
    """Test the LLM Intent Detector in isolation."""
    logger.info("=== Testing LLM Intent Detector Standalone ===")
    
    try:
        # Create AI processor
        ai_processor = AIProcessor()
        if not ai_processor.is_available():
            logger.warning("AI Processor not available - skipping LLM tests")
            return False
        
        # Create LLM intent detector
        detector = LLMIntentDetector(ai_processor=ai_processor)
        
        if not detector.is_enabled():
            logger.warning("LLM Intent Detector not enabled - skipping tests")
            return False
        
        logger.info(f"LLM Intent Detector Status: {detector.get_status()}")
        
        # Test a few scenarios
        test_inputs = [
            "Portami a Roma",
            "Che tempo fa?",
            "Come sta il motore?",
            "Ciao Frank"
        ]
        
        for test_input in test_inputs:
            logger.info(f"\nTesting input: '{test_input}'")
            
            start_time = time.time()
            result = detector.detect_intent(test_input)
            elapsed = time.time() - start_time
            
            logger.info(f"Result: requires_tool={result.requires_tool}, "
                       f"intent={result.primary_intent}, "
                       f"confidence={result.confidence:.2f}, "
                       f"time={elapsed:.2f}s")
            
            if result.requires_tool:
                logger.info(f"Parameters: {result.extracted_parameters}")
                logger.info(f"Reasoning: {result.reasoning}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing LLM Intent Detector standalone: {e}")
        return False

def test_ai_handler_hybrid_system():
    """Test the AI Handler with hybrid intent detection."""
    logger.info("\n=== Testing AI Handler Hybrid System ===")
    
    try:
        # Create AI handler with LLM intent detection enabled
        ai_handler = AIHandler(llm_intent_enabled=True)
        
        logger.info(f"AI Handler Status: {ai_handler.get_ai_status()}")
        logger.info(f"LLM Intent Enabled: {ai_handler.is_llm_intent_enabled()}")
        
        # Test scenarios
        for i, scenario in enumerate(TEST_SCENARIOS[:10]):  # Test first 10 scenarios
            logger.info(f"\n--- Test {i+1}: {scenario['description']} ---")
            logger.info(f"Input: '{scenario['input']}'")
            
            context = scenario.get('context')
            
            start_time = time.time()
            
            # Test intent detection directly
            intent_result = ai_handler._detect_tool_intent(scenario['input'], context)
            
            elapsed = time.time() - start_time
            
            if intent_result:
                logger.info(f"Intent detected: {intent_result.get('primary_category')}")
                logger.info(f"Confidence: {intent_result.get('confidence', 0):.2f}")
                logger.info(f"Detection method: {intent_result.get('detection_method', 'unknown')}")
                logger.info(f"Time: {elapsed:.2f}s")
                
                # Check if matches expected
                expected = scenario['expected_category']
                actual = intent_result.get('primary_category')
                
                if expected and actual == expected:
                    logger.info("✓ Expected intent matched")
                elif expected:
                    logger.warning(f"✗ Expected '{expected}' but got '{actual}'")
                else:
                    logger.info("ℹ No specific expectation")
            else:
                logger.info("No intent detected")
                if scenario['expected_category']:
                    logger.warning(f"✗ Expected '{scenario['expected_category']}' but got None")
                else:
                    logger.info("✓ Correctly identified as conversational")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing AI Handler hybrid system: {e}")
        return False

def test_pattern_matching_fallback():
    """Test that pattern matching fallback works when LLM is disabled."""
    logger.info("\n=== Testing Pattern Matching Fallback ===")
    
    try:
        # Create AI handler with LLM intent detection disabled
        ai_handler = AIHandler(llm_intent_enabled=False)
        
        logger.info(f"LLM Intent Enabled: {ai_handler.is_llm_intent_enabled()}")
        
        # Test a few clear navigation examples
        navigation_tests = [
            "Portami a Roma",
            "Navigazione verso Milano", 
            "Imposta rotta per Firenze"
        ]
        
        for test_input in navigation_tests:
            logger.info(f"\nTesting: '{test_input}'")
            
            intent_result = ai_handler._detect_tool_intent(test_input)
            
            if intent_result:
                logger.info(f"Detected: {intent_result.get('primary_category')} "
                           f"(method: {intent_result.get('detection_method', 'pattern')})")
                logger.info(f"Confidence: {intent_result.get('confidence', 0):.2f}")
            else:
                logger.info("No intent detected")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing pattern matching fallback: {e}")
        return False

def test_performance_comparison():
    """Compare performance between LLM and pattern matching."""
    logger.info("\n=== Performance Comparison ===")
    
    try:
        # Test inputs
        test_inputs = [
            "Portami a Roma",
            "Che tempo fa a Milano?",
            "Come sta il motore?",
            "Ciao Frank"
        ]
        
        # Test with LLM enabled
        ai_handler_llm = AIHandler(llm_intent_enabled=True)
        
        # Test with pattern matching only
        ai_handler_pattern = AIHandler(llm_intent_enabled=False)
        
        logger.info("Testing LLM-enabled handler...")
        llm_times = []
        for test_input in test_inputs:
            start_time = time.time()
            ai_handler_llm._detect_tool_intent(test_input)
            elapsed = time.time() - start_time
            llm_times.append(elapsed)
            logger.info(f"'{test_input}': {elapsed:.3f}s")
        
        logger.info("\nTesting pattern-only handler...")
        pattern_times = []
        for test_input in test_inputs:
            start_time = time.time()
            ai_handler_pattern._detect_tool_intent(test_input)
            elapsed = time.time() - start_time
            pattern_times.append(elapsed)
            logger.info(f"'{test_input}': {elapsed:.3f}s")
        
        # Calculate averages
        avg_llm = sum(llm_times) / len(llm_times)
        avg_pattern = sum(pattern_times) / len(pattern_times)
        
        logger.info(f"\nAverage times:")
        logger.info(f"LLM-enabled: {avg_llm:.3f}s")
        logger.info(f"Pattern-only: {avg_pattern:.3f}s")
        logger.info(f"Overhead: {(avg_llm - avg_pattern):.3f}s ({((avg_llm / avg_pattern - 1) * 100):.1f}%)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in performance comparison: {e}")
        return False

def run_all_tests():
    """Run all test functions."""
    logger.info("Starting LLM Intent Detection Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("LLM Intent Detector Standalone", test_llm_intent_detector_standalone),
        ("AI Handler Hybrid System", test_ai_handler_hybrid_system),
        ("Pattern Matching Fallback", test_pattern_matching_fallback),
        ("Performance Comparison", test_performance_comparison)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)
    
    logger.info(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.warning("⚠️ Some tests failed")
        return False

#----------------------------------------------------------------
# MAIN EXECUTION
#----------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LLM Intent Detection Integration")
    parser.add_argument("--test", choices=["standalone", "hybrid", "fallback", "performance", "all"], 
                       default="all", help="Which test to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.test == "standalone":
        success = test_llm_intent_detector_standalone()
    elif args.test == "hybrid":
        success = test_ai_handler_hybrid_system()
    elif args.test == "fallback":
        success = test_pattern_matching_fallback()
    elif args.test == "performance":
        success = test_performance_comparison()
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)
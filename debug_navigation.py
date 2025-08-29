#!/usr/bin/env python3
"""
Debug script for the specific failing case.
"""

import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ai.ai_handler import AIHandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def debug_navigation_extraction():
    """Debug the specific failing case."""
    handler = AIHandler()
    
    user_input = 'puoi portarmi a roma?'
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
    
    print(f"Input: '{user_input}'")
    print(f"Tool: {tool_info['name']}")
    
    # Test the navigation fallback extraction directly
    params = handler._extract_navigation_params_fallback(user_input)
    print(f"Navigation fallback result: {params}")
    
    # Test the overall fallback
    overall_params = handler._extract_parameters_fallback(user_input, tool_info)
    print(f"Overall fallback result: {overall_params}")

if __name__ == "__main__":
    debug_navigation_extraction()
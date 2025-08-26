"""
Test script for MCP Navigation functionality.

This script demonstrates the working navigation features of Frank Camper Assistant
without requiring external network resources or browser integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.ai.ai_handler import AIHandler

def test_navigation_commands():
    """Test various navigation commands."""
    
    print("🗺️  Testing Frank Camper Assistant - MCP Navigation Tool")
    print("=" * 60)
    
    # Initialize AI handler
    ai_handler = AIHandler()
    
    # Test different navigation commands
    test_commands = [
        "Portami a Roma evitando pedaggi",
        "vai a Milano",
        "navigazione per Firenze",
        "come arrivo a Venezia",
        "strada per Napoli senza autostrade"
    ]
    
    for i, command in enumerate(test_commands, 1):
        print(f"\n🚐 Test {i}: '{command}'")
        print("-" * 40)
        
        response = ai_handler.handle_ai_request(command)
        
        print(f"✅ Response: {response.text}")
        print(f"✅ Success: {response.success}")
        
        if response.success and response.metadata:
            action = response.metadata.get('action')
            if action == 'open_navigator':
                route_data = response.metadata.get('route_payload', {})
                stats = route_data.get('stats', {})
                warnings = route_data.get('warnings', [])
                
                print(f"🎯 Action: {action}")
                print(f"📊 Distance: {stats.get('distance_km', 0):.1f} km")
                print(f"⏱️  Duration: {stats.get('duration_min', 0):.0f} min")
                print(f"⚠️  Warnings: {len(warnings)}")
                
                for warning in warnings:
                    severity_icon = {"warning": "⚠️", "info": "ℹ️", "critical": "🚨"}.get(warning.get('severity', 'info'), "ℹ️")
                    print(f"   {severity_icon} {warning['message']}")
        
        print()

if __name__ == "__main__":
    test_navigation_commands()
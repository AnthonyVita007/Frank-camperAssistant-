"""
Navigation Tool for Frank Camper Assistant.

This module implements the NavigationTool MCP tool for offline-first route planning
and navigation with camper-specific considerations.
"""

import logging
import os
import configparser
from typing import Dict, Any, List, Optional, Tuple
import json

from ..mcp_tool import MCPTool, ToolResult, ToolResultType


class NavigationTool(MCPTool):
    """
    MCP tool for offline navigation and route planning.
    
    This tool provides offline-first navigation capabilities with special
    consideration for camper vehicles (width, height, weight restrictions).
    Supports multiple routing backends and fallback analysis.
    
    Features:
    - Offline-first route planning
    - Camper-specific warnings (bridges, width/height restrictions)
    - Multiple routing backend support (GraphHopper, Valhalla, fallback)
    - GeoJSON output for frontend map integration
    """
    
    def __init__(self) -> None:
        """Initialize the NavigationTool."""
        super().__init__(
            name="navigation",
            description="Plan routes with camper-specific considerations and offline capabilities"
        )
        
        # Load configuration
        self.config = self._load_config()
        self.router_type = self.config.get('navigation', 'ROUTER', fallback='none')
        self.router_url = self.config.get('navigation', 'ROUTER_URL', fallback='http://localhost:8989')
        
        logging.info(f'[NavigationTool] Initialized with router: {self.router_type}')
    
    def _load_config(self) -> configparser.ConfigParser:
        """Load configuration from config.ini."""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), '../../../config.ini')
        
        if os.path.exists(config_path):
            config.read(config_path)
        else:
            logging.warning('[NavigationTool] config.ini not found, using defaults')
        
        return config
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for navigation parameters.
        
        Returns:
            Dict[str, Any]: JSON schema for navigation tool
        """
        return {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "object",
                    "description": "Starting location",
                    "properties": {
                        "lat": {"type": "number", "minimum": -90, "maximum": 90},
                        "lon": {"type": "number", "minimum": -180, "maximum": 180},
                        "address": {"type": "string", "description": "Address string (alternative to lat/lon)"}
                    }
                },
                "destination": {
                    "type": "object",
                    "description": "Destination location",
                    "properties": {
                        "lat": {"type": "number", "minimum": -90, "maximum": 90},
                        "lon": {"type": "number", "minimum": -180, "maximum": 180},
                        "address": {"type": "string", "description": "Address string (alternative to lat/lon)"}
                    },
                    "required": ["lat", "lon", "address"]
                },
                "vehicle": {
                    "type": "object",
                    "description": "Vehicle specifications",
                    "properties": {
                        "width_m": {"type": "number", "default": 2.3, "minimum": 1.5, "maximum": 5.0},
                        "height_m": {"type": "number", "default": 3.1, "minimum": 2.0, "maximum": 5.0},
                        "length_m": {"type": "number", "default": 7.5, "minimum": 3.0, "maximum": 15.0},
                        "weight_tons": {"type": "number", "default": 3.5, "minimum": 1.0, "maximum": 20.0}
                    }
                },
                "preferences": {
                    "type": "object",
                    "description": "Route preferences",
                    "properties": {
                        "avoid_tolls": {"type": "boolean", "default": False},
                        "avoid_motorways": {"type": "boolean", "default": False},
                        "avoid_ferries": {"type": "boolean", "default": False},
                        "avoid_low_bridges": {"type": "boolean", "default": True},
                        "avoid_ztl": {"type": "boolean", "default": True}
                    }
                }
            },
            "required": ["destination"]
        }
    
    def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute navigation route planning.
        
        Args:
            parameters (Dict[str, Any]): Navigation parameters
            
        Returns:
            ToolResult: Route planning result with GeoJSON and warnings
        """
        logging.info('[NavigationTool] Executing navigation request')
        
        # Validate parameters
        validation_errors = self.validate_parameters(parameters)
        if validation_errors:
            return ToolResult(
                result_type=ToolResultType.ERROR,
                message=f"Parameter validation failed: {'; '.join(validation_errors)}"
            )
        
        try:
            # Extract and process parameters
            destination = parameters['destination']
            origin = parameters.get('origin', self._get_default_origin())
            vehicle = self._merge_vehicle_defaults(parameters.get('vehicle', {}))
            preferences = self._merge_preference_defaults(parameters.get('preferences', {}))
            
            # Attempt route planning based on configured router
            if self.router_type == 'graphhopper':
                route_result = self._plan_route_graphhopper(origin, destination, vehicle, preferences)
            elif self.router_type == 'valhalla':
                route_result = self._plan_route_valhalla(origin, destination, vehicle, preferences)
            else:
                # Fallback analysis
                route_result = self._plan_route_fallback(origin, destination, vehicle, preferences)
            
            # Analyze route for warnings
            warnings = self._analyze_route_warnings(route_result['route'], vehicle)
            
            # Prepare final result
            result_data = {
                'route': route_result['route'],
                'warnings': warnings,
                'stats': route_result['stats']
            }
            
            message = f"Route calculated: {result_data['stats']['distance_km']:.1f} km, " \
                     f"{result_data['stats']['duration_min']:.0f} min"
            
            if warnings:
                message += f" ({len(warnings)} warnings)"
            
            return ToolResult(
                result_type=ToolResultType.SUCCESS,
                data=result_data,
                message=message,
                metadata={
                    'router_used': self.router_type,
                    'vehicle_profile': 'camper',
                    'warning_count': len(warnings)
                }
            )
            
        except Exception as e:
            logging.error(f'[NavigationTool] Route planning failed: {e}')
            return ToolResult(
                result_type=ToolResultType.ERROR,
                message=f"Route planning failed: {str(e)}"
            )
    
    def _get_default_origin(self) -> Dict[str, float]:
        """Get default origin coordinates (current location or fallback)."""
        # For MVP, use a default location (Rome center)
        # In production, this would come from GPS
        return {
            'lat': 41.9028,
            'lon': 12.4964,
            'address': 'Current Location'
        }
    
    def _merge_vehicle_defaults(self, vehicle: Dict[str, Any]) -> Dict[str, float]:
        """Merge vehicle parameters with defaults."""
        defaults = {
            'width_m': 2.3,
            'height_m': 3.1,
            'length_m': 7.5,
            'weight_tons': 3.5
        }
        defaults.update(vehicle)
        return defaults
    
    def _merge_preference_defaults(self, preferences: Dict[str, Any]) -> Dict[str, bool]:
        """Merge route preferences with defaults."""
        defaults = {
            'avoid_tolls': False,
            'avoid_motorways': False,
            'avoid_ferries': False,
            'avoid_low_bridges': True,
            'avoid_ztl': True
        }
        defaults.update(preferences)
        return defaults
    
    def _plan_route_graphhopper(self, origin: Dict, destination: Dict, 
                               vehicle: Dict, preferences: Dict) -> Dict[str, Any]:
        """Plan route using GraphHopper (not implemented in MVP)."""
        # TODO: Implement GraphHopper integration
        logging.warning('[NavigationTool] GraphHopper not implemented, using fallback')
        return self._plan_route_fallback(origin, destination, vehicle, preferences)
    
    def _plan_route_valhalla(self, origin: Dict, destination: Dict,
                            vehicle: Dict, preferences: Dict) -> Dict[str, Any]:
        """Plan route using Valhalla (not implemented in MVP)."""
        # TODO: Implement Valhalla integration
        logging.warning('[NavigationTool] Valhalla not implemented, using fallback')
        return self._plan_route_fallback(origin, destination, vehicle, preferences)
    
    def _plan_route_fallback(self, origin: Dict, destination: Dict,
                            vehicle: Dict, preferences: Dict) -> Dict[str, Any]:
        """Fallback route planning with basic straight-line route."""
        logging.info('[NavigationTool] Using fallback route planning')
        
        # Get coordinates
        origin_coords = self._get_coordinates(origin)
        dest_coords = self._get_coordinates(destination)
        
        if not origin_coords or not dest_coords:
            raise ValueError("Could not resolve coordinates for origin or destination")
        
        # Create simple straight-line route (for MVP)
        route_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [origin_coords['lon'], origin_coords['lat']],
                            [dest_coords['lon'], dest_coords['lat']]
                        ]
                    },
                    "properties": {
                        "name": "Route",
                        "description": "Fallback straight-line route"
                    }
                }
            ]
        }
        
        # Calculate approximate distance and duration
        distance_km = self._haversine_distance(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )
        
        # Rough time estimate (assuming 50 km/h average)
        duration_min = (distance_km / 50.0) * 60
        
        stats = {
            'distance_km': distance_km,
            'duration_min': duration_min,
            'ascent_m': 0,  # Not calculated in fallback
            'descent_m': 0  # Not calculated in fallback
        }
        
        return {
            'route': route_geojson,
            'stats': stats
        }
    
    def _get_coordinates(self, location: Dict) -> Optional[Dict[str, float]]:
        """Extract coordinates from location object."""
        if 'lat' in location and 'lon' in location:
            return {'lat': float(location['lat']), 'lon': float(location['lon'])}
        
        # TODO: Implement geocoding for address strings
        if 'address' in location:
            logging.warning(f'[NavigationTool] Geocoding not implemented for: {location["address"]}')
            return None
        
        return None
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        import math
        
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _analyze_route_warnings(self, route_geojson: Dict, vehicle: Dict) -> List[Dict[str, Any]]:
        """Analyze route for potential warnings and restrictions."""
        warnings = []
        
        # For MVP, add some sample warnings based on vehicle specs
        if vehicle['height_m'] > 3.0:
            warnings.append({
                'type': 'height_restriction',
                'message': f'Vehicle height {vehicle["height_m"]}m may encounter low bridges',
                'segment_ref': 'general',
                'severity': 'warning'
            })
        
        if vehicle['width_m'] > 2.2:
            warnings.append({
                'type': 'width_restriction', 
                'message': f'Vehicle width {vehicle["width_m"]}m may have issues on narrow roads',
                'segment_ref': 'general',
                'severity': 'info'
            })
        
        if vehicle['weight_tons'] > 3.5:
            warnings.append({
                'type': 'weight_restriction',
                'message': f'Vehicle weight {vehicle["weight_tons"]}t may require special routing',
                'segment_ref': 'general', 
                'severity': 'warning'
            })
        
        # TODO: Implement real OSM-based analysis
        logging.debug(f'[NavigationTool] Generated {len(warnings)} warnings for route')
        
        return warnings
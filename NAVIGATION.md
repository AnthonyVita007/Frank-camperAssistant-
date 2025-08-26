# Frank Camper Assistant - MCP Navigation Feature

## Overview

The MCP (Model Context Protocol) Navigation feature adds offline-first route planning capabilities to Frank Camper Assistant with special considerations for camper/RV vehicles.

## Features

- **Offline-first navigation**: Works without internet connection using fallback routing
- **Camper-specific warnings**: Analyzes routes for height, width, weight restrictions
- **Natural language interface**: Italian language navigation commands
- **Dual interface modes**: Visual maps in User Mode, text-only in Debug Mode
- **KITT-themed UI**: Consistent with the retro-futuristic design aesthetic

## Navigation Commands

The system recognizes various Italian navigation commands:

- `"Portami a Roma"` - Take me to Rome
- `"vai a Milano"` - Go to Milan
- `"navigazione per Firenze"` - Navigation to Florence
- `"come arrivo a Venezia"` - How do I get to Venice
- `"strada per Napoli evitando pedaggi"` - Route to Naples avoiding tolls
- `"percorso verso Bologna senza autostrade"` - Route to Bologna without highways

## Supported Preferences

- `evitando pedaggi` / `senza pedaggi` - Avoid tolls
- `evitando autostrade` / `senza autostrade` - Avoid highways  
- `evitando traghetti` / `senza traghetti` - Avoid ferries

## Supported Cities (Geocoding Database)

- Roma (Rome)
- Milano (Milan)
- Napoli (Naples)
- Firenze (Florence)
- Venezia (Venice)
- Torino (Turin)
- Bologna
- Genova (Genoa)
- Palermo
- Bari

## Configuration

Add to `config.ini`:

```ini
[navigation]
# Router backend: graphhopper | valhalla | none
ROUTER = none
ROUTER_URL = http://localhost:8989
MBTILES_PATH = /data/tiles/country.mbtiles
DEFAULT_VEHICLE = camper
```

## Vehicle Specifications (Default Camper Profile)

- **Width**: 2.3 meters
- **Height**: 3.1 meters  
- **Length**: 7.5 meters
- **Weight**: 3.5 tons

## Route Warnings

The system analyzes routes and provides warnings for:

- **Height restrictions**: Bridges or tunnels with low clearance
- **Width restrictions**: Narrow roads unsuitable for wide vehicles
- **Weight restrictions**: Roads with weight limits
- **Access restrictions**: ZTL zones, HGV restrictions

## Backend Architecture

### MCP Tool Structure

```
backend/mcp/
├── __init__.py
├── mcp_tool.py           # Base MCPTool class and ToolResult
└── tools/
    ├── __init__.py
    └── navigation_tool.py # NavigationTool implementation
```

### Key Classes

- **MCPTool**: Abstract base class for all MCP tools
- **ToolResult**: Structured result with SUCCESS/ERROR/WARNING/INFO types
- **NavigationTool**: Navigation-specific implementation

### Integration Points

1. **AIHandler**: Detects navigation intents and invokes NavigationTool
2. **CommunicationHandler**: Emits navigation actions via Socket.IO
3. **Frontend**: Renders maps (User Mode) or text logs (Debug Mode)

## Frontend Implementation

### User Mode
- Leaflet map integration for route visualization
- KITT-themed navigation interface with warnings panel
- Toggle between tiles and navigation views

### Debug Mode  
- Text-only navigation output
- Route statistics and warnings displayed as log entries

## Offline Routing Backends

### GraphHopper (Planned)
- Professional routing engine with truck profiles
- Supports vehicle-specific routing constraints
- Requires local OSM data and server setup

### Valhalla (Planned)
- Open-source routing engine
- Advanced truck routing capabilities
- Supports complex vehicle restrictions

### Fallback Mode (Current)
- Simple straight-line distance calculation
- Basic vehicle warning generation
- No dependency on external routing services

## Example Usage

```python
from backend.mcp.tools.navigation_tool import NavigationTool

# Initialize navigation tool
nav_tool = NavigationTool()

# Execute navigation request
params = {
    'destination': {'lat': 41.9028, 'lon': 12.4964, 'address': 'Roma, Italia'},
    'preferences': {'avoid_tolls': True}
}

result = nav_tool.execute(params)
print(f"Route: {result.data['stats']}")
print(f"Warnings: {len(result.data['warnings'])}")
```

## Socket.IO Events

### Backend → Frontend

- `backend_action` with `action: "open_navigator"` - Switch to navigation mode
- `backend_action` with `action: "render_route"` - Display route on map
- `backend_response` - Standard AI response with navigation confirmation

### Event Payloads

```javascript
// Open navigator
{
  "action": "open_navigator"
}

// Render route
{
  "action": "render_route", 
  "data": {
    "route": {/* GeoJSON FeatureCollection */},
    "warnings": [
      {
        "type": "height_restriction",
        "message": "Vehicle height 3.1m may encounter low bridges",
        "severity": "warning"
      }
    ],
    "stats": {
      "distance_km": 476.9,
      "duration_min": 572,
      "ascent_m": 0,
      "descent_m": 0
    }
  }
}
```

## Testing

Run the navigation test script:

```bash
python test_navigation.py
```

This demonstrates all navigation functionality without requiring external dependencies.

## Future Enhancements

1. **Real Offline Routing**: Integration with GraphHopper/Valhalla
2. **Enhanced Geocoding**: Support for addresses, POIs, coordinates
3. **Route Optimization**: Multiple waypoints, route alternatives
4. **Detailed Warnings**: Real OSM-based restriction analysis
5. **GPS Integration**: Current location detection
6. **Voice Navigation**: Turn-by-turn guidance
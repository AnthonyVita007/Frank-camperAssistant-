# Frank Camper Assistant - AI Development Guide

This document guides AI agents on effectively working with the Frank Camper Assistant codebase - an offline-first AI assistant designed for RV/camper integration.

## Architecture Overview

- **Core Pattern**: Hybrid architecture combining local and cloud capabilities
  - Local LLM (Ollama) handles critical offline functions
  - Cloud services (Google APIs) enhance functionality when online
  - Main controller (`backend/main_controller.py`) orchestrates all services
  - Flask + WebSocket server (`app.py`) manages client communication

## Key Files and Components

- `app.py`: Application entry point and server initialization
- `backend/main_controller.py`: Central event orchestrator ("Director")
- `frontend/templates/index.html`: Main UI interface
- `frontend/static/{css,js}/`: UI assets following the KITT-inspired design system

## Development Workflows

### Local Development Setup

1. Install Python dependencies: `pip install -r requirements.txt`
2. Configure local LLM models using Ollama
3. Start the Flask development server through `app.py`

### Event Handling Pattern

1. WebSocket events flow: Frontend → `app.py` → `main_controller.py` → Services
2. New events should be registered in `main_controller.py` using the `@socketio_instance.on()` decorator
3. Event handlers emit responses using `emit('backend_response', data)`

## Project-Specific Conventions

### Code Organization
- Backend logic is modularized in `backend/` directory
- Frontend follows a classic static/templates Flask structure
- Configuration lives in `config.ini`

### Design System
- UI follows a retrofuturistic "KITT" aesthetic
- Color palette: 
  - Primary: Black (`#000000`)
  - Accents: Red (`#FF0000`), Amber (`#FFBF00`), Cyan (`#00FFFF`)
- Interface elements use monospace fonts (e.g., `VT323`)

## Integration Points

1. Hardware Integration
   - OBD-II via Bluetooth for vehicle data
   - GPS module for positioning
   - LED scanner for status indication

2. AI Services
   - Local LLM orchestration via Ollama
   - Google Cloud APIs for enhanced STT/TTS
   - RAG system for local document knowledge

## Common Tasks

### Adding New Features
1. Implement service logic in appropriate backend module
2. Register event handlers in `main_controller.py`
3. Add corresponding frontend UI elements following KITT design system

### Testing
- Ensure offline functionality works without cloud services
- Test both voice and touch interface paths
- Verify WebSocket event flow end-to-end

## Development Guidelines

1. Follow the "offline-first" philosophy - critical features must work without internet
2. Maintain multimodal support (voice + touch) for all features
3. Keep KITT-inspired design language consistent across UI changes
4. Document all WebSocket events and their data structures

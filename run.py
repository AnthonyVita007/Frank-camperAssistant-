"""
----------------------------------------------------------------------------------------------------
### run.py - Configurable Flask Server Launch ###
This file provides environment-variable based configuration for Flask server settings,
particularly for threading and reloader options which affect AI stability on Windows.
----------------------------------------------------------------------------------------------------
"""

import os
import logging
from app import app, socketio, HOST, PORT, DEBUG

def get_env_bool(name: str, default: bool = True) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(name, '1' if default else '0').lower()
    return value in ('1', 'true', 'yes', 'on')

def main():
    """Main entry point with configurable server settings."""
    
    # Read environment variables for server configuration
    use_reloader = get_env_bool('FLASK_USE_RELOADER', True)
    threaded = get_env_bool('FLASK_THREADED', True)
    
    # Log the configuration being used
    logging.info("=" * 60)
    logging.info("Frank Camper Assistant - Server Configuration")
    logging.info("=" * 60)
    logging.info(f"Host: {HOST}")
    logging.info(f"Port: {PORT}")
    logging.info(f"Debug: {DEBUG}")
    logging.info(f"Use Reloader: {use_reloader}")
    logging.info(f"Threaded: {threaded}")
    logging.info("=" * 60)
    
    if not use_reloader:
        logging.info("Reloader disabled - recommended for AI stability on Windows")
    if not threaded:
        logging.info("Threading disabled - single-threaded mode for maximum stability")
    
    try:
        # Start the server with the configured settings
        socketio.run(
            app,
            host=HOST,
            port=PORT,
            debug=DEBUG,
            use_reloader=use_reloader,
            threaded=threaded,
            allow_unsafe_werkzeug=True if DEBUG else False
        )
    except KeyboardInterrupt:
        logging.info("Server shutdown requested by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        raise

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
# =============================================================================
# OSINT OA - Flask Application Entrypoint
# =============================================================================
"""
Main Flask application entrypoint.

Run with:
    python app.py
    
Or with Flask CLI:
    flask run
"""

import asyncio
import logging
import os
import threading
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import config
from db import init_db
from api.routes import api

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.DEBUG if config.FLASK_DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Factory
# =============================================================================

def create_app() -> Flask:
    """
    Create and configure the Flask application.
    
    Returns:
        Configured Flask app
    """
    # Create Flask app
    app = Flask(
        __name__,
        static_folder='frontend',
        static_url_path=''
    )
    
    # Load configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.FLASK_DEBUG
    
    # Enable CORS for API routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register API blueprint
    app.register_blueprint(api)
    
    # Initialize database on first request
    with app.app_context():
        try:
            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    # Import and register LangChain agents
    try:
        from agents.registry import register_all_agents
        register_all_agents()
        logger.info("LangChain OSINT agents registered")
    except Exception as e:
        logger.warning(f"Failed to load LangChain agents: {e}")
    
    # Telegram MCP is handled on-demand by ConsolidatorAgent
    # The MCP client spawns the server process for each request
    if config.TELEGRAM_CHAT_ID:
        logger.info("Telegram MCP publishing enabled (ConsolidatorAgent)")
    
    # Log configuration warnings
    warnings = config.validate()
    for warning in warnings:
        logger.warning(f"Config: {warning}")
    
    # ==========================================================================
    # Frontend Routes
    # ==========================================================================
    
    @app.route('/')
    def index():
        """Serve the main frontend page."""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files from frontend folder."""
        return send_from_directory(app.static_folder, path)
    
    # ==========================================================================
    # Error Handlers
    # ==========================================================================
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors."""
        return {"error": "Not found"}, 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        logger.error(f"Server error: {e}")
        return {"error": "Internal server error"}, 500
    
    return app


# =============================================================================
# Main
# =============================================================================

# Create app instance
app = create_app()


# =============================================================================
# Telegram Listener Background Thread
# =============================================================================

def start_telegram_listener():
    """
    Start the Telegram listener in a background thread.
    
    Only starts if Telegram credentials are configured and TELEGRAM_LISTENER_ENABLED=true.
    
    Note: For development, it's recommended to run the listener separately or use
    production mode with supervisord to avoid SQLite session conflicts.
    """
    # Check if listener is explicitly enabled
    listener_enabled = os.environ.get('TELEGRAM_LISTENER_ENABLED', 'false').lower() == 'true'
    
    if not listener_enabled:
        logger.info("Telegram listener disabled (set TELEGRAM_LISTENER_ENABLED=true to enable)")
        return
    
    # Check if Telegram is configured
    tg_app_id = os.environ.get('TG_APP_ID')
    tg_api_hash = os.environ.get('TG_API_HASH')
    target_dialog = os.environ.get('TELEGRAM_TARGET_DIALOG')
    
    if not tg_app_id or not tg_api_hash:
        logger.info("Telegram credentials not configured, listener not started")
        logger.info("Set TG_APP_ID and TG_API_HASH to enable Telegram listener")
        return
    
    if not target_dialog:
        logger.info("TELEGRAM_TARGET_DIALOG not set, listener not started")
        return
    
    def run_listener_thread():
        """Run the listener in its own event loop."""
        try:
            # Import here to avoid issues if Telethon not installed
            from integrations.telegram.listener import run_listener
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            logger.info("Starting Telegram listener in background thread...")
            loop.run_until_complete(run_listener())
        except ImportError as e:
            logger.error(f"Failed to import TelegramListener: {e}")
        except Exception as e:
            logger.error(f"Telegram listener error: {e}")
    
    # Start listener in daemon thread
    listener_thread = threading.Thread(target=run_listener_thread, daemon=True)
    listener_thread.start()
    logger.info("Telegram listener thread started")


if __name__ == '__main__':
    # Ensure data directory exists
    config.ensure_data_dir()
    
    # Start Telegram listener in background (if configured)
    start_telegram_listener()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting OSINT OA on {host}:{port}")
    logger.info(f"Database: {config.DATABASE_PATH}")
    logger.info(f"Debug mode: {config.FLASK_DEBUG}")
    
    app.run(
        host=host,
        port=port,
        debug=config.FLASK_DEBUG
    )

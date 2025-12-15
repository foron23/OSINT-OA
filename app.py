#!/usr/bin/env python3
# =============================================================================
# OSINT News Aggregator - Flask Application Entrypoint
# =============================================================================
"""
Main Flask application entrypoint.

Run with:
    python app.py
    
Or with Flask CLI:
    flask run
"""

import logging
import os
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


if __name__ == '__main__':
    # Ensure data directory exists
    config.ensure_data_dir()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting OSINT News Aggregator on {host}:{port}")
    logger.info(f"Database: {config.DATABASE_PATH}")
    logger.info(f"Debug mode: {config.FLASK_DEBUG}")
    
    app.run(
        host=host,
        port=port,
        debug=config.FLASK_DEBUG
    )

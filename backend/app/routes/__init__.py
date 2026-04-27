"""
Routes package - API endpoints for ISE AI
"""

from .dashboard_routes import register_dashboard_routes
from .training_routes import register_training_routes


def register_all_routes(app):
    """Register all routes with Flask app"""
    register_dashboard_routes(app)
    register_training_routes(app)

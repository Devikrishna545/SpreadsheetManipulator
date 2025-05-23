"""
API Endpoints module
-----------------
Defines RESTful API endpoints for the application
"""

from flask import Blueprint, jsonify

# Blueprint for API routes
api_bp = Blueprint('api', __name__)


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Returns:
        flask.Response: JSON response with health status
    """
    return jsonify({
        'status': 'ok',
        'version': '0.1.0'
    })


# Additional API endpoints can be added here
# For now, the main app handles most functionality directly

"""
API Endpoints module
-----------------
Defines RESTful API endpoints for the application
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

# Blueprint for API routes
api_bp = Blueprint('api', __name__)


@api_bp.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    
    Returns:
        Dict[str, Any]: Health status
    """
    return jsonify({
        'status': 'ok',
        'version': '0.1.0'
    })


# Additional API endpoints can be added here
# For now, the main app handles most functionality directly

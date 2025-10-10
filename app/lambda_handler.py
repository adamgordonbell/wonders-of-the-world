"""
Lambda handler for the Flask application.

This module provides the AWS Lambda handler function that wraps the Flask app
using serverless-wsgi to handle API Gateway events.
"""

import serverless_wsgi
from app import app


def handler(event, context):
    """
    AWS Lambda handler function.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    return serverless_wsgi.handle_request(app, event, context)

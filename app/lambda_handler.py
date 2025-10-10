"""
Lambda handler for Flask application using serverless-wsgi.
"""
import serverless_wsgi
from app import app

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)

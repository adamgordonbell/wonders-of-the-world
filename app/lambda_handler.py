"""
Lambda handler for the Flask application using Mangum.
"""

from mangum import Mangum
from app import app

# Create the Lambda handler
handler = Mangum(app, lifespan="off")

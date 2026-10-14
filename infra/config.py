"""Configuration file for Pulumi infrastructure deployment."""

import os
import pulumi
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# MongoDB Atlas configuration
MONGODB_ATLAS_PROJECT_ID = os.getenv("MONGODB_ATLAS_PROJECT_ID")
if not MONGODB_ATLAS_PROJECT_ID:
    raise ValueError("MONGODB_ATLAS_PROJECT_ID environment variable is required")

MONGODB_ATLAS_PUBLIC_KEY = os.getenv("MONGODB_ATLAS_PUBLIC_KEY")
MONGODB_ATLAS_PRIVATE_KEY = os.getenv("MONGODB_ATLAS_PRIVATE_KEY")

# Database configuration
VECTOR_DATABASE = "ww"
VECTOR_COLLECTION = "facts"
VECTOR_USER = "wondersuser"
VECTOR_PASSWORD = pulumi.Config().get_secret("mongodb-password") or pulumi.Output.secret(
    os.getenv("MONGODB_PASSWORD", "ChangeMe123!")
)

# Get current IP address for MongoDB access list
IP_ADDRESS = os.getenv("IP_ADDRESS")
if not IP_ADDRESS:
    import requests
    try:
        IP_ADDRESS = requests.get('https://api.ipify.org', timeout=5).text
    except:
        IP_ADDRESS = "0.0.0.0"

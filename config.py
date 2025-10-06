"""
This module handles the configuration for deploying MongoDB Atlas resources using Pulumi.

It checks that the variables are configured correctly. These should be set via the
"pulumi config set" commands. However, an .env file can also be provided.
If an IP address is not set, the module dynamically fetches it using
the "get_public_ip" function.

Environment Variables:
- MONGODB_ATLAS_PROJECT_ID: The MongoDB Atlas project ID where resources will be created.
- MONGODB_ATLAS_PUBLIC_KEY: The public key for MongoDB Atlas API authentication.
- MONGODB_ATLAS_PRIVATE_KEY: The private key for MongoDB Atlas API authentication.
- IP_ADDRESS: The public IP address to be used for accessing MongoDB Atlas resources.
- VECTOR_DATABASE: The name of the MongoDB database to store vector data.
- VECTOR_COLLECTION: The name of the MongoDB collection to store vector data.
- VECTOR_USER: The username for accessing the MongoDB vector database.
- VECTOR_PASSWORD: The password for accessing the MongoDB vector database.

Functions:
- get_public_ip: Fetches the public IP address dynamically if not set in the environment variables.
"""
# Standard library imports
import os
import sys  # Used for process exit handling

# Third-party imports
from dotenv import load_dotenv  # Loads environment variables from .env file
from pulumi import Config

# Local application imports
from utils import get_public_ip  # Function to fetch public IP address


# Create a Config object
pulumi_config = Config()
atlas_config = Config("mongodbatlas")

# Load environment variables from .env file
load_dotenv()

# MongoDB Atlas project where the resources will be created
MONGODB_ATLAS_PROJECT_ID = pulumi_config.get('mongodbatlas_projectId') or os.getenv("MONGODB_ATLAS_PROJECT_ID")
if not MONGODB_ATLAS_PROJECT_ID:
    raise Exception(
        "❌ Missing MONGODB_ATLAS_PROJECT_ID.\n"
        "Set it in your environment or Pulumi config.\n"
    )


# If your MongoDB Atlas Organization has
# "Require IP Access List for the Atlas Administration API" enabled,
# ensure that the Pulumi Cloud IPs are allowed under your programmatic
# API key' access list.
# Note: This security feature is optional and is ON by default.
#
# For more details, refer to:
# https://tinyurl.com/atlas-api-ips
# https://tinyurl.com/pulumi-cloud-ips
# PULUMI_CLOUD_IP_ACCESS_LIST = [
#     "34.208.94.47/32",
#     "34.212.116.224/32",
#     "44.241.59.217/32",
#     "52.40.198.20/32"
# ]


# MongoDB Atlas API keys for authentication
if  not (atlas_config.get("publicKey") or os.getenv("MONGODB_ATLAS_PUBLIC_KEY") ) or \
    not (atlas_config.get_secret("privateKey") or os.getenv("MONGODB_ATLAS_PRIVATE_KEY") ):
    print(
        "❌ Missing MongoDB Atlas API keys.\n"
        "[Preferred] Please set it via\n"
        "pulumi config set mongodbatlas:publicKey <publicKey>\n"
        "pulumi config set mongodbatlas:privateKey --secret  <privateKey>\n"
        "[Alternative] Please add entries in your .env file as\n"
        "MONGODB_ATLAS_PUBLIC_KEY and MONGODB_ATLAS_PRIVATE_KEY.\n"
        "Need keys? Follow these steps to create them: 👉\n"
        "https://tinyurl.com/atlas-keys"
    )
    sys.exit(1)

# Retrieve the public IP address or fetch dynamically if not set
IP_ADDRESS = pulumi_config.get("mongodbatlas_ip_address") or os.getenv("IP_ADDRESS", get_public_ip())
if not IP_ADDRESS:
    print(
        "❌ Missing IP_ADDRESS.\n"
        "[Preferred] Please set it via\n"
        "pulumi config set mongodbatlas_ip_address <ipAddress>\n"
        "[Alternative] Please add an entry in your .env file\n"
        "or ensure network connectivity to dynamically fetch it."
    )
    sys.exit(1)

# Fetch variables or use default values
VECTOR_DATABASE = pulumi_config.get("vector_database") or os.getenv("VECTOR_DATABASE", "ww")
VECTOR_COLLECTION = pulumi_config.get("vector_collection") or os.getenv("VECTOR_COLLECTION", "facts")
VECTOR_USER = pulumi_config.get("vector_user") or os.getenv("VECTOR_USER", "vector-user")
VECTOR_PASSWORD = pulumi_config.get_secret("vector_password") or os.getenv("VECTOR_PASSWORD", "v3ct0rp4ssw0rd")  # For demo purposes only

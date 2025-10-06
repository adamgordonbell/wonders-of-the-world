"""
helpers.py

This module provides helper functions for interacting with external services and databases.

1. `get_public_ip`: Fetches the public IP address of the machine using the ipify API.

Dependencies:
    - requests: Used for making HTTP requests to external APIs.

Usage:
    - Use `get_public_ip` to retrieve the machine's public IP address.
"""

import requests

def get_public_ip():
    """
    Retrieves the public IP address of the machine using the ipify API.

    This function makes a request to the ipify API (https://api.ipify.org) to fetch the public
    IP address of the machine. If the request is successful, it returns the IP address as a string.
    In case of an error (such as a timeout or failed request), it logs the error and returns None.

    Returns:
        str: The public IP address of the machine, or None if an error occurred.
    """
    try:
        # Use ipify API to get the public IP address
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data["ip"]
    except requests.exceptions.Timeout as e:
        print(f"Error timeout fetching public IP: {e}")
        return None
    except requests.RequestException as e:
        print(f"Error retrieving public IP: {e}")
        return None

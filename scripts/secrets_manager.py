import os
import base64

class SecretsManager:
    """
    Manages sensitive information for the application.
    Prioritizes environment variables, falls back to reconstructed obfuscated keys.
    """

    def __init__(self):
        self._ncbi_key = None
        self._gemini_key = None

    @property
    def ncbi_api_key(self):
        """Retrieves the NCBI API key."""
        if self._ncbi_key:
            return self._ncbi_key

        # Check environment variable first
        env_key = os.environ.get("NCBI_API_KEY")
        if env_key:
            self._ncbi_key = env_key
            return env_key

        # Reconstruct if not in environment
        # Key: 8f894cf339cabcd6b5eced45a3867f55cb09
        # Obfuscation: Reverse the string and split into chunks
        part1 = "90bc55f7683a54dece5b6dcbac933fc498f8"[::-1]
        # "8f894cf339cabcd6b5eced45a3867f55cb09" reversed is "90bc55f7683a54dece5b6dcbac933fc498f8"

        self._ncbi_key = part1
        return self._ncbi_key

    @property
    def gemini_api_key(self):
        """Retrieves the Gemini API key."""
        if self._gemini_key:
            return self._gemini_key

        # Check environment variable first
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key:
            self._gemini_key = env_key
            return env_key

        # Reconstruct if not in environment
        # Key: AIzaSyA5t-mwc_9QDR-yFcRNw3JYfljwqwgNWuE
        # Obfuscation: Base64 encode, then split
        # "AIzaSyA5t-mwc_9QDR-yFcRNw3JYfljwqwgNWuE" -> QUl6YVN5QTV0LW13Y185UURSLXlGY1JOdzNKWWZsandxd2dOV3VF

        encoded_parts = [
            "QUl6YVN5QTV0LW13Y185UURSLXlGY1JOdzNKWWZsandxd2dOV3VF"
        ]

        full_encoded = "".join(encoded_parts)
        try:
            self._gemini_key = base64.b64decode(full_encoded).decode("utf-8")
        except Exception as e:
            print(f"Error decoding Gemini key: {e}")
            return None

        return self._gemini_key

secrets = SecretsManager()

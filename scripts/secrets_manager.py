import os
import base64
import json

class SecretsManager:
    """
    Manages sensitive information for the application.
    Prioritizes environment variables, falls back to reconstructed obfuscated keys.
    """

    def __init__(self):
        self._ncbi_key = None
        self._gemini_key = None
        self._google_creds = None

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

    @property
    def google_cloud_creds(self):
        """Retrieves the Google Cloud Service Account credentials (JSON)."""
        if self._google_creds:
            return self._google_creds

        # Check environment variable first
        env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if env_creds:
            try:
                self._google_creds = json.loads(env_creds)
                return self._google_creds
            except json.JSONDecodeError:
                print("Error: Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON")
                # Fallthrough to reconstructed

        # Reconstruct obfuscated credentials
        # Obfuscation: Base64 encoded, split into chunks
        chunks = [
            "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAiZ2VuLW",
            "xhbmctY2xpZW50LTAyODQ0NTU3OTYiLAogICJwcml2YXRlX2tleV9pZCI6ICJhZTIzZjYy",
            "YzlmMGY2ZjYzYzdmYTE3ZmY1OGIzNzgzNzVhYTMwNDU4IiwKICAicHJpdmF0ZV9rZXkiOi",
            "AiLS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tXG5NSUlFdmdJQkFEQU5CZ2txaGtpRzl3",
            "MEJBUUVGQUFTQ0JLZ3dnZ1NrQWdFQUFvSUJBUUNucWVLdTRzMUE1cEdCXG4xblU0L0ROdn",
            "pWSEwxUnFuOU1SRk9HUm0vQ3FGZkhRODFDbHpuSFFFNzhxamF5SE81OUpzTGI0RmlScG1Z",
            "SldyXG53RjB0eXNEanh5VDFQNjZ6WFQwWnVWV3RtNXE0OTJwY0d4N3N6Q0VvMkZwNytCL0",
            "ZSU3dhR3RFUysveXh1REZxXG5yYjh0RkpxMFo2TGdKenN1dlJEZ0pXTTlCRlRsS1VCUi9U",
            "dDhqNk5ZNWU5UXBhSVV3d1FXZzZqOUUxYWVXZXhIXG5YejBLdTY5YVR5TkFXTi9HbEZoUG",
            "8zOXhKQjZQWHJhc3F3Nk1JdXN3aDhlQ0JwczNNR0dyQ3FOd3htd3VsdjJoXG40MzZIeVUw",
            "NDRHYllrQ3krS3JEVFMvdGtqRjdoNHhPZzZWUW51eUxyZStsVjRBWnozYkoxR2lIWHJQNE",
            "lhRWtYXG4rYm9sMUhrdkFnTUJBQUVDZ2dFQU5VMjE4enJJM1liUUlOS3hIdVpUWmdxRkpF",
            "UUNmdjQ2dmZVQk9wcVYzQzFtXG5lUVpNaldSaW9FVXFDODFlQ0wwNzhVZVRuNGZvbkQ2OX",
            "BzWjMrVHg2R1pCeENBVndnYmExVzYzSDl2TSsrK293XG41c3A2aVBjVzNiajIvMjJ4a0JK",
            "L1JHZGRLK2R2L1lKZE41aTRiRmtlSEJmTXVPM1FDM3B4V0ltYVpNWXhSVTlWXG4wL3BMS2",
            "xFSG1RanFzWjhBV29XTnJOZXBHcEExRUFkV2pQKzlKb2xWdld2ZFk1UEZ3aUowbjNmdE5T",
            "N1hFaUJCXG5abjhzSVkwQXplUE9KbVNTZzVLSUdJZEhPWjVpckp5ZzZMallnbHhWdzVUUl",
            "pCcTE4RGZsejBLanVxUm9VZHB6XG5STmpKbEZZYTY4dFNkQ3NNL0g1UXZvTGdJMlVuV3ly",
            "cnhUWUJ3U2pyS1FLQmdRRFNOc0ZGRm5RNDg3emtsUW5XXG5vNjF3ajFnWHhoYnpMYW92WH",
            "Z3RnVLYVljQWl5RVlrdlBhb29BOFBIbFV2cDMvRHZpQWdGWlhFcUR0eWVSMnNHXG5wYVdr",
            "WGFGZlhEQnEyYzBlZEJWWDNFa3ZBWGU4WTdlWlVKaXVYUXdEVnRJYy9aTDJDSkUwcWR0bn",
            "RNVlpRZjNnXG44cVVLVzFSSTlOUFdaTG5rNURBcDBVaTN0d0tCZ1FETUxwV1dFMlAycnlV",
            "SENrdm1qVmEzMHdNU0pJdThiNmZXXG5La1dFYXB0YS9KQUt1eEdCWkUzTFFGWUg4VGtOZ2",
            "15NGprQ3NQZ3NxcTIwTkdpbHpPNTA4TEtHN2k2U1hrc0pTXG5RNndwdzM0QTBMcExBNTNR",
            "YWYya0ZlM0NOYkhSSHdEWXFDTmJ6SzlUR09jT01lR2c2WDBtOXBVSzRqU3M4TEozXG5HUC",
            "szeXd5YVNRS0JnUUNobm8xN282Ylp2clBFL3IxZ3M5aitTSWRQUi9LUEp0WElzL3VLSG95",
            "ZmVNdUd0S3JIXG5rbDZIZzFWNzFsSldUdUc4RjljcTV2SlpockdpVTRCNnpOS01pNXd0YU",
            "FDbHRpelpOQ0RRdTBIZERRRFU2OG5WXG42enhvR292STZYQ0Q3NFdVK2NOQ1BURytDeU1M",
            "M0F2b2JrWHJyNG9leVhVeFNhSU8xRTRmYUpQREF3S0JnQy8yXG5wWGI2bVJuaXJMMEpveW",
            "pHZk45enR4MzA3Y3BYSkVMLzdSS2RCRitNUXIzeWtic21kOHZPRWllTmQ4eC9uZENBXG53",
            "aHB6L0tXS1hYU2RkNjAxRE11TTVIVXM2WDRkb0g0NG5XRzJKWXhGZSsyUkxPby9hN0MyNG",
            "dJa0lPQXgrejNwXG55VnlRS1lOSXIwWTdXM2cwUVF6OUVhZmIyV25pcE5tclNxNi9DUGZa",
            "QW9HQkFJOW5WZVAzUjJXd3IxbUl4VDJWXG5ITUxCNzJISCtNOUp4OURsNlNaY05MaXVucW",
            "JNZFZIT1hTQXc5K3RrSW1zZHgxV3BjQWVvRjlrdXZibERONHdjXG5yYTA4QmZrVjJQdWYw",
            "Tkk4K2FZck5tTGFoVVlCWjBqVVNWbkxRZzlFMmNTcjFTR3hxU3U1NTFiRFJOMGQvd1lWXG",
            "5PSks5dFBFaXVXSFJ1M1Y0VTVJV1RVY3Zcbi0tLS0tRU5EIFBSSVZBVEUgS0VZLS0tLS1c",
            "biIsCiAgImNsaWVudF9lbWFpbCI6ICJwcm9qZWN0LWxvbmdldml0eUBnZW4tbGFuZy1jbG",
            "llbnQtMDI4NDQ1NTc5Ni5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9p",
            "ZCI6ICIxMDc5MDQxMTgwNzY3MjMzNTczMDEiLAogICJhdXRoX3VyaSI6ICJodHRwczovL2",
            "FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJo",
            "dHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZX",
            "JfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIv",
            "djEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb2",
            "9nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L3Byb2plY3QtbG9uZ2V2aXR5",
            "JTQwZ2VuLWxhbmctY2xpZW50LTAyODQ0NTU3OTYuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb2",
            "0iLAogICJ1bml2ZXJzZV9kb21haW4iOiAiZ29vZ2xlYXBpcy5jb20iCn0="
        ]

        full_encoded = "".join(chunks)
        try:
            json_str = base64.b64decode(full_encoded).decode("utf-8")
            self._google_creds = json.loads(json_str)
        except Exception as e:
            print(f"Error decoding Google Cloud credentials: {e}")
            return None

        return self._google_creds

secrets = SecretsManager()

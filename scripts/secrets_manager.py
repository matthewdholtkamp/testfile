import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SecretsManager:
    """
    Manages sensitive information for the pipeline.
    Uses ONLY environment variables or GitHub Secrets.

    SECURITY NOTE: Never hardcode API keys or credentials in source code.
    Set these via GitHub Secrets (for Actions) or local environment variables.

    Required environment variables:
        NCBI_API_KEY            - NCBI E-utilities API key
        GEMINI_API_KEY          - Google Gemini API key
        GOOGLE_APPLICATION_CREDENTIALS_JSON - GCP service account JSON (as string)
    """

    def __init__(self):
        self._ncbi_key = None
        self._gemini_key = None
        self._google_creds = None

    @property
    def ncbi_api_key(self):
        """Retrieves the NCBI API key from environment."""
        if self._ncbi_key:
            return self._ncbi_key

        key = os.environ.get("NCBI_API_KEY")
        if not key:
            logging.warning(
                "NCBI_API_KEY not set. PubMed requests will be rate-limited. "
                "Set it via: export NCBI_API_KEY=your_key or add to GitHub Secrets."
            )
            return None

        self._ncbi_key = key
        return key

    @property
    def gemini_api_key(self):
        """Retrieves the Gemini API key from environment."""
        if self._gemini_key:
            return self._gemini_key

        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            logging.error(
                "GEMINI_API_KEY not set. Claim extraction will fail. "
                "Set it via: export GEMINI_API_KEY=your_key or add to GitHub Secrets."
            )
            return None

        self._gemini_key = key
        return key

    @property
    def google_credentials(self):
        """Retrieves Google Cloud credentials from environment."""
        if self._google_creds:
            return self._google_creds

        # Option 1: JSON string in environment variable
        creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if creds_json:
            try:
                self._google_creds = json.loads(creds_json)
                return self._google_creds
            except json.JSONDecodeError:
                logging.error("Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON")
                return None

        # Option 2: Path to service account file
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            try:
                with open(creds_path, "r") as f:
                    self._google_creds = json.load(f)
                return self._google_creds
            except Exception as e:
                logging.error(f"Error reading credentials file: {e}")
                return None

        logging.warning(
            "No Google credentials found. Drive sync will be skipped. "
            "Set GOOGLE_APPLICATION_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS."
        )
        return None

    def validate(self):
        """Check that all required secrets are available. Returns dict of status."""
        return {
            "ncbi_api_key": bool(self.ncbi_api_key),
            "gemini_api_key": bool(self.gemini_api_key),
            "google_credentials": bool(self.google_credentials),
        }

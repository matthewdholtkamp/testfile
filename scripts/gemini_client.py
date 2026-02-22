import requests
import json
import logging
import os
import sys
import time
import random
import re

# Add script directory to path to allow imports
sys.path.append(os.path.dirname(__file__))

from secrets_manager import SecretsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")

ALLOWED_GEMINI_MODELS = {"gemini-2.5-flash-lite", "gemini-2.5-flash"}

class QuotaExhaustedException(Exception):
    """Exception raised when API quota is exhausted (limit: 0)."""
    pass

class GeminiClient:
    def __init__(self, model_name=None, fallback_models=None):
        secrets = SecretsManager()
        self.api_key = secrets.gemini_api_key
        if not self.api_key:
            raise ValueError("Gemini API key not found in secrets.")

        # Load config
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            extraction_config = config["extraction"]

            # Prioritize passed model_name, then config, then default
            self.model_name = model_name or extraction_config.get("gemini_model", "gemini-2.5-flash-lite")
            self.fallback_models = fallback_models or []

            self.temperature = extraction_config.get("temperature", 0.1)
            self.max_output_tokens = extraction_config.get("max_output_tokens", 4096)

            # Retry config
            self.max_attempts = 5
            self.base_backoff = 60.0
            self.max_sleep_total = 600.0

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def extract_claims(self, paper_data):
        """
        Extracts structured claims from a paper abstract using Gemini via REST API.
        Implements robust retry logic and model fallback.
        """
        prompt_text = self._construct_prompt(paper_data)

        # List of models to try: [primary, fallback1, fallback2, ...]
        models_to_try = [self.model_name] + self.fallback_models

        for model in models_to_try:
            try:
                logging.info(f"Extracting claims for PMID: {paper_data.get('pmid')} using {model}")
                result = self._generate_content_with_retry(prompt_text, model, paper_data.get('pmid'))
                if result:
                    return result
            except QuotaExhaustedException:
                logging.warning(f"Quota exhausted for model {model}. Trying next model if available.")
                continue
            except ValueError:
                raise
            except Exception as e:
                logging.error(f"Unexpected error with model {model}: {e}")
                # Depending on error type, might want to continue or stop.
                # For now, continue to next model.
                continue

        # If we reach here, all models failed
        logging.error(f"All models failed for PMID {paper_data.get('pmid')}. Returning quota_exhausted.")
        return {"error": "quota_exhausted", "reason": "all_models_failed"}

    def _generate_content_with_retry(self, prompt_text, model, pmid):
        """
        Generates content with a specific model, handling retries for 429 errors.
        Raises QuotaExhaustedException if limit is 0.
        """
        model = model.strip()
        if model not in ALLOWED_GEMINI_MODELS:
            raise ValueError(f"Model not allowed: {model}")

        url = f"{self.base_url}/{model}:generateContent"
        params = {"key": self.api_key}
        headers = {
            "Content-Type": "application/json",
            "Referer": "http://localhost"  # Required for this specific API key
        }

        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json"
            }
        }

        total_sleep = 0

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = requests.post(url, params=params, headers=headers, json=payload)

                if response.status_code == 200:
                    return self._parse_response(response.json(), pmid)

                if response.status_code == 429:
                    # Check for hard limit (limit: 0)
                    error_data = response.json().get("error", {})
                    message = error_data.get("message", "")

                    if "limit: 0" in message or "limit:0" in message:
                        logging.warning(f"Quota hard limit reached for {model}: {message}")
                        raise QuotaExhaustedException()

                    # Calculate delay
                    delay = self._calculate_retry_delay(response, attempt)

                    if total_sleep + delay > self.max_sleep_total:
                        logging.error(f"Max sleep time exceeded for {model}. Giving up.")
                        return None # Or raise

                    logging.warning(f"Rate limited (429) on {model}. Retrying in {delay:.2f}s (Attempt {attempt}/{self.max_attempts})")
                    time.sleep(delay)
                    total_sleep += delay
                    continue

                # Other errors
                logging.error(f"HTTP {response.status_code} for {pmid}: {response.text}")
                return None

            except requests.exceptions.RequestException as e:
                logging.error(f"Network error for {pmid}: {e}")
                return None

        logging.error(f"Max attempts reached for {model} on PMID {pmid}")
        return None

    def _calculate_retry_delay(self, response, attempt):
        """Calculates delay based on Backoff, Header, or JSON body."""
        # 1. Exponential Backoff
        backoff = self.base_backoff * (2 ** (attempt - 1))
        # Add jitter
        backoff += random.uniform(0, 1)

        # 2. Retry-After Header
        header_delay = 0
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                header_delay = float(retry_after)
            except ValueError:
                pass # parse error, ignore

        # 3. retryDelay in JSON
        json_delay = 0
        try:
            data = response.json()
            if "error" in data and "details" in data["error"]:
                for detail in data["error"]["details"]:
                    if "retryDelay" in detail:
                        # Format might be "3.5s"
                        d = detail["retryDelay"]
                        if d.endswith("s"):
                            json_delay = float(d[:-1])
        except Exception:
            pass

        return max(backoff, header_delay, json_delay)

    def _parse_response(self, result, pmid):
        """Parses the successful JSON response with robust fallback."""
        candidates = result.get("candidates", [])
        if not candidates:
            logging.warning(f"No candidates returned for {pmid}")
            return None

        text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
        original_text = text  # Keep for fallback

        # Step 1: Strip markdown code fences
        if "```" in text:
            # Handle ```json ... ``` or just ``` ... ```
            # We want to find the first occurrence of ``` and the next occurrence of ```
            match = re.search(r"```(?:\w+)?\s(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            else:
                # Fallback if regex doesn't match perfectly but ``` exists (e.g. unclosed)
                # Just try to remove lines starting with ```
                lines = text.split('\n')
                text = '\n'.join([line for line in lines if not line.strip().startswith('```')]).strip()

        # Step 2: Attempt json.loads(clean_text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Step 3: Attempt to parse substring between first { and last }
        try:
            start_index = text.find('{')
            end_index = text.rfind('}')
            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_str = text[start_index : end_index + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Step 4: Return fallback structure
        logging.error(f"Failed to parse JSON for {pmid}. Returning fallback.")
        return {
            "claims": [],
            "parse_error": True,
            "raw_snippet": original_text[:200]
        }

    def _construct_prompt(self, paper):
        return f"""
SYSTEM: You are a biomedical research extraction engine. Your job is to
extract ONLY factual claims that are explicitly stated in the provided
abstract. You must NEVER infer, extrapolate, or generate claims not
directly supported by the text. If the abstract does not contain
extractable quantitative claims, return an empty claims array.

USER: Extract structured research claims from the following paper abstract.

TITLE: {paper.get('title', '')}
DOI: {paper.get('doi', '')}
JOURNAL: {paper.get('journal', '')}
ABSTRACT: {paper.get('abstract', '')}

For each distinct claim in the abstract, extract a JSON object.
Return the result as a valid JSON object matching this schema:

{{
  "claims": [
    {{
      "claim_text": "One-sentence plain-English summary of the finding",
      "intervention": "Treatment/compound/condition tested. null if observational.",
      "target": "Biological target or endpoint measured",
      "direction": "increase | decrease | no_change | complex",
      "effect_size": "Quantitative effect as reported. null if not quantified.",
      "p_value": "As reported. null if not reported.",
      "confidence_interval": "As reported. null if not reported.",
      "species": "human | mouse | rat | primate | cell_line | drosophila | c_elegans | other:{{specify}}",
      "strain_or_population": "e.g. 'C57BL/6', 'healthy adults 60-75'",
      "tissue_or_system": "e.g. 'liver', 'whole blood', 'systemic'",
      "sample_size": "Total n as integer. null if not stated.",
      "study_design": "RCT | observational_cohort | case_control | cross_sectional | animal_intervention | in_vitro | meta_analysis | review",
      "duration": "Treatment/observation duration. null if not stated.",
      "domain_tags": ["epigenetic", "senescence", "mitochondrial", "nutrient_sensing", "stem_cell_ecm", "comparative", "cross_domain"],
      "novelty_flag": "novel | replication | extension | contradicts_prior",
      "limitations_noted": ["Limitations mentioned by the authors"]
    }}
  ],
  "paper_metadata": {{
    "study_type": "primary_research | review | meta_analysis | commentary | methods | case_report",
    "species_studied": ["All species in the study"],
    "aging_relevance": "direct | indirect | peripheral",
    "cross_domain_connections": ["Domains this paper bridges"],
    "key_methods": ["Major methods used"]
  }}
}}

RULES:
1. Extract ONLY claims explicitly stated in the abstract. Do not infer.
2. Qualitative findings: extract but set effect_size to null.
3. Reviews/meta-analyses: extract synthesized conclusions as claims.
4. Multiple experiments: extract each as a separate claim.
5. Observational findings: set intervention to null.
6. novelty_flag "novel" ONLY if authors explicitly state it is new.
   Default to "extension" if unclear.
7. Tag cross_domain_connections when findings span multiple domains.
8. Return valid JSON only. No markdown, no commentary.
"""

import requests
import json
import logging
import os
import sys

# Add script directory to path to allow imports
sys.path.append(os.path.dirname(__file__))

from secrets_manager import SecretsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")

class GeminiClient:
    def __init__(self):
        secrets = SecretsManager()
        self.api_key = secrets.gemini_api_key
        if not self.api_key:
            raise ValueError("Gemini API key not found in secrets.")

        # Load config
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            extraction_config = config["extraction"]
            self.model_name = extraction_config.get("gemini_model", "gemini-1.5-flash")
            self.temperature = extraction_config.get("temperature", 0.1)
            self.max_output_tokens = extraction_config.get("max_output_tokens", 4096)

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def extract_claims(self, paper_data):
        """
        Extracts structured claims from a paper abstract using Gemini via REST API.
        """
        prompt_text = self._construct_prompt(paper_data)

        logging.info(f"Extracting claims for PMID: {paper_data.get('pmid')} using {self.model_name} (T={self.temperature}, MaxTokens={self.max_output_tokens})")

        url = f"{self.base_url}/{self.model_name}:generateContent"
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
                "responseMimeType": "application/json" # Force JSON response
            }
        }

        try:
            response = requests.post(url, params=params, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()

            # Parse response
            # Candidates -> Content -> Parts -> Text
            candidates = result.get("candidates", [])
            if not candidates:
                logging.warning(f"No candidates returned for {paper_data.get('pmid')}")
                return None

            text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")

            # Clean up potential markdown code blocks if not handled by responseMimeType
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Error extracting claims for {paper_data.get('pmid')}: {e}")
            if e.response is not None:
                logging.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"Error extracting claims for {paper_data.get('pmid')}: {e}")
            return None

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

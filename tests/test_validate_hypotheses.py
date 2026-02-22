import unittest
import os
import json
import sys
import shutil
from unittest.mock import MagicMock, patch

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))
import validate_hypotheses
import pipeline_utils

class TestValidateHypotheses(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)
        self.config = {
            "_meta": {"version": "test"},
            "domains": {
                "senescence": {"key_biomarkers": ["p16", "il-6"], "biorxiv_keywords": []},
                "epigenetic": {"key_biomarkers": ["clock"], "biorxiv_keywords": []}
            },
            "validation": {
                "hypothesis_ledger_path": "tests/test_data/ledger.md",
                "scoring": {
                    "match_weights": {"domain_overlap": 0.45, "token_jaccard": 0.40, "entity_score": 0.15},
                    "match_threshold": 20,
                    "top_k": 3,
                    "composite_weights": {"match": 0.55, "evidence_quality": 0.45, "replication_modifier": 0.10, "contradiction_modifier": 0.35},
                    "evidence_quality_weights": {"evidence_strength": 0.50, "species_relevance": 0.25, "sample_size": 0.25}
                }
            }
        }
        self.ledger_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.config["validation"]["hypothesis_ledger_path"])

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        # ledger_path points to inside test_data if configured correctly in test,
        # but in setUp config uses "tests/test_data/ledger.md" relative to repo root.
        # Ensure cleanup if it was created outside test_data dir (unlikely with this setup but safe)
        if os.path.exists(self.ledger_path):
            try:
                os.remove(self.ledger_path)
            except OSError:
                pass

    def test_tier_c_fallback(self):
        # Ensure ledger file does not exist
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)

        hyps, tier = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(len(hyps), 6)
        self.assertEqual(tier, "C")
        self.assertEqual(hyps[0]["id"], "HYP-VAL-01")

    def test_tier_a_json_list(self):
        content = """
Some text
<!-- HYPOTHESIS_REGISTRY_JSON_START -->
[
  {"id": "HYP-A-01", "text": "Test A1", "domain": "senescence"}
]
<!-- HYPOTHESIS_REGISTRY_JSON_END -->
"""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            f.write(content)

        hyps, tier = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(tier, "A")
        self.assertEqual(len(hyps), 1)
        self.assertEqual(hyps[0]["id"], "HYP-A-01")

    def test_tier_a_json_object(self):
        content = """
<!-- HYPOTHESIS_REGISTRY_JSON_START -->
{
  "registry_version": "1.0",
  "hypotheses": [
    {"id": "HYP-A-02", "text": "Test A2", "domain": "epigenetic"}
  ]
}
<!-- HYPOTHESIS_REGISTRY_JSON_END -->
"""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            f.write(content)

        hyps, tier = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(tier, "A")
        self.assertEqual(len(hyps), 1)
        self.assertEqual(hyps[0]["id"], "HYP-A-02")

    def test_tier_b_markdown_minimal(self):
        content = """
# Ledger
- **[HYP-B-01]** Minimal Hypothesis
"""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            f.write(content)

        hyps, tier = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(tier, "B")
        self.assertEqual(len(hyps), 1)
        self.assertEqual(hyps[0]["id"], "HYP-B-01")
        self.assertEqual(hyps[0]["text"], "Minimal Hypothesis")
        self.assertEqual(hyps[0]["domain"], "unknown") # Default

    def test_tier_b_markdown_full(self):
        content = """
# Ledger
- **[HYP-B-02]** Full Hypothesis
  - Keywords: senolytic, p16
  - Domain tags: senescence, aging
  - Expected: target=IL-6 direction=decrease
  - Evidence FOR: PMID:123, PMID:456
  - Evidence AGAINST: PMID:789
"""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            f.write(content)

        hyps, tier = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(tier, "B")
        self.assertEqual(len(hyps), 1)
        h = hyps[0]
        self.assertEqual(h["id"], "HYP-B-02")
        self.assertEqual(h["keywords"], ["senolytic", "p16"])
        self.assertEqual(h["domain_tags"], ["senescence", "aging"])
        self.assertEqual(h["domain"], "senescence") # Primary inferred from config
        self.assertEqual(h["expected_effect"], [{"target": "IL-6", "direction": "decrease"}])
        self.assertEqual(h["evidence_for"], ["123", "456"])
        self.assertEqual(h["evidence_against"], ["789"])

    def test_tier_b_multiple_hyps(self):
        content = """
- **[HYP-1]** First
  - Domain tags: epigenetic
- **[HYP-2]** Second
  - Domain tags: senescence
"""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "w") as f:
            f.write(content)

        hyps, tier = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(len(hyps), 2)
        self.assertEqual(hyps[0]["domain"], "epigenetic")
        self.assertEqual(hyps[1]["domain"], "senescence")

    def test_scoring_logic(self):
        # Senolytic X / IL-6 / RCT / human / n=120 / senescence domain
        claim = {
            "claim_text": "Senolytic X reduces IL-6 levels in humans.",
            "domain_primary": "senescence",
            "study_design": "RCT",
            "species": ["human"],
            "sample_size": "n=120",
            "p_value": "0.01",
            "effect_size": "large",
            "novelty_flag": "extension",
            "contradiction_flags": {"contradicts_existing": False}
        }
        hypothesis = {
            "id": "HYP-TEST",
            "domain": "senescence",
            "text": "Senolytics reduce IL-6 and inflammation.",
            "keywords": ["senolytic", "il-6"]
        }

        match_score = validate_hypotheses.calculate_match_score(claim, hypothesis, self.config)
        self.assertGreater(match_score, 60)

    @patch('pipeline_utils.get_run_date_utc')
    @patch('pipeline_utils.get_results_dir')
    @patch('validate_hypotheses.glob.glob')
    @patch('validate_hypotheses.load_hypotheses')
    @patch('builtins.open')
    @patch('json.load')
    @patch('json.dump')
    @patch('os.rename')
    def test_process_claims_malformed_file(self, mock_rename, mock_json_dump, mock_json_load, mock_open, mock_load_hyps, mock_glob, mock_res_dir, mock_date):
        mock_date.return_value = ("2099", "01", "01")
        mock_res_dir.return_value = "/tmp/results"
        mock_glob.return_value = ["/tmp/claims/bad.json", "/tmp/claims/good.json"]

        # Mock Hyps
        mock_load_hyps.return_value = ([{"id": "HYP-1", "text": "test", "domain": "unknown"}], "C")

        # Mock JSON Load side effects
        # 1. bad.json raises JSONDecodeError
        # 2. good.json returns valid list
        mock_json_load.side_effect = [
            json.JSONDecodeError("Expecting value", "doc", 0),
            [{"input_paper": {"pmid": "123"}, "extracted_claims": {"claims": []}}]
        ]

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch('pipeline_utils.update_status'):
            with patch('pipeline_utils.print_handoff'):
                validate_hypotheses.process_claims(self.config)

                # Verify json.dump was called with correct data
                args, _ = mock_json_dump.call_args
                output_data = args[0]

                # Check run_errors
                self.assertEqual(len(output_data["run_errors"]), 1)
                self.assertEqual(output_data["run_errors"][0]["file"], "bad.json")
                self.assertIn("JSON Decode Error", output_data["run_errors"][0]["error"])

    @patch('pipeline_utils.get_run_date_utc')
    @patch('pipeline_utils.get_results_dir')
    @patch('validate_hypotheses.glob.glob')
    @patch('validate_hypotheses.load_hypotheses')
    @patch('builtins.open')
    @patch('json.load')
    @patch('json.dump')
    @patch('os.rename')
    def test_process_claims_malformed_paper(self, mock_rename, mock_json_dump, mock_json_load, mock_open, mock_load_hyps, mock_glob, mock_res_dir, mock_date):
        mock_date.return_value = ("2099", "01", "01")
        mock_res_dir.return_value = "/tmp/results"
        mock_glob.return_value = ["/tmp/claims/mixed.json"]

        mock_load_hyps.return_value = ([{"id": "HYP-1", "text": "test", "domain": "unknown"}], "C")

        # file has one bad paper (missing input_paper) and one good paper
        mock_json_load.side_effect = [[
            {"bad_key": "no input paper"},
            {"input_paper": {"pmid": "123"}, "extracted_claims": {"claims": []}}
        ]]

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch('pipeline_utils.update_status'):
            with patch('pipeline_utils.print_handoff'):
                validate_hypotheses.process_claims(self.config)

                args, _ = mock_json_dump.call_args
                output_data = args[0]

                self.assertEqual(len(output_data["run_errors"]), 1)
                self.assertEqual(output_data["run_errors"][0]["error"], "Missing input_paper")
                self.assertEqual(output_data["hypotheses_index"]["source_tier"], "C")

if __name__ == '__main__':
    unittest.main()

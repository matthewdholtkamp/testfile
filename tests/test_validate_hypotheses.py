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

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_tier_c_fallback(self):
        # Ensure ledger file does not exist
        ledger_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.config["validation"]["hypothesis_ledger_path"])
        if os.path.exists(ledger_path):
            os.remove(ledger_path)

        hyps = validate_hypotheses.load_hypotheses(self.config)
        self.assertEqual(len(hyps), 6)
        self.assertEqual(hyps[0]["id"], "HYP-VAL-01")

    def test_scoring_example(self):
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

        ev_strength = validate_hypotheses.calculate_evidence_strength(claim)
        self.assertEqual(ev_strength, 98) # 90 + 3 + 5

        sp_rel = validate_hypotheses.calculate_species_relevance(claim)
        self.assertEqual(sp_rel, 100)

        sz_score = validate_hypotheses.calculate_sample_size_score(claim)
        # log10(120)/3 * 100 = 69.3
        self.assertAlmostEqual(sz_score, 69.3, delta=1)

        rep_score = validate_hypotheses.calculate_replication_score(claim, 0)
        self.assertEqual(rep_score, 50)

        contra_score = validate_hypotheses.calculate_contradiction_score(claim, hypothesis)
        self.assertEqual(contra_score, 100)

        # Composite calculation check
        eq_w = self.config["validation"]["scoring"]["evidence_quality_weights"]
        eq = eq_w["evidence_strength"] * ev_strength + eq_w["species_relevance"] * sp_rel + eq_w["sample_size"] * sz_score

        cw = self.config["validation"]["scoring"]["composite_weights"]
        comp = cw["match"] * match_score + cw["evidence_quality"] * eq + cw["replication_modifier"] * (rep_score - 50) - (100 - contra_score) * cw["contradiction_modifier"]

        # ~76.5
        self.assertGreater(comp, 70)

    def test_unmatched_claim(self):
        claim = {
            "claim_text": "Something completely different.",
            "domain_primary": "physics",
        }
        hypothesis = {
            "id": "HYP-TEST",
            "domain": "senescence",
            "text": "Senolytics reduce IL-6.",
            "keywords": ["senolytic"]
        }
        match_score = validate_hypotheses.calculate_match_score(claim, hypothesis, self.config)
        self.assertLess(match_score, 20)

    @patch('validate_hypotheses.glob.glob')
    @patch('pipeline_utils.get_run_date_utc')
    def test_process_claims_empty(self, mock_date, mock_glob):
        mock_date.return_value = ("2099", "01", "01")
        mock_glob.return_value = []

        with patch('pipeline_utils.update_status') as mock_update:
            with patch('pipeline_utils.print_handoff') as mock_handoff:
                validate_hypotheses.process_claims(self.config)
                mock_update.assert_called_with("validate_hypotheses", "success", count=0, config=self.config)

    @patch('pipeline_utils.get_run_date_utc')
    @patch('pipeline_utils.get_results_dir')
    @patch('validate_hypotheses.glob.glob')
    @patch('validate_hypotheses.load_hypotheses')
    @patch('builtins.open') # Need to mock open for file reading and writing
    @patch('json.load')
    @patch('json.dump')
    @patch('os.rename')
    def test_process_claims_success(self, mock_rename, mock_json_dump, mock_json_load, mock_open, mock_load_hyps, mock_glob, mock_res_dir, mock_date):
        mock_date.return_value = ("2099", "01", "01")
        mock_res_dir.return_value = "/tmp/results"
        mock_glob.return_value = ["/tmp/claims/file1.json"]

        # Mock Hypothesis
        mock_load_hyps.return_value = [{
            "id": "HYP-TEST",
            "domain": "senescence",
            "text": "Senolytics reduce IL-6.",
            "keywords": ["senolytic"]
        }]

        # Mock Claim Input
        mock_json_load.side_effect = [
            # First call: load claim file
            [{
                "input_paper": {"pmid": "123"},
                "extracted_claims": {
                    "claims": [{
                        "claim_text": "Senolytics reduce IL-6.",
                        "domain_primary": "senescence",
                        "study_design": "RCT",
                        "species": ["human"],
                        "sample_size": "n=100"
                    }]
                }
            }]
        ]

        # Mock Open context manager
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch('pipeline_utils.update_status') as mock_update:
            with patch('pipeline_utils.print_handoff') as mock_handoff:
                validate_hypotheses.process_claims(self.config)

                # Check that json.dump was called (writing output)
                self.assertTrue(mock_json_dump.called)

                # Check status update
                mock_update.assert_called()
                args, kwargs = mock_update.call_args
                self.assertEqual(kwargs['count'], 1)

if __name__ == '__main__':
    unittest.main()

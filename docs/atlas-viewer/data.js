window.ATLAS_VIEWER_DATA = {
  "metadata": {
    "repo": {
      "repo_url": "https://github.com/matthewdholtkamp/testfile",
      "blob_base_url": "https://github.com/matthewdholtkamp/testfile/blob/main",
      "workflow_base_url": "https://github.com/matthewdholtkamp/testfile/actions/workflows",
      "actions_url": "https://github.com/matthewdholtkamp/testfile/actions"
    },
    "generated_from": {
      "index": "reports/mechanism_dossiers/mechanism_dossier_index_2026-03-28_013915.md",
      "chapter": "reports/atlas_chapter_draft/starter_atlas_chapter_draft_2026-03-28_013915.md",
      "chapter_synthesis": "reports/atlas_chapter_synthesis_draft/starter_atlas_chapter_synthesis_draft_2026-03-28_013915.md",
      "ledger": "reports/atlas_chapter_ledger/starter_atlas_chapter_evidence_ledger_2026-03-28_013915.csv",
      "workpack": "",
      "bridge": "reports/mechanism_dossiers/translational_bridge_2026-03-28_013915.csv",
      "release_manifest": "reports/atlas_release_manifest/atlas_release_manifest_2026-03-28_013915.json",
      "decision_brief": "",
      "idea_gate": "reports/idea_generation_gate/idea_generation_gate_2026-03-28_013915.json",
      "hypothesis_candidates": "reports/hypothesis_candidates/hypothesis_candidates_2026-03-28_013915.json",
      "synthesis": "reports/mechanistic_synthesis/mechanistic_synthesis_blocks_2026-03-28_013915.csv",
      "review_packet_index": "reports/mechanism_review_packets/mechanism_review_packet_index_2026-03-28_013915.md",
      "target_packet_index": "",
      "program_status": "reports/program_status/program_status_report_2026-03-28_013713.md",
      "chembl_template": "",
      "open_targets_template": "",
      "clinicaltrials_template": "reports/connector_candidate_manifest/templates/clinicaltrials_gov_import_template_2026-03-28_013712.csv",
      "preprint_template": "reports/connector_candidate_manifest/templates/biorxiv_medrxiv_import_template_2026-03-28_013712.csv",
      "tenx_template": "reports/connector_candidate_manifest/templates/tenx_genomics_import_template_2026-03-28_013712.csv"
    }
  },
  "summary": {
    "lead_mechanism": "Blood-Brain Barrier Dysfunction",
    "stable_rows": 5,
    "provisional_rows": 6,
    "blocked_rows": 5,
    "mechanism_count": 3,
    "top_priority": "",
    "idea_ready_now": 3,
    "breakthrough_ready_now": 1,
    "idea_almost_ready": 0
  },
  "mechanisms": [
    {
      "id": "blood-brain-barrier-dysfunction",
      "display_name": "Blood-Brain Barrier Dysfunction",
      "top_bullets": [
        "Canonical mechanism: `blood_brain_barrier_disruption`",
        "Promotion status: `near_ready`",
        "Promotion reason: atlas backbone is usable but still needs bounded cleanup or enrichment"
      ],
      "overview": [
        "Papers in packet: `25`",
        "Claim rows: `29`",
        "Source quality mix: `full_text_like` 20, `abstract_only` 5",
        "Action lanes: `core_atlas_candidate` 19, `upgrade_source` 5, `deepen_extraction` 1"
      ],
      "anchor_papers": [
        {
          "PMID": "41859452",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "SCFAs cross the BBB and inhibit HDACs to promote neuroprotection."
        },
        {
          "PMID": "41683989",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "TBI-induced BBB breakdown promotes neuroinflammation."
        },
        {
          "PMID": "41446731",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "rmTBI causes acute BBB disruption via downregulation of ZO-1 and claudin-5."
        },
        {
          "PMID": "41532955",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Neutrophil-derived exosomes disrupt BBB integrity."
        },
        {
          "PMID": "41660351",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "CSD causes spreading ischemia through inverse neurovascular coupling in vulnerable cortex."
        },
        {
          "PMID": "41698173",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Blood-brain barrier disruption facilitates CNS-to-saliva protein transfer."
        },
        {
          "PMID": "41748851",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Cerebrovascular architecture influences individual susceptibility to TBI-induced network dysfunction."
        },
        {
          "PMID": "41752185",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "MMP-9 upregulation mediates delayed BBB breakdown."
        },
        {
          "PMID": "41752185",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Downregulation of tight junction proteins drives early BBB permeability."
        },
        {
          "PMID": "41756282",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "IL-1R1 signaling mediates acute TBI neuroinflammation and BBB breakdown."
        }
      ],
      "atlas_layers": [
        {
          "Atlas Layer": "early_molecular_cascade",
          "Papers": "12",
          "Full-text-like": "10",
          "Abstract-only": "2",
          "Avg Depth": "3.667",
          "Anchor PMIDs": "41859452; 41446731; 41660351; 41752185; 41756282"
        },
        {
          "Atlas Layer": "tissue_network_consequence",
          "Papers": "8",
          "Full-text-like": "7",
          "Abstract-only": "1",
          "Avg Depth": "3.75",
          "Anchor PMIDs": "41532955; 41748851; 41752185; 41863251; 41039850"
        },
        {
          "Atlas Layer": "cellular_response",
          "Papers": "5",
          "Full-text-like": "3",
          "Abstract-only": "2",
          "Avg Depth": "3.5",
          "Anchor PMIDs": "41683989; 41673382; 41801080; 41765742; 41786390"
        },
        {
          "Atlas Layer": "trigger_primary_injury",
          "Papers": "2",
          "Full-text-like": "2",
          "Abstract-only": "0",
          "Avg Depth": "3.5",
          "Anchor PMIDs": "41698173; 41649131"
        },
        {
          "Atlas Layer": "clinical_chronic_phenotype",
          "Papers": "1",
          "Full-text-like": "1",
          "Abstract-only": "0",
          "Avg Depth": "3.0",
          "Anchor PMIDs": "41762323"
        }
      ],
      "contradictions": [
        "MMP-9 -> disrupts -> BBB | support_only | PMIDs: 41465583; 41801080"
      ],
      "biomarkers": [
        "FITC-labeled mNGF fluorescence: `1` claim mentions",
        "Optical density (OD) readings: `1` claim mentions",
        "Cerebral blood flow (CBF): `1` claim mentions",
        "Claudin-5 expression: `1` claim mentions",
        "Evans blue content: `1` claim mentions",
        "Occludin expression: `1` claim mentions",
        "ZO-1 expression: `1` claim mentions",
        "gadolinium leakage: `1` claim mentions"
      ],
      "targets": [
        "AQP4 via open_targets",
        "CLDN5 via open_targets",
        "MMP9 via open_targets",
        "OCLN via open_targets",
        "TJP1 via open_targets"
      ],
      "therapeutics": [
        "Compound/mechanism enrichment not yet populated."
      ],
      "trials": [
        "Trial landscape not yet populated."
      ],
      "preprints": [
        "Preprint watchlist not yet populated."
      ],
      "genomics": [
        "10x or other genomics-expression enrichment not yet populated."
      ],
      "gaps": [
        "Primary remaining queue pressure is `upgrade_source` with 5 paper(s).",
        "No compound/mechanism enrichment has been added yet.",
        "No active trial landscape has been added yet.",
        "No preprint watchlist has been added yet.",
        "No 10x or other genomics-expression enrichment has been added yet."
      ],
      "work_queue": [
        "upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41622481 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41740873 | abstract_only | abstract-only source limits mechanistic confidence",
        "deepen_extraction: PMID 41762323 | full_text_like | full-text paper is captured but still shallow for investigation use",
        "upgrade_source: PMID 41765742 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41786390 | abstract_only | abstract-only source limits mechanistic confidence"
      ],
      "raw_markdown": "# Mechanism Dossier: Blood-Brain Barrier Dysfunction\n\n- Canonical mechanism: `blood_brain_barrier_disruption`\n- Promotion status: `near_ready`\n- Promotion reason: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n## Overview\n\n- Papers in packet: `25`\n- Claim rows: `29`\n- Source quality mix: `full_text_like` 20, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 19, `upgrade_source` 5, `deepen_extraction` 1\n\n## Weighted Anchor Papers\n\n| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |\n| --- | --- | --- | --- | --- |\n| 41859452 | full_text_like | high_signal | 5.0 | SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. |\n| 41683989 | full_text_like | high_signal | 4.0 | TBI-induced BBB breakdown promotes neuroinflammation. |\n| 41446731 | full_text_like | high_signal | 4.0 | rmTBI causes acute BBB disruption via downregulation of ZO-1 and claudin-5. |\n| 41532955 | full_text_like | high_signal | 4.0 | Neutrophil-derived exosomes disrupt BBB integrity. |\n| 41660351 | full_text_like | high_signal | 4.0 | CSD causes spreading ischemia through inverse neurovascular coupling in vulnerable cortex. |\n| 41698173 | full_text_like | high_signal | 4.0 | Blood-brain barrier disruption facilitates CNS-to-saliva protein transfer. |\n| 41748851 | full_text_like | high_signal | 4.0 | Cerebrovascular architecture influences individual susceptibility to TBI-induced network dysfunction. |\n| 41752185 | full_text_like | high_signal | 4.0 | MMP-9 upregulation mediates delayed BBB breakdown. |\n| 41752185 | full_text_like | high_signal | 4.0 | Downregulation of tight junction proteins drives early BBB permeability. |\n| 41756282 | full_text_like | high_signal | 4.0 | IL-1R1 signaling mediates acute TBI neuroinflammation and BBB breakdown. |\n\n## Strongest Atlas-Layer Rows\n\n| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- |\n| early_molecular_cascade | 12 | 10 | 2 | 3.667 | 41859452; 41446731; 41660351; 41752185; 41756282 |\n| tissue_network_consequence | 8 | 7 | 1 | 3.75 | 41532955; 41748851; 41752185; 41863251; 41039850 |\n| cellular_response | 5 | 3 | 2 | 3.5 | 41683989; 41673382; 41801080; 41765742; 41786390 |\n| trigger_primary_injury | 2 | 2 | 0 | 3.5 | 41698173; 41649131 |\n| clinical_chronic_phenotype | 1 | 1 | 0 | 3.0 | 41762323 |\n\n## Contradiction / Tension Shortlist\n\n- MMP-9 -> disrupts -> BBB | support_only | PMIDs: 41465583; 41801080\n\n## Biomarker Summary\n\n- FITC-labeled mNGF fluorescence: `1` claim mentions\n- Optical density (OD) readings: `1` claim mentions\n- Cerebral blood flow (CBF): `1` claim mentions\n- Claudin-5 expression: `1` claim mentions\n- Evans blue content: `1` claim mentions\n- Occludin expression: `1` claim mentions\n- ZO-1 expression: `1` claim mentions\n- gadolinium leakage: `1` claim mentions\n\n## Target Summary\n\n- AQP4 via open_targets\n- CLDN5 via open_targets\n- MMP9 via open_targets\n- OCLN via open_targets\n- TJP1 via open_targets\n\n## Therapeutic / Compound Summary\n\n- Compound/mechanism enrichment not yet populated.\n\n## Active Trial Summary\n\n- Trial landscape not yet populated.\n\n## Preprint Watchlist\n\n- Preprint watchlist not yet populated.\n\n## 10x / Genomics Expression Signals\n\n- 10x or other genomics-expression enrichment not yet populated.\n\n## Open Questions / Evidence Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n\n## Remaining Work Queue\n\n- upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41622481 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41740873 | abstract_only | abstract-only source limits mechanistic confidence\n- deepen_extraction: PMID 41762323 | full_text_like | full-text paper is captured but still shallow for investigation use\n- upgrade_source: PMID 41765742 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41786390 | abstract_only | abstract-only source limits mechanistic confidence\n",
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "promotion_status": "near_ready",
      "papers": 25,
      "queue_burden": 6,
      "target_rows": 5,
      "compound_rows": 0,
      "trial_rows": 0,
      "preprint_rows": 0,
      "genomics_rows": 0,
      "source_path": "reports/mechanism_dossiers/blood_brain_barrier_disruption_dossier_2026-03-28_013915.md",
      "source_href": "../../reports/mechanism_dossiers/blood_brain_barrier_disruption_dossier_2026-03-28_013915.md",
      "source_github_url": "https://github.com/matthewdholtkamp/testfile/blob/main/reports/mechanism_dossiers/blood_brain_barrier_disruption_dossier_2026-03-28_013915.md"
    },
    {
      "id": "mitochondrial-dysfunction",
      "display_name": "Mitochondrial Dysfunction",
      "top_bullets": [
        "Canonical mechanism: `mitochondrial_bioenergetic_dysfunction`",
        "Promotion status: `near_ready`",
        "Promotion reason: atlas backbone is usable but still needs bounded cleanup or enrichment"
      ],
      "overview": [
        "Papers in packet: `22`",
        "Claim rows: `29`",
        "Source quality mix: `full_text_like` 17, `abstract_only` 5",
        "Action lanes: `core_atlas_candidate` 17, `upgrade_source` 5"
      ],
      "anchor_papers": [
        {
          "PMID": "41480492",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis."
        },
        {
          "PMID": "41651694",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Parkin overexpression alleviates TNI-induced neurotoxicity, apoptosis, and mitochondrial dysfunction."
        },
        {
          "PMID": "41651694",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits."
        },
        {
          "PMID": "41648326",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "TBI causes neuronal mitochondrial morphological changes."
        },
        {
          "PMID": "41648607",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "rmTBI skull secretome induces neurometabolic inflexibility."
        },
        {
          "PMID": "41651694",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI."
        },
        {
          "PMID": "41735605",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "ER stress leads to mitochondrial dysfunction via mitophagy."
        },
        {
          "PMID": "41735605",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Mitochondrial dysfunction drives neuronal death."
        },
        {
          "PMID": "41737251",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "KNG1 knockdown attenuates oxidative stress."
        },
        {
          "PMID": "41737534",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "NOX2 inhibition is neuroprotective in TBI."
        }
      ],
      "atlas_layers": [
        {
          "Atlas Layer": "cellular_response",
          "Papers": "10",
          "Full-text-like": "9",
          "Abstract-only": "1",
          "Avg Depth": "3.917",
          "Anchor PMIDs": "41480492; 41648326; 41651694; 41735605; 41737251"
        },
        {
          "Atlas Layer": "early_molecular_cascade",
          "Papers": "11",
          "Full-text-like": "8",
          "Abstract-only": "3",
          "Avg Depth": "3.5",
          "Anchor PMIDs": "41651694; 41737534; 41867877; 41623705; 41267966"
        },
        {
          "Atlas Layer": "tissue_network_consequence",
          "Papers": "5",
          "Full-text-like": "4",
          "Abstract-only": "1",
          "Avg Depth": "3.8",
          "Anchor PMIDs": "41651694; 41648607; 41735605; 41737534; 41709427"
        }
      ],
      "contradictions": [
        "No contradiction or tension cues were detected for this mechanism subset."
      ],
      "biomarkers": [
        "CAT: `1` claim mentions",
        "ROS: `1` claim mentions",
        "SOD: `1` claim mentions",
        "OSI: `1` claim mentions",
        "TAS: `1` claim mentions",
        "TOS: `1` claim mentions",
        "ClO-: `1` claim mentions",
        "ONOO-: `1` claim mentions"
      ],
      "targets": [
        "CAT via open_targets",
        "CYBB via open_targets",
        "KNG1 via open_targets",
        "PRKN via open_targets"
      ],
      "therapeutics": [
        "Compound/mechanism enrichment not yet populated."
      ],
      "trials": [
        "Trial landscape not yet populated."
      ],
      "preprints": [
        "Preprint watchlist not yet populated."
      ],
      "genomics": [
        "10x or other genomics-expression enrichment not yet populated."
      ],
      "gaps": [
        "Primary remaining queue pressure is `upgrade_source` with 5 paper(s).",
        "No compound/mechanism enrichment has been added yet.",
        "No active trial landscape has been added yet.",
        "No preprint watchlist has been added yet.",
        "No 10x or other genomics-expression enrichment has been added yet."
      ],
      "work_queue": [
        "upgrade_source: PMID 41636499 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41642156 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41709427 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41773418 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41779627 | abstract_only | abstract-only source limits mechanistic confidence"
      ],
      "raw_markdown": "# Mechanism Dossier: Mitochondrial Dysfunction\n\n- Canonical mechanism: `mitochondrial_bioenergetic_dysfunction`\n- Promotion status: `near_ready`\n- Promotion reason: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n## Overview\n\n- Papers in packet: `22`\n- Claim rows: `29`\n- Source quality mix: `full_text_like` 17, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 17, `upgrade_source` 5\n\n## Weighted Anchor Papers\n\n| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |\n| --- | --- | --- | --- | --- |\n| 41480492 | full_text_like | high_signal | 5.0 | MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. |\n| 41651694 | full_text_like | high_signal | 4.0 | Parkin overexpression alleviates TNI-induced neurotoxicity, apoptosis, and mitochondrial dysfunction. |\n| 41651694 | full_text_like | high_signal | 4.0 | Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits. |\n| 41648326 | full_text_like | high_signal | 4.0 | TBI causes neuronal mitochondrial morphological changes. |\n| 41648607 | full_text_like | high_signal | 4.0 | rmTBI skull secretome induces neurometabolic inflexibility. |\n| 41651694 | full_text_like | high_signal | 4.0 | Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI. |\n| 41735605 | full_text_like | high_signal | 4.0 | ER stress leads to mitochondrial dysfunction via mitophagy. |\n| 41735605 | full_text_like | high_signal | 4.0 | Mitochondrial dysfunction drives neuronal death. |\n| 41737251 | full_text_like | high_signal | 4.0 | KNG1 knockdown attenuates oxidative stress. |\n| 41737534 | full_text_like | high_signal | 4.0 | NOX2 inhibition is neuroprotective in TBI. |\n\n## Strongest Atlas-Layer Rows\n\n| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- |\n| cellular_response | 10 | 9 | 1 | 3.917 | 41480492; 41648326; 41651694; 41735605; 41737251 |\n| early_molecular_cascade | 11 | 8 | 3 | 3.5 | 41651694; 41737534; 41867877; 41623705; 41267966 |\n| tissue_network_consequence | 5 | 4 | 1 | 3.8 | 41651694; 41648607; 41735605; 41737534; 41709427 |\n\n## Contradiction / Tension Shortlist\n\n- No contradiction or tension cues were detected for this mechanism subset.\n\n## Biomarker Summary\n\n- CAT: `1` claim mentions\n- ROS: `1` claim mentions\n- SOD: `1` claim mentions\n- OSI: `1` claim mentions\n- TAS: `1` claim mentions\n- TOS: `1` claim mentions\n- ClO-: `1` claim mentions\n- ONOO-: `1` claim mentions\n\n## Target Summary\n\n- CAT via open_targets\n- CYBB via open_targets\n- KNG1 via open_targets\n- PRKN via open_targets\n\n## Therapeutic / Compound Summary\n\n- Compound/mechanism enrichment not yet populated.\n\n## Active Trial Summary\n\n- Trial landscape not yet populated.\n\n## Preprint Watchlist\n\n- Preprint watchlist not yet populated.\n\n## 10x / Genomics Expression Signals\n\n- 10x or other genomics-expression enrichment not yet populated.\n\n## Open Questions / Evidence Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n\n## Remaining Work Queue\n\n- upgrade_source: PMID 41636499 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41642156 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41709427 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41773418 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41779627 | abstract_only | abstract-only source limits mechanistic confidence\n",
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "promotion_status": "near_ready",
      "papers": 22,
      "queue_burden": 5,
      "target_rows": 4,
      "compound_rows": 0,
      "trial_rows": 0,
      "preprint_rows": 0,
      "genomics_rows": 0,
      "source_path": "reports/mechanism_dossiers/mitochondrial_bioenergetic_dysfunction_dossier_2026-03-28_013915.md",
      "source_href": "../../reports/mechanism_dossiers/mitochondrial_bioenergetic_dysfunction_dossier_2026-03-28_013915.md",
      "source_github_url": "https://github.com/matthewdholtkamp/testfile/blob/main/reports/mechanism_dossiers/mitochondrial_bioenergetic_dysfunction_dossier_2026-03-28_013915.md"
    },
    {
      "id": "neuroinflammation-microglial-activation",
      "display_name": "Neuroinflammation / Microglial Activation",
      "top_bullets": [
        "Canonical mechanism: `neuroinflammation_microglial_activation`",
        "Promotion status: `hold`",
        "Promotion reason: mechanism still needs more deepening, cleanup, or translational context"
      ],
      "overview": [
        "Papers in packet: `69`",
        "Claim rows: `97`",
        "Source quality mix: `full_text_like` 57, `abstract_only` 12",
        "Action lanes: `core_atlas_candidate` 52, `upgrade_source` 11, `deepen_extraction` 5, `manual_review` 1"
      ],
      "anchor_papers": [
        {
          "PMID": "41612383",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "GAS6 in 3D-sEVs drives M1 to M2 microglial polarization."
        },
        {
          "PMID": "41737534",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "TREM2 activation enhances microglial phagocytic clearance of pathological aggregates."
        },
        {
          "PMID": "41737534",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release."
        },
        {
          "PMID": "41179995",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting..."
        },
        {
          "PMID": "41622228",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "Neuronal IFN-beta activates microglial IFNAR-STAT1 axis."
        },
        {
          "PMID": "41683989",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "NLRP3 inflammasome activation mediates TBI-induced tau pathology."
        },
        {
          "PMID": "41859452",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "Gut-derived LPS activates microglial Piezo1 to drive synaptic pruning."
        },
        {
          "PMID": "41880282",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "5.0",
          "Example Claim": "Blast exposure triggers NLRP3-mediated neuronal pyroptosis in the visual cortex."
        },
        {
          "PMID": "41327381",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "mTBI induces axonal degeneration and glial activation in tracts orthogonal to the rotation axis."
        },
        {
          "PMID": "41622228",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery."
        }
      ],
      "atlas_layers": [
        {
          "Atlas Layer": "cellular_response",
          "Papers": "47",
          "Full-text-like": "38",
          "Abstract-only": "9",
          "Avg Depth": "3.72",
          "Anchor PMIDs": "41612383; 41737534; 41859452; 41327381; 41642456"
        },
        {
          "Atlas Layer": "early_molecular_cascade",
          "Papers": "30",
          "Full-text-like": "28",
          "Abstract-only": "2",
          "Avg Depth": "3.833",
          "Anchor PMIDs": "41737534; 41179995; 41622228; 41683989; 41880282"
        },
        {
          "Atlas Layer": "tissue_network_consequence",
          "Papers": "9",
          "Full-text-like": "7",
          "Abstract-only": "2",
          "Avg Depth": "3.556",
          "Anchor PMIDs": "41622228; 41648607; 41792174; 41867797; 41612383"
        },
        {
          "Atlas Layer": "clinical_chronic_phenotype",
          "Papers": "2",
          "Full-text-like": "2",
          "Abstract-only": "0",
          "Avg Depth": "4.0",
          "Anchor PMIDs": "41734021; 41756282"
        }
      ],
      "contradictions": [
        "HMGB1 -> drives -> TLR4 | support_only | PMIDs: 41756234; 41756282",
        "NLRP3 inflammasome -> drives -> IL-1\u03b2 release | support_only | PMIDs: 41712436; 41737534"
      ],
      "biomarkers": [
        "GFAP: `8` claim mentions",
        "IL-1\u03b2: `3` claim mentions",
        "IL-10: `2` claim mentions",
        "IL-6: `2` claim mentions",
        "C3: `2` claim mentions",
        "pro-inflammatory cytokines (IL-1\u03b2, IL-6, TNF-\u03b1): `1` claim mentions",
        "RAGE: `1` claim mentions",
        "S100B (blood): `1` claim mentions"
      ],
      "targets": [
        "GFAP via open_targets",
        "IL10 via open_targets",
        "IL1B via open_targets",
        "IL6 via open_targets",
        "NLRP3 via open_targets",
        "TNF via open_targets"
      ],
      "therapeutics": [
        "Compound/mechanism enrichment not yet populated."
      ],
      "trials": [
        "Trial landscape not yet populated."
      ],
      "preprints": [
        "Preprint watchlist not yet populated."
      ],
      "genomics": [
        "10x or other genomics-expression enrichment not yet populated."
      ],
      "gaps": [
        "Primary remaining queue pressure is `upgrade_source` with 11 paper(s).",
        "No compound/mechanism enrichment has been added yet.",
        "No active trial landscape has been added yet.",
        "No preprint watchlist has been added yet.",
        "No 10x or other genomics-expression enrichment has been added yet."
      ],
      "work_queue": [
        "upgrade_source: PMID 41135688 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41617128 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41622461 | abstract_only | abstract-only source limits mechanistic confidence",
        "manual_review: PMID 41643638 | abstract_only | needs review or has extraction/artifact uncertainty",
        "deepen_extraction: PMID 41675431 | full_text_like | full-text paper is captured but still shallow for investigation use",
        "deepen_extraction: PMID 41675841 | full_text_like | full-text paper is captured but still shallow for investigation use",
        "upgrade_source: PMID 41690666 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41700019 | abstract_only | abstract-only source limits mechanistic confidence",
        "upgrade_source: PMID 41702482 | abstract_only | abstract-only source limits mechanistic confidence"
      ],
      "raw_markdown": "# Mechanism Dossier: Neuroinflammation / Microglial Activation\n\n- Canonical mechanism: `neuroinflammation_microglial_activation`\n- Promotion status: `hold`\n- Promotion reason: mechanism still needs more deepening, cleanup, or translational context\n\n## Overview\n\n- Papers in packet: `69`\n- Claim rows: `97`\n- Source quality mix: `full_text_like` 57, `abstract_only` 12\n- Action lanes: `core_atlas_candidate` 52, `upgrade_source` 11, `deepen_extraction` 5, `manual_review` 1\n\n## Weighted Anchor Papers\n\n| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |\n| --- | --- | --- | --- | --- |\n| 41612383 | full_text_like | high_signal | 5.0 | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. |\n| 41737534 | full_text_like | high_signal | 5.0 | TREM2 activation enhances microglial phagocytic clearance of pathological aggregates. |\n| 41737534 | full_text_like | high_signal | 5.0 | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. |\n| 41179995 | full_text_like | high_signal | 5.0 | Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting... |\n| 41622228 | full_text_like | high_signal | 5.0 | Neuronal IFN-beta activates microglial IFNAR-STAT1 axis. |\n| 41683989 | full_text_like | high_signal | 5.0 | NLRP3 inflammasome activation mediates TBI-induced tau pathology. |\n| 41859452 | full_text_like | high_signal | 5.0 | Gut-derived LPS activates microglial Piezo1 to drive synaptic pruning. |\n| 41880282 | full_text_like | high_signal | 5.0 | Blast exposure triggers NLRP3-mediated neuronal pyroptosis in the visual cortex. |\n| 41327381 | full_text_like | high_signal | 4.0 | mTBI induces axonal degeneration and glial activation in tracts orthogonal to the rotation axis. |\n| 41622228 | full_text_like | high_signal | 4.0 | NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery. |\n\n## Strongest Atlas-Layer Rows\n\n| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- |\n| cellular_response | 47 | 38 | 9 | 3.72 | 41612383; 41737534; 41859452; 41327381; 41642456 |\n| early_molecular_cascade | 30 | 28 | 2 | 3.833 | 41737534; 41179995; 41622228; 41683989; 41880282 |\n| tissue_network_consequence | 9 | 7 | 2 | 3.556 | 41622228; 41648607; 41792174; 41867797; 41612383 |\n| clinical_chronic_phenotype | 2 | 2 | 0 | 4.0 | 41734021; 41756282 |\n\n## Neuroinflammation Subtracks\n\n| Subtrack | Papers | Full-text-like | Abstract-only | Example Signal | Biomarker Focus | Queue Burden | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| NLRP3 / Cytokine lane | 31 | 27 | 4 | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. | IL-1\u03b2; IL-10; IL-6; NLRP3 | 7 | 41737534; 41683989; 41880282; 41734021 |\n| Microglial state-transition lane | 20 | 18 | 2 | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. | C3; GFAP; S100A10; AQP-4 polarization | 3 | 41612383; 41737534; 41824127; 41618372 |\n| AQP4 / Glymphatic / Astroglial lane | 26 | 20 | 6 | Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting... | GFAP; C3; NSE; S100\u03b2 | 7 | 41179995; 41642456; 41648326; 41824127 |\n\n## Contradiction / Tension Shortlist\n\n- HMGB1 -> drives -> TLR4 | support_only | PMIDs: 41756234; 41756282\n- NLRP3 inflammasome -> drives -> IL-1\u03b2 release | support_only | PMIDs: 41712436; 41737534\n\n## Biomarker Summary\n\n- GFAP: `8` claim mentions\n- IL-1\u03b2: `3` claim mentions\n- IL-10: `2` claim mentions\n- IL-6: `2` claim mentions\n- C3: `2` claim mentions\n- pro-inflammatory cytokines (IL-1\u03b2, IL-6, TNF-\u03b1): `1` claim mentions\n- RAGE: `1` claim mentions\n- S100B (blood): `1` claim mentions\n\n## Target Summary\n\n- GFAP via open_targets\n- IL10 via open_targets\n- IL1B via open_targets\n- IL6 via open_targets\n- NLRP3 via open_targets\n- TNF via open_targets\n\n## Therapeutic / Compound Summary\n\n- Compound/mechanism enrichment not yet populated.\n\n## Active Trial Summary\n\n- Trial landscape not yet populated.\n\n## Preprint Watchlist\n\n- Preprint watchlist not yet populated.\n\n## 10x / Genomics Expression Signals\n\n- 10x or other genomics-expression enrichment not yet populated.\n\n## Open Questions / Evidence Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 11 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n\n## Remaining Work Queue\n\n- upgrade_source: PMID 41135688 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41617128 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41622461 | abstract_only | abstract-only source limits mechanistic confidence\n- manual_review: PMID 41643638 | abstract_only | needs review or has extraction/artifact uncertainty\n- deepen_extraction: PMID 41675431 | full_text_like | full-text paper is captured but still shallow for investigation use\n- deepen_extraction: PMID 41675841 | full_text_like | full-text paper is captured but still shallow for investigation use\n- upgrade_source: PMID 41690666 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41700019 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41702482 | abstract_only | abstract-only source limits mechanistic confidence\n",
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "promotion_status": "hold",
      "papers": 69,
      "queue_burden": 17,
      "target_rows": 6,
      "compound_rows": 0,
      "trial_rows": 0,
      "preprint_rows": 0,
      "genomics_rows": 0,
      "source_path": "reports/mechanism_dossiers/neuroinflammation_microglial_activation_dossier_2026-03-28_013915.md",
      "source_href": "../../reports/mechanism_dossiers/neuroinflammation_microglial_activation_dossier_2026-03-28_013915.md",
      "source_github_url": "https://github.com/matthewdholtkamp/testfile/blob/main/reports/mechanism_dossiers/neuroinflammation_microglial_activation_dossier_2026-03-28_013915.md"
    }
  ],
  "chapter": {
    "lead_mechanism": "Blood-Brain Barrier Dysfunction",
    "lead_recommendation": [
      "Lead mechanism for the first chapter: **Blood-Brain Barrier Dysfunction**",
      "Why now: status `near_ready`, queue burden `6`, target rows `5`, trial rows `0`.",
      "Interpretation: start the first chapter where the atlas backbone is coherent and the cleanup burden is still bounded."
    ],
    "framing": [
      "Chapter objective: explain how the starter mechanisms organize early injury biology, downstream network consequences, and translational hooks in TBI.",
      "Writing rule: treat full-text-like anchors as primary evidence and abstract-only rows as provisional support only.",
      "Current scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation."
    ],
    "writing_priority": [
      "Draft the lead mechanism section in full.",
      "Use the second `near_ready` mechanism as the comparative chapter section.",
      "Treat neuroinflammation as the integrating response layer, but write it through the narrower starter lanes instead of one broad inflammatory block."
    ],
    "immediate_follow_on": [
      "Add manual ChEMBL rows for the lead mechanism.",
      "Add targeted public-trial review for the lead mechanism to remove generic or weak trial matches.",
      "If 10x outputs become available, append them into the same dossier before locking the chapter narrative."
    ],
    "raw_markdown": "# Starter Atlas Chapter Draft\n\nThis draft is dossier-driven. It is meant to be the first real writing artifact assembled from the investigation engine, not from manually rereading the whole corpus.\n\n## Lead Recommendation\n\n- Lead mechanism for the first chapter: **Blood-Brain Barrier Dysfunction**\n- Why now: status `near_ready`, queue burden `6`, target rows `5`, trial rows `0`.\n- Interpretation: start the first chapter where the atlas backbone is coherent and the cleanup burden is still bounded.\n\n## Chapter Framing\n\n- Chapter objective: explain how the starter mechanisms organize early injury biology, downstream network consequences, and translational hooks in TBI.\n- Writing rule: treat full-text-like anchors as primary evidence and abstract-only rows as provisional support only.\n- Current scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation.\n\n## Blood-Brain Barrier Dysfunction\n\n- Promotion status: `near_ready`\n- Readout: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n### Current State\n\n- Papers in packet: `25`\n- Claim rows: `29`\n- Source quality mix: `full_text_like` 20, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 19, `upgrade_source` 5, `deepen_extraction` 1\n\n### Anchor Signals\n\n- | 41859452 | full_text_like | high_signal | 5.0 | SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. |\n- | 41683989 | full_text_like | high_signal | 4.0 | TBI-induced BBB breakdown promotes neuroinflammation. |\n- | 41446731 | full_text_like | high_signal | 4.0 | rmTBI causes acute BBB disruption via downregulation of ZO-1 and claudin-5. |\n\n### Backbone Rows\n\n- | early_molecular_cascade | 12 | 10 | 2 | 3.667 | 41859452; 41446731; 41660351; 41752185; 41756282 |\n- | tissue_network_consequence | 8 | 7 | 1 | 3.75 | 41532955; 41748851; 41752185; 41863251; 41039850 |\n- | cellular_response | 5 | 3 | 2 | 3.5 | 41683989; 41673382; 41801080; 41765742; 41786390 |\n\n### Translational / Enrichment Readout\n\n- Target: AQP4 via open_targets\n- Target: CLDN5 via open_targets\n- Target: MMP9 via open_targets\n\n### Remaining Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n- Work queue snapshot:\n  - upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41622481 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41740873 | abstract_only | abstract-only source limits mechanistic confidence\n  - deepen_extraction: PMID 41762323 | full_text_like | full-text paper is captured but still shallow for investigation use\n\n## Mitochondrial Dysfunction\n\n- Promotion status: `near_ready`\n- Readout: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n### Current State\n\n- Papers in packet: `22`\n- Claim rows: `29`\n- Source quality mix: `full_text_like` 17, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 17, `upgrade_source` 5\n\n### Anchor Signals\n\n- | 41480492 | full_text_like | high_signal | 5.0 | MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. |\n- | 41651694 | full_text_like | high_signal | 4.0 | Parkin overexpression alleviates TNI-induced neurotoxicity, apoptosis, and mitochondrial dysfunction. |\n- | 41651694 | full_text_like | high_signal | 4.0 | Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits. |\n\n### Backbone Rows\n\n- | cellular_response | 10 | 9 | 1 | 3.917 | 41480492; 41648326; 41651694; 41735605; 41737251 |\n- | early_molecular_cascade | 11 | 8 | 3 | 3.5 | 41651694; 41737534; 41867877; 41623705; 41267966 |\n- | tissue_network_consequence | 5 | 4 | 1 | 3.8 | 41651694; 41648607; 41735605; 41737534; 41709427 |\n\n### Translational / Enrichment Readout\n\n- Target: CAT via open_targets\n- Target: CYBB via open_targets\n- Target: KNG1 via open_targets\n\n### Remaining Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n- Work queue snapshot:\n  - upgrade_source: PMID 41636499 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41642156 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41709427 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41773418 | abstract_only | abstract-only source limits mechanistic confidence\n\n## Neuroinflammation / Microglial Activation\n\n- Promotion status: `hold`\n- Readout: mechanism still needs more deepening, cleanup, or translational context\n\n### Current State\n\n- Papers in packet: `69`\n- Claim rows: `97`\n- Source quality mix: `full_text_like` 57, `abstract_only` 12\n- Action lanes: `core_atlas_candidate` 52, `upgrade_source` 11, `deepen_extraction` 5, `manual_review` 1\n\n### Anchor Signals\n\n- | 41612383 | full_text_like | high_signal | 5.0 | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. |\n- | 41737534 | full_text_like | high_signal | 5.0 | TREM2 activation enhances microglial phagocytic clearance of pathological aggregates. |\n- | 41737534 | full_text_like | high_signal | 5.0 | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. |\n\n### Backbone Rows\n\n- | cellular_response | 47 | 38 | 9 | 3.72 | 41612383; 41737534; 41859452; 41327381; 41642456 |\n- | early_molecular_cascade | 30 | 28 | 2 | 3.833 | 41737534; 41179995; 41622228; 41683989; 41880282 |\n- | tissue_network_consequence | 9 | 7 | 2 | 3.556 | 41622228; 41648607; 41792174; 41867797; 41612383 |\n\n### Narrower Neuroinflammation Lanes\n\n- NLRP3 / Cytokine lane: papers `31`, full-text-like `27`, abstract-only `4`, queue burden `7`. Example signal: Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release.. Biomarker focus: IL-1\u03b2; IL-10; IL-6; NLRP3. Anchor PMIDs: 41737534; 41683989; 41880282; 41734021.\n- Microglial state-transition lane: papers `20`, full-text-like `18`, abstract-only `2`, queue burden `3`. Example signal: GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.. Biomarker focus: C3; GFAP; S100A10; AQP-4 polarization. Anchor PMIDs: 41612383; 41737534; 41824127; 41618372.\n- AQP4 / Glymphatic / Astroglial lane: papers `26`, full-text-like `20`, abstract-only `6`, queue burden `7`. Example signal: Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting.... Biomarker focus: GFAP; C3; NSE; S100\u03b2. Anchor PMIDs: 41179995; 41642456; 41648326; 41824127.\n\n### Translational / Enrichment Readout\n\n- Target: GFAP via open_targets\n- Target: IL10 via open_targets\n- Target: IL1B via open_targets\n\n### Remaining Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 11 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n- Work queue snapshot:\n  - upgrade_source: PMID 41135688 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41617128 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41622461 | abstract_only | abstract-only source limits mechanistic confidence\n\n## Writing Priority\n\n1. Draft the lead mechanism section in full.\n2. Use the second `near_ready` mechanism as the comparative chapter section.\n3. Treat neuroinflammation as the integrating response layer, but write it through the narrower starter lanes instead of one broad inflammatory block.\n\n## Immediate Follow-on\n\n- Add manual ChEMBL rows for the lead mechanism.\n- Add targeted public-trial review for the lead mechanism to remove generic or weak trial matches.\n- If 10x outputs become available, append them into the same dossier before locking the chapter narrative.\n\n",
    "preview_markdown": "# Starter Atlas Chapter Synthesis Draft\n\nThis draft is evidence-first. It is built from the mechanistic synthesis packet, which itself is derived from the chapter evidence ledger rather than from dossier recap alone.\n\n## Lead Recommendation\n\n- Lead chapter mechanism: **Blood-Brain Barrier Dysfunction**\n- Writing rule: use `ready` rows as assertive prose, `caution` rows as bounded interpretation, and `hold` rows only as unresolved context.\n- Scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation.\n\n## Canonical Demo Chapter\n\nThe first proof-of-concept chapter should be **Blood-Brain Barrier Dysfunction**.\n\n### Demo Paragraph 1\n\nSCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This is reinforced by evidence that neutrophil-derived exosomes disrupt BBB integrity. The current atlas also places BBB disruption upstream of at least part of the inflammatory response.\n\n### Demo Paragraph 2\n\nSCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This sequence then extends into a downstream cellular-response lane in which TBI-induced BBB breakdown promotes neuroinflammation. It remains visible at the tissue/network level because neutrophil-derived exosomes disrupt BBB integrity.\n\n### Demo Paragraph 3\n\nCurrent BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI. The bridge and downstream language should stay bounded until the remaining upgrade and deepening items are cleared.\n\n### Demo Paragraph 4\n\nThe current translational lane is still early, but the atlas already points to AQP4, CLDN5, MMP9 as the most actionable targets for the first proof-of-concept pass.\n\n### Why This Mechanism First\n\n- It has the cleanest early-to-downstream causal structure in the current atlas.\n- It already carries an explicit bridge into neuroinflammatory amplification.\n- Its remaining uncertainty is bounded enough to support a strong proof-of-concept chapter now.\n\n## Blood-Brain Barrier Dysfunction\n\nSCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This is reinforced by evidence that neutrophil-derived exosomes disrupt BBB integrity. The current atlas also places BBB disruption upstream of at least part of the inflammatory response.\n\n### Canonical Demo Narrative\n\nSCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This is reinforced by evidence that neutrophil-derived exosomes disrupt BBB integrity. The current atlas also places BBB disruption upstream of at least part of the inflammatory response.\n\nSCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This sequence then extends into a downstream cellular-response lane in which TBI-induced BBB breakdown promotes neuroinflammation. It remains visible at the tissue/network level because neutrophil-derived exosomes disrupt BBB integrity.\n\nCurrent BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI. The bridge and downstream language should stay bounded until the remaining upgrade and deepening items are cleared.\n\nThe current translational lane is still early, but the atlas already points to AQP4, CLDN5, MMP9 as the most actionable targets for the first proof-of-concept pass.\n\n### Causal Sequence\n\n- `early_molecular_cascade` | `ready` | SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. | PMIDs: 41859452; 41446731; 41660351; 41752185; 41756282\n- `cellular_response` | `caution` | TBI-induced BBB breakdown promotes neuroinflammation. | PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n- `tissue_network_consequence` | `ready` | Neutrophil-derived exosomes disrupt BBB integrity. | PMIDs: 41532955; 41748851; 41752185; 41863251; 41039850\n\n### Cross-Mechanism Links\n\n- Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI. Related mechanism: Neuroinflammation / Microglial Activation. PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n\n### Evidence Boundaries\n\n- Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.\n\n### Translational Hooks\n\n- Translational hook: AQP4 (target_association)\n- Translational hook: CLDN5 (target_association)\n- Translational hook: MMP9 (target_association)\n\n### Immediate Next Actions\n\n- Upgrade the abstract-only support rows before locking final prose.\n\n## Mitochondrial Dysfunction\n\nMAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis.\n\n### Causal Sequence\n\n- `early_molecular_cascade` | `caution` | Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI. | PMIDs: 41651694; 41737534; 41867877; 41623705; 41267966\n- `cellular_response` | `ready` | MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. | PMIDs: 41480492; 41648326; 41651694; 41735605; 41737251\n- `tissue_network_consequence` | `caution` | Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits. | PMIDs: 41651694; 41648607; 41735605; 41737534; 41709427\n\n### Cross-Mechanism Links\n\n- No mechanism bridge has reached writing-grade support yet.\n\n### Evidence Boundaries\n\n- Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.\n\n### Translational Hooks\n\n- Translational hook: CAT (target_association)\n- Translational hook: CYBB (target_association)\n- Translational hook: KNG1 (target_association)\n\n### Immediate Next Actions\n\n- Upgrade the abstract-only support rows before locking final prose.\n\n## Neuroinflammation / Microglial Activation\n\nNeuroinflammation is better handled as narrower starter lanes than as one broad block: NLRP3 / Cytokine lane, Microglial state-transition lane, AQP4 / Glymphatic / Astroglial lane. The current strongest lane indicates that microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. A second lane captures that GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.\n\n### Causal Sequence\n\n- `early_molecular_cascade` | `caution` | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. | PMIDs: 41737534; 41683989; 41880282; 41734021; 41853701\n- `cellular_response` | `caution` | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. | PMIDs: 41612383; 41737534; 41824127; 41618372; 41625091\n- `early_molecular_cascade` | `hold` | Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting in the accumulation of tau protein, S100\u03b2, glial fibrillary acidic protein (GFAP), and neuron-specific enolase (NSE), which promotes neurofibrillary pathology, neuroinflammation, and neurodegeneration. | PMIDs: 41179995; 41642456; 41648326; 41103638; 41508250\n- `tissue_network_consequence` | `ready` | NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery. | PMIDs: 41622228; 41648607; 41792174; 41867797; 41612383\n\n### Cross-Mechanism Links\n\n- The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism. Related mechanism: Blood-Brain Barrier Dysfunction. PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n\n### Evidence Boundaries\n\n- Open blockers: needs deeper extraction 1, needs source upgrade 1, needs adjudication 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.\n\n### Translational Hooks\n\n- Translational hook: GFAP (target_association)\n- Translational hook: IL10 (target_association)\n- Translational hook: IL1B (target_association)\n\n### Immediate Next Actions\n\n- Upgrade the abstract-only support rows before locking final prose.\n- Deepen the shallow full-text rows so the mechanism sequence is more explicit.\n\n## Cross-Mechanism Synthesis\n\n- The current atlas is strongest when it treats BBB dysfunction as an early vascular gate that can feed forward into later inflammatory biology.\n- Mitochondrial dysfunction remains the best comparative intracellular injury program, but it still needs a denser bridge into the broader inflammatory layer.\n- Neuroinflammation is better handled as an integrating response layer than as the lead chapter until more bridge rows and cleanup reduce its burden.\n\n### Explicit Bridge Statements\n\n- Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI. | PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n- The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism. | PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n\n## Practical Follow-On\n\n- Keep the BBB section as the lead writing section.\n- Use mitochondrial dysfunction as the second section and keep its provisional rows clearly marked.\n- Treat neuroinflammation as the integrating downstream section rather than the opening chapter.\n- Finish the remaining BBB source upgrades before declaring the section locked.\n- Expand mitochondrial translational rows so the second section has a clearer intervention bridge.\n"
  },
  "ledger": [
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "mechanism_display_name": "Blood-Brain Barrier Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "early_molecular_cascade",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "12",
      "supporting_pmids": "41859452; 41446731; 41660351; 41752185; 41756282",
      "proposed_narrative_claim": "SCFAs cross the BBB and inhibit HDACs to promote neuroprotection.",
      "best_anchor_claim_text": "Microbial metabolites like SCFAs cross the BBB to inhibit histone deacetylase activity, promoting neuroprotection and reducing neuroinflammation.",
      "best_anchor_pmid": "41859452",
      "source_quality_mix": "full_text_like:10; abstract_only:2",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 10
        },
        {
          "label": "abstract_only",
          "count": 2
        }
      ]
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "mechanism_display_name": "Blood-Brain Barrier Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "tissue_network_consequence",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "8",
      "supporting_pmids": "41532955; 41748851; 41752185; 41863251; 41039850",
      "proposed_narrative_claim": "Neutrophil-derived exosomes disrupt BBB integrity.",
      "best_anchor_claim_text": "Neutrophil-derived exosomes compromise the BBB by downregulating tight junction proteins (Claudin-5, Occludin, ZO-1).",
      "best_anchor_pmid": "41532955",
      "source_quality_mix": "full_text_like:7; abstract_only:1",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 7
        },
        {
          "label": "abstract_only",
          "count": 1
        }
      ]
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "mechanism_display_name": "Blood-Brain Barrier Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "cellular_response",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "5",
      "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
      "proposed_narrative_claim": "TBI-induced BBB breakdown promotes neuroinflammation.",
      "best_anchor_claim_text": "BBB disruption following TBI allows infiltration of peripheral immune cells and circulating inflammatory mediators, amplifying neuroinflammation.",
      "best_anchor_pmid": "41683989",
      "source_quality_mix": "full_text_like:3; abstract_only:2",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "upgrade_source:2",
      "confidence_bucket": "provisional",
      "promotion_note": "needs source upgrade",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 3
        },
        {
          "label": "abstract_only",
          "count": 2
        }
      ]
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "mechanism_display_name": "Mitochondrial Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "cellular_response",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "10",
      "supporting_pmids": "41480492; 41648326; 41651694; 41735605; 41737251",
      "proposed_narrative_claim": "MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis.",
      "best_anchor_claim_text": "Excessive Ca2+ influx at MAMs triggers mPTP opening, leading to cytochrome c release and caspase-3 activation.",
      "best_anchor_pmid": "41480492",
      "source_quality_mix": "full_text_like:9; abstract_only:1",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 9
        },
        {
          "label": "abstract_only",
          "count": 1
        }
      ]
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "mechanism_display_name": "Mitochondrial Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "early_molecular_cascade",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "11",
      "supporting_pmids": "41651694; 41737534; 41867877; 41623705; 41267966",
      "proposed_narrative_claim": "Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI.",
      "best_anchor_claim_text": "Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI.",
      "best_anchor_pmid": "41651694",
      "source_quality_mix": "full_text_like:8; abstract_only:3",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "provisional",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 8
        },
        {
          "label": "abstract_only",
          "count": 3
        }
      ]
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "mechanism_display_name": "Mitochondrial Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "tissue_network_consequence",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "5",
      "supporting_pmids": "41651694; 41648607; 41735605; 41737534; 41709427",
      "proposed_narrative_claim": "Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits.",
      "best_anchor_claim_text": "Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits.",
      "best_anchor_pmid": "41651694",
      "source_quality_mix": "full_text_like:4; abstract_only:1",
      "quality_mix": "high_signal:4; usable:1",
      "contradiction_signal": "none_detected",
      "action_blockers": "upgrade_source:1",
      "confidence_bucket": "provisional",
      "promotion_note": "needs source upgrade",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 4
        },
        {
          "label": "abstract_only",
          "count": 1
        }
      ]
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "tissue_network_consequence",
      "mechanism_subtrack": "",
      "mechanism_subtrack_display_name": "",
      "paper_count": "9",
      "supporting_pmids": "41622228; 41648607; 41792174; 41867797; 41612383",
      "proposed_narrative_claim": "NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery.",
      "best_anchor_claim_text": "NK cell depletion significantly attenuates TBI-induced neuroinflammation and improves neurological outcomes.",
      "best_anchor_pmid": "41622228",
      "source_quality_mix": "full_text_like:7; abstract_only:2",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 7
        },
        {
          "label": "abstract_only",
          "count": 2
        }
      ]
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "early_molecular_cascade",
      "mechanism_subtrack": "nlrp3_cytokine_lane",
      "mechanism_subtrack_display_name": "NLRP3 / Cytokine lane",
      "paper_count": "30",
      "supporting_pmids": "41737534; 41179995; 41622228; 41683989; 41880282",
      "proposed_narrative_claim": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release.",
      "best_anchor_claim_text": "NLRP3 inflammasome activation in microglia drives caspase-1-mediated maturation of IL-1\u03b2 and IL-18, exacerbating neuroinflammation in AD and TBI.",
      "best_anchor_pmid": "41737534",
      "source_quality_mix": "full_text_like:28; abstract_only:2",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 28
        },
        {
          "label": "abstract_only",
          "count": 2
        }
      ]
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "row_kind": "atlas_layer_backbone",
      "atlas_layer": "cellular_response",
      "mechanism_subtrack": "microglial_state_transition_lane",
      "mechanism_subtrack_display_name": "Microglial state-transition lane",
      "paper_count": "47",
      "supporting_pmids": "41612383; 41737534; 41859452; 41327381; 41642456",
      "proposed_narrative_claim": "GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
      "best_anchor_claim_text": "3D-sEVs promote M1 to M2 microglial polarization via GAS6 delivery.",
      "best_anchor_pmid": "41612383",
      "source_quality_mix": "full_text_like:38; abstract_only:9",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "provisional",
      "promotion_note": "ready to write",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 38
        },
        {
          "label": "abstract_only",
          "count": 9
        }
      ]
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "row_kind": "mechanism_subtrack_focus",
      "atlas_layer": "cellular_response",
      "mechanism_subtrack": "microglial_state_transition_lane",
      "mechanism_subtrack_display_name": "Microglial state-transition lane",
      "paper_count": "16",
      "supporting_pmids": "41612383; 41737534; 41824127; 41618372; 41625091",
      "proposed_narrative_claim": "GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
      "best_anchor_claim_text": "3D-sEVs promote M1 to M2 microglial polarization via GAS6 delivery.",
      "best_anchor_pmid": "41612383",
      "source_quality_mix": "full_text_like:14; abstract_only:2",
      "quality_mix": "high_signal:13; usable:3",
      "contradiction_signal": "none_detected",
      "action_blockers": "upgrade_source:2",
      "confidence_bucket": "provisional",
      "promotion_note": "needs source upgrade",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 14
        },
        {
          "label": "abstract_only",
          "count": 2
        }
      ]
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "row_kind": "mechanism_subtrack_focus",
      "atlas_layer": "early_molecular_cascade",
      "mechanism_subtrack": "nlrp3_cytokine_lane",
      "mechanism_subtrack_display_name": "NLRP3 / Cytokine lane",
      "paper_count": "29",
      "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701",
      "proposed_narrative_claim": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release.",
      "best_anchor_claim_text": "NLRP3 inflammasome activation in microglia drives caspase-1-mediated maturation of IL-1\u03b2 and IL-18, exacerbating neuroinflammation in AD and TBI.",
      "best_anchor_pmid": "41737534",
      "source_quality_mix": "full_text_like:25; abstract_only:4",
      "quality_mix": "high_signal:24; usable:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "upgrade_source:4; deepen_extraction:3",
      "confidence_bucket": "provisional",
      "promotion_note": "needs deeper extraction",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 25
        },
        {
          "label": "abstract_only",
          "count": 4
        }
      ]
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "row_kind": "mechanism_subtrack_focus",
      "atlas_layer": "early_molecular_cascade",
      "mechanism_subtrack": "aqp4_glymphatic_astroglial_lane",
      "mechanism_subtrack_display_name": "AQP4 / Glymphatic / Astroglial lane",
      "paper_count": "21",
      "supporting_pmids": "41179995; 41642456; 41648326; 41103638; 41508250",
      "proposed_narrative_claim": "Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting in the accumulation of tau protein, S100\u03b2, glial fibrillary acidic protein (GFAP), and neuron-specific enolase (NSE), which promotes neurofibrillary pathology, neuroinflammation, and neurodegeneration.",
      "best_anchor_claim_text": "Genetic knock-out of AQP-4 aggravates post-TBI glymphatic dysfunction, leading to accumulation of tau protein, S100\u03b2, GFAP, and NSE, promoting neurofibrillary pathology, neuroinflammation, and neurodegeneration.",
      "best_anchor_pmid": "41179995",
      "source_quality_mix": "full_text_like:17; abstract_only:4",
      "quality_mix": "high_signal:18; usable:2; review_needed:1",
      "contradiction_signal": "none_detected",
      "action_blockers": "upgrade_source:3; deepen_extraction:1; manual_review:1",
      "confidence_bucket": "hold",
      "promotion_note": "needs adjudication",
      "strength_tag": "speculative",
      "source_quality_breakdown": [
        {
          "label": "full_text_like",
          "count": 17
        },
        {
          "label": "abstract_only",
          "count": 4
        }
      ]
    }
  ],
  "workpack": {
    "why_now": [
      "Manual enrichment workpack has not been generated in this run yet."
    ],
    "top_priorities": [],
    "fill_targets": [
      "Run the manual enrichment cycle to produce the next BBB / mitochondrial fill targets."
    ],
    "fill_order": [
      "Generate the manual workpack after the curated enrichment pass."
    ],
    "next_move": [
      "Use the atlas build for synthesis review, then run the manual enrichment cycle when human curation is ready."
    ],
    "raw_markdown": ""
  },
  "bridge_rows": [
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "biomarker_seed": "FITC-labeled mNGF fluorescence",
      "target_entity": "AQP4",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: AQP4",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "biomarker_seed": "Optical density (OD) readings",
      "target_entity": "CLDN5",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: CLDN5",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "biomarker_seed": "Cerebral blood flow (CBF)",
      "target_entity": "MMP9",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: MMP9",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "biomarker_seed": "Claudin-5 expression",
      "target_entity": "OCLN",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: OCLN",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "biomarker_seed": "Evans blue content",
      "target_entity": "TJP1",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: TJP1",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "biomarker_seed": "CAT",
      "target_entity": "CAT",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: CAT",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "biomarker_seed": "ROS",
      "target_entity": "CYBB",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: CYBB",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "biomarker_seed": "SOD",
      "target_entity": "KNG1",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: KNG1",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "biomarker_seed": "OSI",
      "target_entity": "PRKN",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: PRKN",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "GFAP",
      "target_entity": "GFAP",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: GFAP",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "IL-1\u03b2",
      "target_entity": "IL10",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: IL-10",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "IL-10",
      "target_entity": "IL1B",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: IL1B",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "IL-6",
      "target_entity": "IL6",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: IL6",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "C3",
      "target_entity": "NLRP3",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: NLRP3",
      "evidence_summary": "target_association | open_targets"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "pro-inflammatory cytokines (IL-1\u03b2, IL-6, TNF-\u03b1)",
      "target_entity": "TNF",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: TNF",
      "evidence_summary": "target_association | open_targets"
    }
  ],
  "release_manifest": {
    "summary": {
      "lead_chapter_candidate": "Blood-Brain Barrier Dysfunction",
      "canonical_demo_ready": 1,
      "bounded_demo_ready": 0,
      "core_atlas_now": 0,
      "core_atlas_candidates": 1,
      "review_track": 0,
      "hold": 2
    },
    "rows": [
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "promotion_status": "near_ready",
        "readiness_score": "43",
        "gate_status": "near_ready",
        "stable_rows": "2",
        "provisional_rows": "1",
        "blocked_rows": "1",
        "bridge_rows": "1",
        "translational_hook_rows": "3",
        "queue_burden": "6",
        "target_rows": "5",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "core_atlas_candidate",
        "chapter_role": "lead_section",
        "recommended_action": "close_last_gaps_then_write",
        "demo_status": "canonical_demo_ready",
        "demo_reason": "lead mechanism has enough stable structure and bridge support to anchor the proof-of-concept chapter now"
      },
      {
        "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
        "display_name": "Mitochondrial Dysfunction",
        "promotion_status": "near_ready",
        "readiness_score": "8",
        "gate_status": "hold",
        "stable_rows": "1",
        "provisional_rows": "2",
        "blocked_rows": "1",
        "bridge_rows": "0",
        "translational_hook_rows": "3",
        "queue_burden": "5",
        "target_rows": "4",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "hold",
        "chapter_role": "hold",
        "recommended_action": "upgrade_remaining_abstract_support",
        "demo_status": "supporting_section",
        "demo_reason": "mechanism is better used as a supporting or follow-on section than the primary demo chapter"
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "promotion_status": "hold",
        "readiness_score": "0",
        "gate_status": "hold",
        "stable_rows": "2",
        "provisional_rows": "3",
        "blocked_rows": "3",
        "bridge_rows": "1",
        "translational_hook_rows": "3",
        "queue_burden": "17",
        "target_rows": "6",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs adjudication; needs deeper extraction; needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "hold",
        "chapter_role": "hold",
        "recommended_action": "upgrade_remaining_abstract_support",
        "demo_status": "supporting_section",
        "demo_reason": "mechanism is better used as a supporting or follow-on section than the primary demo chapter"
      }
    ],
    "quality_gate_csv": "reports/atlas_quality_gate/atlas_quality_gate_2026-03-28_013915.csv"
  },
  "decision_brief": {},
  "idea_gate": {
    "summary": {
      "mechanism_count": 3,
      "idea_ready_now": 3,
      "breakthrough_ready_now": 1,
      "idea_almost_ready": 0
    },
    "rows": [
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "papers": 25,
        "full_text_like": 20,
        "abstract_only": 5,
        "stable_rows": 2,
        "provisional_rows": 1,
        "blocked_rows": 1,
        "signal_rows": 9,
        "queue_burden": 6,
        "chapter_gate_status": "near_ready",
        "chapter_release_bucket": "core_atlas_candidate",
        "idea_generation_status": "ready_now",
        "breakthrough_status": "ready_now",
        "missing_for_idea_generation": "",
        "missing_for_breakthrough": "",
        "recommended_next_move": "generate_hypothesis_candidates_now"
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "papers": 69,
        "full_text_like": 57,
        "abstract_only": 12,
        "stable_rows": 2,
        "provisional_rows": 3,
        "blocked_rows": 3,
        "signal_rows": 10,
        "queue_burden": 17,
        "chapter_gate_status": "hold",
        "chapter_release_bucket": "hold",
        "idea_generation_status": "ready_now",
        "breakthrough_status": "almost_ready",
        "missing_for_idea_generation": "",
        "missing_for_breakthrough": "queue_burden",
        "recommended_next_move": "generate_hypothesis_candidates_now"
      },
      {
        "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
        "display_name": "Mitochondrial Dysfunction",
        "papers": 22,
        "full_text_like": 17,
        "abstract_only": 5,
        "stable_rows": 1,
        "provisional_rows": 2,
        "blocked_rows": 1,
        "signal_rows": 7,
        "queue_burden": 5,
        "chapter_gate_status": "hold",
        "chapter_release_bucket": "hold",
        "idea_generation_status": "ready_now",
        "breakthrough_status": "almost_ready",
        "missing_for_idea_generation": "",
        "missing_for_breakthrough": "papers, stable_rows",
        "recommended_next_move": "generate_hypothesis_candidates_now"
      }
    ],
    "thresholds": {
      "idea_ready": {
        "min_papers": 15,
        "min_full_text_like": 10,
        "min_stable_rows": 1,
        "min_signal_rows": 1,
        "max_queue_burden": 18
      },
      "breakthrough_ready": {
        "min_papers": 25,
        "min_full_text_like": 15,
        "min_stable_rows": 2,
        "min_signal_rows": 3,
        "max_queue_burden": 12
      }
    },
    "release_manifest_csv": "reports/atlas_release_manifest/atlas_release_manifest_2026-03-28_013915.csv"
  },
  "hypothesis_candidates": {
    "rows": [
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "hypothesis_type": "cross_mechanism_bridge",
        "title": "Blood-Brain Barrier Dysfunction \u2192 Neuroinflammation / Microglial Activation bridge hypothesis",
        "statement": "Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI.",
        "strength_tag": "moderate",
        "why_now": "This bridge is already explicit in the synthesis packet, so it is ready to be used as a causal demo path.",
        "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
        "next_test": "Use the cross-mechanism chain to test whether Blood-Brain Barrier Dysfunction should be framed as upstream of Neuroinflammation / Microglial Activation.",
        "blockers": "upgrade_source:2",
        "operator_decision": "Needs adjudication",
        "decision_rationale": "This bridge shapes the atlas architecture, so it needs explicit confirmation.",
        "unlocks": "Use full-text anchors to confirm whether the upstream/downstream framing should hold."
      },
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "hypothesis_type": "mechanistic_driver",
        "title": "Blood-Brain Barrier Dysfunction driver hypothesis",
        "statement": "SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. TBI-induced BBB breakdown promotes neuroinflammation. Neutrophil-derived exosomes disrupt BBB integrity.",
        "strength_tag": "assertive",
        "why_now": "ready_now for idea generation with 25 papers and 6 queue items.",
        "supporting_pmids": "41859452; 41446731; 41660351; 41752185; 41756282; 41683989; 41673382; 41801080; 41765742; 41786390; 41532955; 41748851; 41863251; 41039850",
        "next_test": "Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.",
        "blockers": "Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
        "operator_decision": "Write now",
        "decision_rationale": "This is strong enough to anchor prose now.",
        "unlocks": "Advance the mechanism into the chapter draft and keep the blocker notes attached."
      },
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "hypothesis_type": "translational_probe",
        "title": "Blood-Brain Barrier Dysfunction translational probe hypothesis",
        "statement": "Modulating AQP4, CLDN5, MMP9 may be the fastest translational probe for blood-brain barrier dysfunction in this atlas version.",
        "strength_tag": "moderate",
        "why_now": "These are the most actionable targets/entities currently attached to this mechanism.",
        "supporting_pmids": "",
        "next_test": "Prioritize enrichment and literature checks for AQP4, CLDN5, MMP9 before expanding to a wider target set.",
        "blockers": "compound/trial depth is still limited",
        "operator_decision": "Needs enrichment",
        "decision_rationale": "The mechanism is interesting, but the translational layer is still too thin.",
        "unlocks": "Fill target, compound, and trial support before promoting this beyond a probe idea."
      },
      {
        "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
        "display_name": "Mitochondrial Dysfunction",
        "hypothesis_type": "mechanistic_driver",
        "title": "Mitochondrial Dysfunction driver hypothesis",
        "statement": "Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI. MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits.",
        "strength_tag": "moderate",
        "why_now": "ready_now for idea generation with 22 papers and 5 queue items.",
        "supporting_pmids": "41651694; 41737534; 41867877; 41623705; 41267966; 41480492; 41648326; 41735605; 41737251; 41648607; 41709427",
        "next_test": "Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.",
        "blockers": "Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
        "operator_decision": "Needs adjudication",
        "decision_rationale": "The driver story is usable, but the narrative still needs a bounded scientific pass.",
        "unlocks": "Pressure-test the strongest anchors and decide what language stays assertive versus cautionary."
      },
      {
        "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
        "display_name": "Mitochondrial Dysfunction",
        "hypothesis_type": "translational_probe",
        "title": "Mitochondrial Dysfunction translational probe hypothesis",
        "statement": "Modulating CAT, CYBB, KNG1 may be the fastest translational probe for mitochondrial dysfunction in this atlas version.",
        "strength_tag": "moderate",
        "why_now": "These are the most actionable targets/entities currently attached to this mechanism.",
        "supporting_pmids": "",
        "next_test": "Prioritize enrichment and literature checks for CAT, CYBB, KNG1 before expanding to a wider target set.",
        "blockers": "compound/trial depth is still limited",
        "operator_decision": "Needs enrichment",
        "decision_rationale": "The mechanism is interesting, but the translational layer is still too thin.",
        "unlocks": "Fill target, compound, and trial support before promoting this beyond a probe idea."
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "hypothesis_type": "cross_mechanism_bridge",
        "title": "Neuroinflammation / Microglial Activation \u2192 Blood-Brain Barrier Dysfunction bridge hypothesis",
        "statement": "The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism.",
        "strength_tag": "moderate",
        "why_now": "This bridge is already explicit in the synthesis packet, so it is ready to be used as a causal demo path.",
        "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
        "next_test": "Use the cross-mechanism chain to test whether Neuroinflammation / Microglial Activation should be framed as upstream of Blood-Brain Barrier Dysfunction.",
        "blockers": "upgrade_source:2",
        "operator_decision": "Needs adjudication",
        "decision_rationale": "This bridge shapes the atlas architecture, so it needs explicit confirmation.",
        "unlocks": "Use full-text anchors to confirm whether the upstream/downstream framing should hold."
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "hypothesis_type": "mechanistic_driver",
        "title": "Neuroinflammation / Microglial Activation driver hypothesis",
        "statement": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting in the accumulation of tau protein, S100\u03b2, glial fibrillary acidic protein (GFAP), and neuron-specific enolase (NSE), which promotes neurofibrillary pathology, neuroinflammation, and neurodegeneration. GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
        "strength_tag": "moderate",
        "why_now": "ready_now for idea generation with 69 papers and 17 queue items.",
        "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701; 41179995; 41642456; 41648326; 41103638; 41508250; 41612383; 41824127; 41618372; 41625091",
        "next_test": "Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.",
        "blockers": "Open blockers: needs deeper extraction 1, needs source upgrade 1, needs adjudication 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
        "operator_decision": "Needs adjudication",
        "decision_rationale": "The driver story is usable, but the narrative still needs a bounded scientific pass.",
        "unlocks": "Pressure-test the strongest anchors and decide what language stays assertive versus cautionary."
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "hypothesis_type": "subtrack_narrowing",
        "title": "Neuroinflammation should be split into narrower lanes",
        "statement": "The neuroinflammation bucket is likely hiding multiple distinct idea lanes: inflammasome/cytokine signaling, microglial state transition, and glymphatic/astroglial response should be evaluated separately rather than as one monolith.",
        "strength_tag": "moderate",
        "why_now": "This mechanism has 69 papers, so narrowing scope is more useful than adding more volume.",
        "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701; 41179995; 41642456; 41648326; 41103638; 41508250",
        "next_test": "Split the next atlas pass into explicit NLRP3, TREM2/GAS6, and AQP4/glymphatic subtracks.",
        "blockers": "queue_burden",
        "operator_decision": "Needs adjudication",
        "decision_rationale": "This is the right narrowing move, but it still needs an explicit operator choice.",
        "unlocks": "Split the next pass into subtracks and evaluate each as its own hypothesis lane."
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "hypothesis_type": "translational_probe",
        "title": "Neuroinflammation / Microglial Activation translational probe hypothesis",
        "statement": "Modulating GFAP, IL10, IL1B may be the fastest translational probe for neuroinflammation / microglial activation in this atlas version.",
        "strength_tag": "moderate",
        "why_now": "These are the most actionable targets/entities currently attached to this mechanism.",
        "supporting_pmids": "",
        "next_test": "Prioritize enrichment and literature checks for GFAP, IL10, IL1B before expanding to a wider target set.",
        "blockers": "compound/trial depth is still limited",
        "operator_decision": "Needs enrichment",
        "decision_rationale": "The mechanism is interesting, but the translational layer is still too thin.",
        "unlocks": "Fill target, compound, and trial support before promoting this beyond a probe idea."
      }
    ],
    "by_mechanism": {
      "blood_brain_barrier_disruption": [
        {
          "canonical_mechanism": "blood_brain_barrier_disruption",
          "display_name": "Blood-Brain Barrier Dysfunction",
          "hypothesis_type": "cross_mechanism_bridge",
          "title": "Blood-Brain Barrier Dysfunction \u2192 Neuroinflammation / Microglial Activation bridge hypothesis",
          "statement": "Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI.",
          "strength_tag": "moderate",
          "why_now": "This bridge is already explicit in the synthesis packet, so it is ready to be used as a causal demo path.",
          "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
          "next_test": "Use the cross-mechanism chain to test whether Blood-Brain Barrier Dysfunction should be framed as upstream of Neuroinflammation / Microglial Activation.",
          "blockers": "upgrade_source:2",
          "operator_decision": "Needs adjudication",
          "decision_rationale": "This bridge shapes the atlas architecture, so it needs explicit confirmation.",
          "unlocks": "Use full-text anchors to confirm whether the upstream/downstream framing should hold."
        },
        {
          "canonical_mechanism": "blood_brain_barrier_disruption",
          "display_name": "Blood-Brain Barrier Dysfunction",
          "hypothesis_type": "mechanistic_driver",
          "title": "Blood-Brain Barrier Dysfunction driver hypothesis",
          "statement": "SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. TBI-induced BBB breakdown promotes neuroinflammation. Neutrophil-derived exosomes disrupt BBB integrity.",
          "strength_tag": "assertive",
          "why_now": "ready_now for idea generation with 25 papers and 6 queue items.",
          "supporting_pmids": "41859452; 41446731; 41660351; 41752185; 41756282; 41683989; 41673382; 41801080; 41765742; 41786390; 41532955; 41748851; 41863251; 41039850",
          "next_test": "Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.",
          "blockers": "Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
          "operator_decision": "Write now",
          "decision_rationale": "This is strong enough to anchor prose now.",
          "unlocks": "Advance the mechanism into the chapter draft and keep the blocker notes attached."
        },
        {
          "canonical_mechanism": "blood_brain_barrier_disruption",
          "display_name": "Blood-Brain Barrier Dysfunction",
          "hypothesis_type": "translational_probe",
          "title": "Blood-Brain Barrier Dysfunction translational probe hypothesis",
          "statement": "Modulating AQP4, CLDN5, MMP9 may be the fastest translational probe for blood-brain barrier dysfunction in this atlas version.",
          "strength_tag": "moderate",
          "why_now": "These are the most actionable targets/entities currently attached to this mechanism.",
          "supporting_pmids": "",
          "next_test": "Prioritize enrichment and literature checks for AQP4, CLDN5, MMP9 before expanding to a wider target set.",
          "blockers": "compound/trial depth is still limited",
          "operator_decision": "Needs enrichment",
          "decision_rationale": "The mechanism is interesting, but the translational layer is still too thin.",
          "unlocks": "Fill target, compound, and trial support before promoting this beyond a probe idea."
        }
      ],
      "mitochondrial_bioenergetic_dysfunction": [
        {
          "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
          "display_name": "Mitochondrial Dysfunction",
          "hypothesis_type": "mechanistic_driver",
          "title": "Mitochondrial Dysfunction driver hypothesis",
          "statement": "Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI. MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits.",
          "strength_tag": "moderate",
          "why_now": "ready_now for idea generation with 22 papers and 5 queue items.",
          "supporting_pmids": "41651694; 41737534; 41867877; 41623705; 41267966; 41480492; 41648326; 41735605; 41737251; 41648607; 41709427",
          "next_test": "Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.",
          "blockers": "Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
          "operator_decision": "Needs adjudication",
          "decision_rationale": "The driver story is usable, but the narrative still needs a bounded scientific pass.",
          "unlocks": "Pressure-test the strongest anchors and decide what language stays assertive versus cautionary."
        },
        {
          "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
          "display_name": "Mitochondrial Dysfunction",
          "hypothesis_type": "translational_probe",
          "title": "Mitochondrial Dysfunction translational probe hypothesis",
          "statement": "Modulating CAT, CYBB, KNG1 may be the fastest translational probe for mitochondrial dysfunction in this atlas version.",
          "strength_tag": "moderate",
          "why_now": "These are the most actionable targets/entities currently attached to this mechanism.",
          "supporting_pmids": "",
          "next_test": "Prioritize enrichment and literature checks for CAT, CYBB, KNG1 before expanding to a wider target set.",
          "blockers": "compound/trial depth is still limited",
          "operator_decision": "Needs enrichment",
          "decision_rationale": "The mechanism is interesting, but the translational layer is still too thin.",
          "unlocks": "Fill target, compound, and trial support before promoting this beyond a probe idea."
        }
      ],
      "neuroinflammation_microglial_activation": [
        {
          "canonical_mechanism": "neuroinflammation_microglial_activation",
          "display_name": "Neuroinflammation / Microglial Activation",
          "hypothesis_type": "cross_mechanism_bridge",
          "title": "Neuroinflammation / Microglial Activation \u2192 Blood-Brain Barrier Dysfunction bridge hypothesis",
          "statement": "The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism.",
          "strength_tag": "moderate",
          "why_now": "This bridge is already explicit in the synthesis packet, so it is ready to be used as a causal demo path.",
          "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
          "next_test": "Use the cross-mechanism chain to test whether Neuroinflammation / Microglial Activation should be framed as upstream of Blood-Brain Barrier Dysfunction.",
          "blockers": "upgrade_source:2",
          "operator_decision": "Needs adjudication",
          "decision_rationale": "This bridge shapes the atlas architecture, so it needs explicit confirmation.",
          "unlocks": "Use full-text anchors to confirm whether the upstream/downstream framing should hold."
        },
        {
          "canonical_mechanism": "neuroinflammation_microglial_activation",
          "display_name": "Neuroinflammation / Microglial Activation",
          "hypothesis_type": "mechanistic_driver",
          "title": "Neuroinflammation / Microglial Activation driver hypothesis",
          "statement": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting in the accumulation of tau protein, S100\u03b2, glial fibrillary acidic protein (GFAP), and neuron-specific enolase (NSE), which promotes neurofibrillary pathology, neuroinflammation, and neurodegeneration. GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
          "strength_tag": "moderate",
          "why_now": "ready_now for idea generation with 69 papers and 17 queue items.",
          "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701; 41179995; 41642456; 41648326; 41103638; 41508250; 41612383; 41824127; 41618372; 41625091",
          "next_test": "Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.",
          "blockers": "Open blockers: needs deeper extraction 1, needs source upgrade 1, needs adjudication 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
          "operator_decision": "Needs adjudication",
          "decision_rationale": "The driver story is usable, but the narrative still needs a bounded scientific pass.",
          "unlocks": "Pressure-test the strongest anchors and decide what language stays assertive versus cautionary."
        },
        {
          "canonical_mechanism": "neuroinflammation_microglial_activation",
          "display_name": "Neuroinflammation / Microglial Activation",
          "hypothesis_type": "subtrack_narrowing",
          "title": "Neuroinflammation should be split into narrower lanes",
          "statement": "The neuroinflammation bucket is likely hiding multiple distinct idea lanes: inflammasome/cytokine signaling, microglial state transition, and glymphatic/astroglial response should be evaluated separately rather than as one monolith.",
          "strength_tag": "moderate",
          "why_now": "This mechanism has 69 papers, so narrowing scope is more useful than adding more volume.",
          "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701; 41179995; 41642456; 41648326; 41103638; 41508250",
          "next_test": "Split the next atlas pass into explicit NLRP3, TREM2/GAS6, and AQP4/glymphatic subtracks.",
          "blockers": "queue_burden",
          "operator_decision": "Needs adjudication",
          "decision_rationale": "This is the right narrowing move, but it still needs an explicit operator choice.",
          "unlocks": "Split the next pass into subtracks and evaluate each as its own hypothesis lane."
        },
        {
          "canonical_mechanism": "neuroinflammation_microglial_activation",
          "display_name": "Neuroinflammation / Microglial Activation",
          "hypothesis_type": "translational_probe",
          "title": "Neuroinflammation / Microglial Activation translational probe hypothesis",
          "statement": "Modulating GFAP, IL10, IL1B may be the fastest translational probe for neuroinflammation / microglial activation in this atlas version.",
          "strength_tag": "moderate",
          "why_now": "These are the most actionable targets/entities currently attached to this mechanism.",
          "supporting_pmids": "",
          "next_test": "Prioritize enrichment and literature checks for GFAP, IL10, IL1B before expanding to a wider target set.",
          "blockers": "compound/trial depth is still limited",
          "operator_decision": "Needs enrichment",
          "decision_rationale": "The mechanism is interesting, but the translational layer is still too thin.",
          "unlocks": "Fill target, compound, and trial support before promoting this beyond a probe idea."
        }
      ]
    }
  },
  "causal_chains": {
    "blood_brain_barrier_disruption": {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "display_name": "Blood-Brain Barrier Dysfunction",
      "thesis": {
        "statement": "SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This is reinforced by evidence that neutrophil-derived exosomes disrupt BBB integrity. The current atlas also places BBB disruption upstream of at least part of the inflammatory response.",
        "supporting_pmids": "41859452; 41446731; 41660351; 41752185; 41756282",
        "strength_tag": "assertive"
      },
      "steps": [
        {
          "atlas_layer": "early_molecular_cascade",
          "statement": "SCFAs cross the BBB and inhibit HDACs to promote neuroprotection.",
          "supporting_pmids": "41859452; 41446731; 41660351; 41752185; 41756282",
          "strength_tag": "assertive",
          "confidence_bucket": "stable",
          "write_status": "ready_to_write"
        },
        {
          "atlas_layer": "cellular_response",
          "statement": "TBI-induced BBB breakdown promotes neuroinflammation.",
          "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
          "strength_tag": "moderate",
          "confidence_bucket": "provisional",
          "write_status": "write_with_caution"
        },
        {
          "atlas_layer": "tissue_network_consequence",
          "statement": "Neutrophil-derived exosomes disrupt BBB integrity.",
          "supporting_pmids": "41532955; 41748851; 41752185; 41863251; 41039850",
          "strength_tag": "assertive",
          "confidence_bucket": "stable",
          "write_status": "ready_to_write"
        }
      ],
      "bridges": [
        {
          "statement": "Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI.",
          "related_mechanisms": "neuroinflammation_microglial_activation",
          "related_display_name": "Neuroinflammation / Microglial Activation",
          "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
          "strength_tag": "moderate"
        }
      ],
      "translational_hooks": [
        {
          "statement": "Translational hook: AQP4",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        },
        {
          "statement": "Translational hook: CLDN5",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        },
        {
          "statement": "Translational hook: MMP9",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        }
      ],
      "subtracks": [],
      "caveat": {
        "statement": "Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
        "strength_tag": "moderate"
      },
      "next_action": "Upgrade the abstract-only support rows before locking final prose."
    },
    "mitochondrial_bioenergetic_dysfunction": {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "display_name": "Mitochondrial Dysfunction",
      "thesis": {
        "statement": "MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis.",
        "supporting_pmids": "41651694; 41737534; 41867877; 41623705; 41267966",
        "strength_tag": "moderate"
      },
      "steps": [
        {
          "atlas_layer": "early_molecular_cascade",
          "statement": "Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI.",
          "supporting_pmids": "41651694; 41737534; 41867877; 41623705; 41267966",
          "strength_tag": "moderate",
          "confidence_bucket": "provisional",
          "write_status": "write_with_caution"
        },
        {
          "atlas_layer": "cellular_response",
          "statement": "MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis.",
          "supporting_pmids": "41480492; 41648326; 41651694; 41735605; 41737251",
          "strength_tag": "assertive",
          "confidence_bucket": "stable",
          "write_status": "ready_to_write"
        },
        {
          "atlas_layer": "tissue_network_consequence",
          "statement": "Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits.",
          "supporting_pmids": "41651694; 41648607; 41735605; 41737534; 41709427",
          "strength_tag": "moderate",
          "confidence_bucket": "provisional",
          "write_status": "write_with_caution"
        }
      ],
      "bridges": [],
      "translational_hooks": [
        {
          "statement": "Translational hook: CAT",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        },
        {
          "statement": "Translational hook: CYBB",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        },
        {
          "statement": "Translational hook: KNG1",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        }
      ],
      "subtracks": [],
      "caveat": {
        "statement": "Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
        "strength_tag": "moderate"
      },
      "next_action": "Upgrade the abstract-only support rows before locking final prose."
    },
    "neuroinflammation_microglial_activation": {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "display_name": "Neuroinflammation / Microglial Activation",
      "thesis": {
        "statement": "Neuroinflammation is better handled as narrower starter lanes than as one broad block: NLRP3 / Cytokine lane, Microglial state-transition lane, AQP4 / Glymphatic / Astroglial lane. The current strongest lane indicates that microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. A second lane captures that GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
        "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701",
        "strength_tag": "moderate"
      },
      "steps": [
        {
          "atlas_layer": "early_molecular_cascade",
          "statement": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release.",
          "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701",
          "strength_tag": "moderate",
          "confidence_bucket": "provisional",
          "write_status": "write_with_caution"
        },
        {
          "atlas_layer": "cellular_response",
          "statement": "GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
          "supporting_pmids": "41612383; 41737534; 41824127; 41618372; 41625091",
          "strength_tag": "moderate",
          "confidence_bucket": "provisional",
          "write_status": "write_with_caution"
        },
        {
          "atlas_layer": "early_molecular_cascade",
          "statement": "Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting in the accumulation of tau protein, S100\u03b2, glial fibrillary acidic protein (GFAP), and neuron-specific enolase (NSE), which promotes neurofibrillary pathology, neuroinflammation, and neurodegeneration.",
          "supporting_pmids": "41179995; 41642456; 41648326; 41103638; 41508250",
          "strength_tag": "speculative",
          "confidence_bucket": "hold",
          "write_status": "hold"
        },
        {
          "atlas_layer": "tissue_network_consequence",
          "statement": "NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery.",
          "supporting_pmids": "41622228; 41648607; 41792174; 41867797; 41612383",
          "strength_tag": "assertive",
          "confidence_bucket": "stable",
          "write_status": "ready_to_write"
        }
      ],
      "bridges": [
        {
          "statement": "The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism.",
          "related_mechanisms": "blood_brain_barrier_disruption",
          "related_display_name": "Blood-Brain Barrier Dysfunction",
          "supporting_pmids": "41683989; 41673382; 41801080; 41765742; 41786390",
          "strength_tag": "moderate"
        }
      ],
      "translational_hooks": [
        {
          "statement": "Translational hook: GFAP",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        },
        {
          "statement": "Translational hook: IL10",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        },
        {
          "statement": "Translational hook: IL1B",
          "supporting_pmids": "",
          "strength_tag": "moderate"
        }
      ],
      "subtracks": [
        {
          "name": "NLRP3 / Cytokine lane",
          "statement": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release.",
          "supporting_pmids": "41737534; 41683989; 41880282; 41734021; 41853701",
          "strength_tag": "moderate"
        },
        {
          "name": "Microglial state-transition lane",
          "statement": "GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
          "supporting_pmids": "41612383; 41737534; 41824127; 41618372; 41625091",
          "strength_tag": "moderate"
        },
        {
          "name": "AQP4 / Glymphatic / Astroglial lane",
          "statement": "Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting in the accumulation of tau protein, S100\u03b2, glial fibrillary acidic protein (GFAP), and neuron-specific enolase (NSE), which promotes neurofibrillary pathology, neuroinflammation, and neurodegeneration.",
          "supporting_pmids": "41179995; 41642456; 41648326; 41103638; 41508250",
          "strength_tag": "speculative"
        }
      ],
      "caveat": {
        "statement": "Open blockers: needs deeper extraction 1, needs source upgrade 1, needs adjudication 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.",
        "strength_tag": "moderate"
      },
      "next_action": "Upgrade the abstract-only support rows before locking final prose."
    }
  },
  "execution_map": [
    {
      "id": "daily-machine-loop",
      "title": "Daily machine refresh",
      "cadence": "Daily at 8:00 AM Central",
      "trigger": "Runs automatically on GitHub Actions.",
      "operator_decision": "No weekly decision required unless the Saturday brief shows a blocker spike or topic drift.",
      "workflow_or_command": "GitHub workflows: ongoing_literature_cycle.yml -> refresh_atlas_from_ongoing_cycle.yml -> refresh_public_enrichment.yml",
      "unlocks": "Fresh corpus, fresh extraction, fresh atlas, fresh dashboard snapshot.",
      "actions": [
        {
          "label": "Open daily workflow",
          "href": "https://github.com/matthewdholtkamp/testfile/actions/workflows/ongoing_literature_cycle.yml",
          "kind": "workflow"
        },
        {
          "label": "Open atlas refresh workflow",
          "href": "https://github.com/matthewdholtkamp/testfile/actions/workflows/refresh_atlas_from_ongoing_cycle.yml",
          "kind": "workflow"
        },
        {
          "label": "Open public enrichment workflow",
          "href": "https://github.com/matthewdholtkamp/testfile/actions/workflows/refresh_public_enrichment.yml",
          "kind": "workflow"
        }
      ]
    },
    {
      "id": "saturday-control-surface",
      "title": "Saturday decision brief",
      "cadence": "Weekly on Saturday",
      "trigger": "Read the Decision Brief at the top of the Atlas Viewer.",
      "operator_decision": "Choose whether to keep Blood-Brain Barrier Dysfunction as the lead mechanism and approve the next curation queue.",
      "workflow_or_command": "GitHub workflow: weekly_human_review_packet.yml",
      "unlocks": "Keeps the weekly human pass bounded to 1-2 pages of decisions instead of full-report review.",
      "actions": [
        {
          "label": "Open Saturday workflow",
          "href": "https://github.com/matthewdholtkamp/testfile/actions/workflows/weekly_human_review_packet.yml",
          "kind": "workflow"
        },
        {
          "label": "Open atlas book",
          "href": "../atlas-book/index.html",
          "kind": "view"
        }
      ]
    },
    {
      "id": "manual-enrichment-cycle",
      "title": "Manual enrichment pass",
      "cadence": "When BBB / mitochondrial targets need stronger translational support",
      "trigger": "Use this after approving top BBB and mitochondrial targets.",
      "operator_decision": "Accept the target queue and fill the ChEMBL/Open Targets rows for the chosen targets.",
      "workflow_or_command": "Local command: python3 scripts/run_manual_enrichment_cycle.py --default-to-auto",
      "unlocks": "Stronger release readiness for BBB and mitochondrial chapters. Current BBB release bucket: core_atlas_candidate.",
      "actions": [
        {
          "label": "Open target packet index",
          "href": "",
          "kind": "local"
        },
        {
          "label": "Open ChEMBL template",
          "href": "",
          "kind": "local"
        },
        {
          "label": "Open Open Targets template",
          "href": "",
          "kind": "local"
        }
      ]
    },
    {
      "id": "idea-generation-pass",
      "title": "Idea-generation pass",
      "cadence": "Any time all starter mechanisms remain idea-ready",
      "trigger": "Current readiness: 3 mechanism(s) idea-ready.",
      "operator_decision": "Decide which candidate ideas deserve immediate writing, enrichment, or narrowing.",
      "workflow_or_command": "Generated artifact + dashboard section: reports/hypothesis_candidates + Atlas Viewer > Candidate Ideas",
      "unlocks": "Moves the atlas from structured synthesis into explicit hypothesis lanes.",
      "actions": [
        {
          "label": "Open hypothesis candidates",
          "href": "../../reports/hypothesis_candidates/hypothesis_candidates_2026-03-28_013915.json",
          "kind": "local"
        },
        {
          "label": "Open chapter synthesis draft",
          "href": "../../reports/atlas_chapter_synthesis_draft/starter_atlas_chapter_synthesis_draft_2026-03-28_013915.md",
          "kind": "local"
        }
      ]
    },
    {
      "id": "neuro-narrowing-pass",
      "title": "Neuroinflammation narrowing",
      "cadence": "When breadth is limiting clarity",
      "trigger": "Use this when neuroinflammation remains broad with queue burden 17.",
      "operator_decision": "Approve tighter subtracks instead of adding more broad neuro papers.",
      "workflow_or_command": "Targeted action: treat NLRP3, TREM2/GAS6, and AQP4/glymphatic response as separate subtracks in the next atlas pass.",
      "unlocks": "Makes neuroinflammation more hypothesis-generative and less diffuse.",
      "actions": [
        {
          "label": "Open review packets",
          "href": "../../reports/mechanism_review_packets/mechanism_review_packet_index_2026-03-28_013915.md",
          "kind": "local"
        },
        {
          "label": "Open target packet index",
          "href": "",
          "kind": "local"
        }
      ]
    },
    {
      "id": "tenx-import-lane",
      "title": "Optional 10x import lane",
      "cadence": "Only when real 10x outputs exist",
      "trigger": "Use once actual 10x exports are available this week.",
      "operator_decision": "Decide whether real genomics exports are ready to import.",
      "workflow_or_command": "Local sidecar path: drop 10x exports into local_connector_inputs and rerun python3 scripts/run_connector_sidecar.py --build-tenx-template",
      "unlocks": "Adds cell-type and pathway evidence without blocking the core atlas. Current mitochondrial release bucket: hold.",
      "actions": [
        {
          "label": "Open 10x template",
          "href": "../../reports/connector_candidate_manifest/templates/tenx_genomics_import_template_2026-03-28_013712.csv",
          "kind": "local"
        },
        {
          "label": "Open connector guide",
          "href": "../../CONNECTOR_ENRICHMENT.md",
          "kind": "local"
        }
      ]
    }
  ]
};

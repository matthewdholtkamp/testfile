window.ATLAS_VIEWER_DATA = {
  "metadata": {
    "generated_from": {
      "index": "reports/mechanism_dossiers/mechanism_dossier_index_2026-03-26_001414.md",
      "chapter": "reports/atlas_chapter_draft/starter_atlas_chapter_draft_2026-03-26_001414.md",
      "chapter_synthesis": "reports/atlas_chapter_synthesis_draft/starter_atlas_chapter_synthesis_draft_2026-03-26_001414.md",
      "ledger": "reports/atlas_chapter_ledger/starter_atlas_chapter_evidence_ledger_2026-03-26_001414.csv",
      "workpack": "",
      "bridge": "reports/mechanism_dossiers/translational_bridge_2026-03-26_001414.csv",
      "release_manifest": "reports/atlas_release_manifest/atlas_release_manifest_2026-03-26_001414.json",
      "decision_brief": "reports/weekly_human_review_packet/weekly_human_review_packet_2026-03-26_003627.json"
    }
  },
  "summary": {
    "lead_mechanism": "Blood-Brain Barrier Dysfunction",
    "stable_rows": 5,
    "provisional_rows": 4,
    "blocked_rows": 2,
    "mechanism_count": 3,
    "top_priority": ""
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
        "Target enrichment not yet populated."
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
        "No target-association enrichment has been added yet.",
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
      "raw_markdown": "# Mechanism Dossier: Blood-Brain Barrier Dysfunction\n\n- Canonical mechanism: `blood_brain_barrier_disruption`\n- Promotion status: `near_ready`\n- Promotion reason: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n## Overview\n\n- Papers in packet: `25`\n- Claim rows: `29`\n- Source quality mix: `full_text_like` 20, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 19, `upgrade_source` 5, `deepen_extraction` 1\n\n## Weighted Anchor Papers\n\n| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |\n| --- | --- | --- | --- | --- |\n| 41859452 | full_text_like | high_signal | 5.0 | SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. |\n| 41683989 | full_text_like | high_signal | 4.0 | TBI-induced BBB breakdown promotes neuroinflammation. |\n| 41446731 | full_text_like | high_signal | 4.0 | rmTBI causes acute BBB disruption via downregulation of ZO-1 and claudin-5. |\n| 41532955 | full_text_like | high_signal | 4.0 | Neutrophil-derived exosomes disrupt BBB integrity. |\n| 41660351 | full_text_like | high_signal | 4.0 | CSD causes spreading ischemia through inverse neurovascular coupling in vulnerable cortex. |\n| 41698173 | full_text_like | high_signal | 4.0 | Blood-brain barrier disruption facilitates CNS-to-saliva protein transfer. |\n| 41748851 | full_text_like | high_signal | 4.0 | Cerebrovascular architecture influences individual susceptibility to TBI-induced network dysfunction. |\n| 41752185 | full_text_like | high_signal | 4.0 | MMP-9 upregulation mediates delayed BBB breakdown. |\n| 41752185 | full_text_like | high_signal | 4.0 | Downregulation of tight junction proteins drives early BBB permeability. |\n| 41756282 | full_text_like | high_signal | 4.0 | IL-1R1 signaling mediates acute TBI neuroinflammation and BBB breakdown. |\n\n## Strongest Atlas-Layer Rows\n\n| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- |\n| early_molecular_cascade | 12 | 10 | 2 | 3.667 | 41859452; 41446731; 41660351; 41752185; 41756282 |\n| tissue_network_consequence | 8 | 7 | 1 | 3.75 | 41532955; 41748851; 41752185; 41863251; 41039850 |\n| cellular_response | 5 | 3 | 2 | 3.5 | 41683989; 41673382; 41801080; 41765742; 41786390 |\n| trigger_primary_injury | 2 | 2 | 0 | 3.5 | 41698173; 41649131 |\n| clinical_chronic_phenotype | 1 | 1 | 0 | 3.0 | 41762323 |\n\n## Contradiction / Tension Shortlist\n\n- MMP-9 -> disrupts -> BBB | support_only | PMIDs: 41465583; 41801080\n\n## Biomarker Summary\n\n- FITC-labeled mNGF fluorescence: `1` claim mentions\n- Optical density (OD) readings: `1` claim mentions\n- Cerebral blood flow (CBF): `1` claim mentions\n- Claudin-5 expression: `1` claim mentions\n- Evans blue content: `1` claim mentions\n- Occludin expression: `1` claim mentions\n- ZO-1 expression: `1` claim mentions\n- gadolinium leakage: `1` claim mentions\n\n## Target Summary\n\n- Target enrichment not yet populated.\n\n## Therapeutic / Compound Summary\n\n- Compound/mechanism enrichment not yet populated.\n\n## Active Trial Summary\n\n- Trial landscape not yet populated.\n\n## Preprint Watchlist\n\n- Preprint watchlist not yet populated.\n\n## 10x / Genomics Expression Signals\n\n- 10x or other genomics-expression enrichment not yet populated.\n\n## Open Questions / Evidence Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No target-association enrichment has been added yet.\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n\n## Remaining Work Queue\n\n- upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41622481 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41740873 | abstract_only | abstract-only source limits mechanistic confidence\n- deepen_extraction: PMID 41762323 | full_text_like | full-text paper is captured but still shallow for investigation use\n- upgrade_source: PMID 41765742 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41786390 | abstract_only | abstract-only source limits mechanistic confidence\n",
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "promotion_status": "near_ready",
      "papers": 25,
      "queue_burden": 6,
      "target_rows": 0,
      "compound_rows": 0,
      "trial_rows": 0,
      "preprint_rows": 0,
      "genomics_rows": 0
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
        "Papers in packet: `20`",
        "Claim rows: `27`",
        "Source quality mix: `full_text_like` 15, `abstract_only` 5",
        "Action lanes: `core_atlas_candidate` 15, `upgrade_source` 5"
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
          "Atlas Layer": "early_molecular_cascade",
          "Papers": "11",
          "Full-text-like": "8",
          "Abstract-only": "3",
          "Avg Depth": "3.5",
          "Anchor PMIDs": "41651694; 41737534; 41867877; 41623705; 41267966"
        },
        {
          "Atlas Layer": "cellular_response",
          "Papers": "8",
          "Full-text-like": "7",
          "Abstract-only": "1",
          "Avg Depth": "4.0",
          "Anchor PMIDs": "41480492; 41648326; 41651694; 41735605; 41737251"
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
        "CAT via open_targets"
      ],
      "therapeutics": [
        "Compound/mechanism enrichment not yet populated."
      ],
      "trials": [
        "Correcting Platelet Dysfunction After Traumatic Brain Injury (COMPLETED | Platelet mapping Thromboelastography) via clinicaltrials_gov"
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
      "raw_markdown": "# Mechanism Dossier: Mitochondrial Dysfunction\n\n- Canonical mechanism: `mitochondrial_bioenergetic_dysfunction`\n- Promotion status: `near_ready`\n- Promotion reason: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n## Overview\n\n- Papers in packet: `20`\n- Claim rows: `27`\n- Source quality mix: `full_text_like` 15, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 15, `upgrade_source` 5\n\n## Weighted Anchor Papers\n\n| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |\n| --- | --- | --- | --- | --- |\n| 41480492 | full_text_like | high_signal | 5.0 | MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. |\n| 41651694 | full_text_like | high_signal | 4.0 | Parkin overexpression alleviates TNI-induced neurotoxicity, apoptosis, and mitochondrial dysfunction. |\n| 41651694 | full_text_like | high_signal | 4.0 | Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits. |\n| 41648326 | full_text_like | high_signal | 4.0 | TBI causes neuronal mitochondrial morphological changes. |\n| 41648607 | full_text_like | high_signal | 4.0 | rmTBI skull secretome induces neurometabolic inflexibility. |\n| 41651694 | full_text_like | high_signal | 4.0 | Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI. |\n| 41735605 | full_text_like | high_signal | 4.0 | ER stress leads to mitochondrial dysfunction via mitophagy. |\n| 41735605 | full_text_like | high_signal | 4.0 | Mitochondrial dysfunction drives neuronal death. |\n| 41737251 | full_text_like | high_signal | 4.0 | KNG1 knockdown attenuates oxidative stress. |\n| 41737534 | full_text_like | high_signal | 4.0 | NOX2 inhibition is neuroprotective in TBI. |\n\n## Strongest Atlas-Layer Rows\n\n| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- |\n| early_molecular_cascade | 11 | 8 | 3 | 3.5 | 41651694; 41737534; 41867877; 41623705; 41267966 |\n| cellular_response | 8 | 7 | 1 | 4.0 | 41480492; 41648326; 41651694; 41735605; 41737251 |\n| tissue_network_consequence | 5 | 4 | 1 | 3.8 | 41651694; 41648607; 41735605; 41737534; 41709427 |\n\n## Contradiction / Tension Shortlist\n\n- No contradiction or tension cues were detected for this mechanism subset.\n\n## Biomarker Summary\n\n- CAT: `1` claim mentions\n- ROS: `1` claim mentions\n- SOD: `1` claim mentions\n- OSI: `1` claim mentions\n- TAS: `1` claim mentions\n- TOS: `1` claim mentions\n- ClO-: `1` claim mentions\n- ONOO-: `1` claim mentions\n\n## Target Summary\n\n- CAT via open_targets\n\n## Therapeutic / Compound Summary\n\n- Compound/mechanism enrichment not yet populated.\n\n## Active Trial Summary\n\n- Correcting Platelet Dysfunction After Traumatic Brain Injury (COMPLETED | Platelet mapping Thromboelastography) via clinicaltrials_gov\n\n## Preprint Watchlist\n\n- Preprint watchlist not yet populated.\n\n## 10x / Genomics Expression Signals\n\n- 10x or other genomics-expression enrichment not yet populated.\n\n## Open Questions / Evidence Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n\n## Remaining Work Queue\n\n- upgrade_source: PMID 41636499 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41642156 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41709427 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41773418 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41779627 | abstract_only | abstract-only source limits mechanistic confidence\n",
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "promotion_status": "near_ready",
      "papers": 20,
      "queue_burden": 5,
      "target_rows": 1,
      "compound_rows": 0,
      "trial_rows": 1,
      "preprint_rows": 0,
      "genomics_rows": 0
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
        "Papers in packet: `67`",
        "Claim rows: `95`",
        "Source quality mix: `full_text_like` 55, `abstract_only` 12",
        "Action lanes: `core_atlas_candidate` 50, `upgrade_source` 11, `deepen_extraction` 5, `manual_review` 1"
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
        },
        {
          "PMID": "41642456",
          "Source Quality": "full_text_like",
          "Quality Bucket": "high_signal",
          "Avg Depth": "4.0",
          "Example Claim": "Mechanical stretch induces dose-dependent astrocyte dysfunction."
        }
      ],
      "atlas_layers": [
        {
          "Atlas Layer": "cellular_response",
          "Papers": "46",
          "Full-text-like": "37",
          "Abstract-only": "9",
          "Avg Depth": "3.735",
          "Anchor PMIDs": "41612383; 41737534; 41859452; 41327381; 41642456"
        },
        {
          "Atlas Layer": "early_molecular_cascade",
          "Papers": "29",
          "Full-text-like": "27",
          "Abstract-only": "2",
          "Avg Depth": "3.8",
          "Anchor PMIDs": "41737534; 41179995; 41622228; 41683989; 41642456"
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
        "IL-10: `2` claim mentions",
        "IL-6: `2` claim mentions",
        "IL-1\u03b2: `2` claim mentions",
        "C3: `2` claim mentions",
        "pro-inflammatory cytokines (IL-1\u03b2, IL-6, TNF-\u03b1): `1` claim mentions",
        "RAGE: `1` claim mentions",
        "S100B (blood): `1` claim mentions"
      ],
      "targets": [
        "GFAP via open_targets",
        "IL10 via open_targets",
        "IL6 via open_targets"
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
      "raw_markdown": "# Mechanism Dossier: Neuroinflammation / Microglial Activation\n\n- Canonical mechanism: `neuroinflammation_microglial_activation`\n- Promotion status: `hold`\n- Promotion reason: mechanism still needs more deepening, cleanup, or translational context\n\n## Overview\n\n- Papers in packet: `67`\n- Claim rows: `95`\n- Source quality mix: `full_text_like` 55, `abstract_only` 12\n- Action lanes: `core_atlas_candidate` 50, `upgrade_source` 11, `deepen_extraction` 5, `manual_review` 1\n\n## Weighted Anchor Papers\n\n| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |\n| --- | --- | --- | --- | --- |\n| 41612383 | full_text_like | high_signal | 5.0 | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. |\n| 41737534 | full_text_like | high_signal | 5.0 | TREM2 activation enhances microglial phagocytic clearance of pathological aggregates. |\n| 41737534 | full_text_like | high_signal | 5.0 | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. |\n| 41179995 | full_text_like | high_signal | 5.0 | Aquaporin-4 (AQP-4) genetic knock-out exacerbates post-traumatic brain injury (TBI) glymphatic dysfunction, resulting... |\n| 41622228 | full_text_like | high_signal | 5.0 | Neuronal IFN-beta activates microglial IFNAR-STAT1 axis. |\n| 41683989 | full_text_like | high_signal | 5.0 | NLRP3 inflammasome activation mediates TBI-induced tau pathology. |\n| 41859452 | full_text_like | high_signal | 5.0 | Gut-derived LPS activates microglial Piezo1 to drive synaptic pruning. |\n| 41327381 | full_text_like | high_signal | 4.0 | mTBI induces axonal degeneration and glial activation in tracts orthogonal to the rotation axis. |\n| 41622228 | full_text_like | high_signal | 4.0 | NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery. |\n| 41642456 | full_text_like | high_signal | 4.0 | Mechanical stretch induces dose-dependent astrocyte dysfunction. |\n\n## Strongest Atlas-Layer Rows\n\n| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |\n| --- | --- | --- | --- | --- | --- |\n| cellular_response | 46 | 37 | 9 | 3.735 | 41612383; 41737534; 41859452; 41327381; 41642456 |\n| early_molecular_cascade | 29 | 27 | 2 | 3.8 | 41737534; 41179995; 41622228; 41683989; 41642456 |\n| tissue_network_consequence | 9 | 7 | 2 | 3.556 | 41622228; 41648607; 41792174; 41867797; 41612383 |\n| clinical_chronic_phenotype | 2 | 2 | 0 | 4.0 | 41734021; 41756282 |\n\n## Contradiction / Tension Shortlist\n\n- HMGB1 -> drives -> TLR4 | support_only | PMIDs: 41756234; 41756282\n- NLRP3 inflammasome -> drives -> IL-1\u03b2 release | support_only | PMIDs: 41712436; 41737534\n\n## Biomarker Summary\n\n- GFAP: `8` claim mentions\n- IL-10: `2` claim mentions\n- IL-6: `2` claim mentions\n- IL-1\u03b2: `2` claim mentions\n- C3: `2` claim mentions\n- pro-inflammatory cytokines (IL-1\u03b2, IL-6, TNF-\u03b1): `1` claim mentions\n- RAGE: `1` claim mentions\n- S100B (blood): `1` claim mentions\n\n## Target Summary\n\n- GFAP via open_targets\n- IL10 via open_targets\n- IL6 via open_targets\n\n## Therapeutic / Compound Summary\n\n- Compound/mechanism enrichment not yet populated.\n\n## Active Trial Summary\n\n- Trial landscape not yet populated.\n\n## Preprint Watchlist\n\n- Preprint watchlist not yet populated.\n\n## 10x / Genomics Expression Signals\n\n- 10x or other genomics-expression enrichment not yet populated.\n\n## Open Questions / Evidence Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 11 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n\n## Remaining Work Queue\n\n- upgrade_source: PMID 41135688 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41617128 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41622461 | abstract_only | abstract-only source limits mechanistic confidence\n- manual_review: PMID 41643638 | abstract_only | needs review or has extraction/artifact uncertainty\n- deepen_extraction: PMID 41675431 | full_text_like | full-text paper is captured but still shallow for investigation use\n- deepen_extraction: PMID 41675841 | full_text_like | full-text paper is captured but still shallow for investigation use\n- upgrade_source: PMID 41690666 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41700019 | abstract_only | abstract-only source limits mechanistic confidence\n- upgrade_source: PMID 41702482 | abstract_only | abstract-only source limits mechanistic confidence\n",
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "promotion_status": "hold",
      "papers": 67,
      "queue_burden": 17,
      "target_rows": 3,
      "compound_rows": 0,
      "trial_rows": 0,
      "preprint_rows": 0,
      "genomics_rows": 0
    }
  ],
  "chapter": {
    "lead_mechanism": "Blood-Brain Barrier Dysfunction",
    "lead_recommendation": [
      "Lead mechanism for the first chapter: **Blood-Brain Barrier Dysfunction**",
      "Why now: status `near_ready`, queue burden `6`, target rows `0`, trial rows `0`.",
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
      "Treat neuroinflammation as the larger integrating mechanism but keep it partially scaffolded until queue burden falls."
    ],
    "immediate_follow_on": [
      "Add manual ChEMBL rows for the lead mechanism.",
      "Add targeted public-trial review for the lead mechanism to remove generic or weak trial matches.",
      "If 10x outputs become available, append them into the same dossier before locking the chapter narrative."
    ],
    "raw_markdown": "# Starter Atlas Chapter Draft\n\nThis draft is dossier-driven. It is meant to be the first real writing artifact assembled from the investigation engine, not from manually rereading the whole corpus.\n\n## Lead Recommendation\n\n- Lead mechanism for the first chapter: **Blood-Brain Barrier Dysfunction**\n- Why now: status `near_ready`, queue burden `6`, target rows `0`, trial rows `0`.\n- Interpretation: start the first chapter where the atlas backbone is coherent and the cleanup burden is still bounded.\n\n## Chapter Framing\n\n- Chapter objective: explain how the starter mechanisms organize early injury biology, downstream network consequences, and translational hooks in TBI.\n- Writing rule: treat full-text-like anchors as primary evidence and abstract-only rows as provisional support only.\n- Current scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation.\n\n## Blood-Brain Barrier Dysfunction\n\n- Promotion status: `near_ready`\n- Readout: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n### Current State\n\n- Papers in packet: `25`\n- Claim rows: `29`\n- Source quality mix: `full_text_like` 20, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 19, `upgrade_source` 5, `deepen_extraction` 1\n\n### Anchor Signals\n\n- | 41859452 | full_text_like | high_signal | 5.0 | SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. |\n- | 41683989 | full_text_like | high_signal | 4.0 | TBI-induced BBB breakdown promotes neuroinflammation. |\n- | 41446731 | full_text_like | high_signal | 4.0 | rmTBI causes acute BBB disruption via downregulation of ZO-1 and claudin-5. |\n\n### Backbone Rows\n\n- | early_molecular_cascade | 12 | 10 | 2 | 3.667 | 41859452; 41446731; 41660351; 41752185; 41756282 |\n- | tissue_network_consequence | 8 | 7 | 1 | 3.75 | 41532955; 41748851; 41752185; 41863251; 41039850 |\n- | cellular_response | 5 | 3 | 2 | 3.5 | 41683989; 41673382; 41801080; 41765742; 41786390 |\n\n### Translational / Enrichment Readout\n\n- Enrichment is still sparse for this mechanism.\n\n### Remaining Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No target-association enrichment has been added yet.\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- Work queue snapshot:\n  - upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41622481 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41740873 | abstract_only | abstract-only source limits mechanistic confidence\n  - deepen_extraction: PMID 41762323 | full_text_like | full-text paper is captured but still shallow for investigation use\n\n## Mitochondrial Dysfunction\n\n- Promotion status: `near_ready`\n- Readout: atlas backbone is usable but still needs bounded cleanup or enrichment\n\n### Current State\n\n- Papers in packet: `20`\n- Claim rows: `27`\n- Source quality mix: `full_text_like` 15, `abstract_only` 5\n- Action lanes: `core_atlas_candidate` 15, `upgrade_source` 5\n\n### Anchor Signals\n\n- | 41480492 | full_text_like | high_signal | 5.0 | MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. |\n- | 41651694 | full_text_like | high_signal | 4.0 | Parkin overexpression alleviates TNI-induced neurotoxicity, apoptosis, and mitochondrial dysfunction. |\n- | 41651694 | full_text_like | high_signal | 4.0 | Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits. |\n\n### Backbone Rows\n\n- | early_molecular_cascade | 11 | 8 | 3 | 3.5 | 41651694; 41737534; 41867877; 41623705; 41267966 |\n- | cellular_response | 8 | 7 | 1 | 4.0 | 41480492; 41648326; 41651694; 41735605; 41737251 |\n- | tissue_network_consequence | 5 | 4 | 1 | 3.8 | 41651694; 41648607; 41735605; 41737534; 41709427 |\n\n### Translational / Enrichment Readout\n\n- Target: CAT via open_targets\n- Trial: Correcting Platelet Dysfunction After Traumatic Brain Injury (COMPLETED | Platelet mapping Thromboelastography) via clinicaltrials_gov\n\n### Remaining Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 5 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n- Work queue snapshot:\n  - upgrade_source: PMID 41636499 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41642156 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41709427 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41773418 | abstract_only | abstract-only source limits mechanistic confidence\n\n## Neuroinflammation / Microglial Activation\n\n- Promotion status: `hold`\n- Readout: mechanism still needs more deepening, cleanup, or translational context\n\n### Current State\n\n- Papers in packet: `67`\n- Claim rows: `95`\n- Source quality mix: `full_text_like` 55, `abstract_only` 12\n- Action lanes: `core_atlas_candidate` 50, `upgrade_source` 11, `deepen_extraction` 5, `manual_review` 1\n\n### Anchor Signals\n\n- | 41612383 | full_text_like | high_signal | 5.0 | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. |\n- | 41737534 | full_text_like | high_signal | 5.0 | TREM2 activation enhances microglial phagocytic clearance of pathological aggregates. |\n- | 41737534 | full_text_like | high_signal | 5.0 | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. |\n\n### Backbone Rows\n\n- | cellular_response | 46 | 37 | 9 | 3.735 | 41612383; 41737534; 41859452; 41327381; 41642456 |\n- | early_molecular_cascade | 29 | 27 | 2 | 3.8 | 41737534; 41179995; 41622228; 41683989; 41642456 |\n- | tissue_network_consequence | 9 | 7 | 2 | 3.556 | 41622228; 41648607; 41792174; 41867797; 41612383 |\n\n### Translational / Enrichment Readout\n\n- Target: GFAP via open_targets\n- Target: IL10 via open_targets\n- Target: IL6 via open_targets\n\n### Remaining Gaps\n\n- Primary remaining queue pressure is `upgrade_source` with 11 paper(s).\n- No compound/mechanism enrichment has been added yet.\n- No active trial landscape has been added yet.\n- No preprint watchlist has been added yet.\n- No 10x or other genomics-expression enrichment has been added yet.\n- Work queue snapshot:\n  - upgrade_source: PMID 41135688 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41173520 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41617128 | abstract_only | abstract-only source limits mechanistic confidence\n  - upgrade_source: PMID 41622461 | abstract_only | abstract-only source limits mechanistic confidence\n\n## Writing Priority\n\n1. Draft the lead mechanism section in full.\n2. Use the second `near_ready` mechanism as the comparative chapter section.\n3. Treat neuroinflammation as the larger integrating mechanism but keep it partially scaffolded until queue burden falls.\n\n## Immediate Follow-on\n\n- Add manual ChEMBL rows for the lead mechanism.\n- Add targeted public-trial review for the lead mechanism to remove generic or weak trial matches.\n- If 10x outputs become available, append them into the same dossier before locking the chapter narrative.\n\n",
    "preview_markdown": "# Starter Atlas Chapter Synthesis Draft\n\nThis draft is evidence-first. It is built from the mechanistic synthesis packet, which itself is derived from the chapter evidence ledger rather than from dossier recap alone.\n\n## Lead Recommendation\n\n- Lead chapter mechanism: **Blood-Brain Barrier Dysfunction**\n- Writing rule: use `ready` rows as assertive prose, `caution` rows as bounded interpretation, and `hold` rows only as unresolved context.\n- Scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation.\n\n## Blood-Brain Barrier Dysfunction\n\nSCFAs cross the BBB and inhibit HDACs to promote neuroprotection. This is reinforced by evidence that neutrophil-derived exosomes disrupt BBB integrity. The current atlas also places BBB disruption upstream of at least part of the inflammatory response.\n\n### Causal Sequence\n\n- `early_molecular_cascade` | `ready` | SCFAs cross the BBB and inhibit HDACs to promote neuroprotection. | PMIDs: 41859452; 41446731; 41660351; 41752185; 41756282\n- `cellular_response` | `caution` | TBI-induced BBB breakdown promotes neuroinflammation. | PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n- `tissue_network_consequence` | `ready` | Neutrophil-derived exosomes disrupt BBB integrity. | PMIDs: 41532955; 41748851; 41752185; 41863251; 41039850\n\n### Cross-Mechanism Links\n\n- Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI. Related mechanism: Neuroinflammation / Microglial Activation. PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n\n### Evidence Boundaries\n\n- Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.\n\n### Translational Hooks\n\n- No translational hooks are attached yet.\n\n### Immediate Next Actions\n\n- Upgrade the abstract-only support rows before locking final prose.\n\n## Mitochondrial Dysfunction\n\nMAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis.\n\n### Causal Sequence\n\n- `early_molecular_cascade` | `caution` | Parkin promotes mitochondrial biogenesis and fission while inhibiting mitochondrial fusion post-TBI. | PMIDs: 41651694; 41737534; 41867877; 41623705; 41267966\n- `cellular_response` | `ready` | MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis. | PMIDs: 41480492; 41648326; 41651694; 41735605; 41737251\n- `tissue_network_consequence` | `caution` | Parkin knockout exacerbates CCI-induced brain damage, edema, and behavioral deficits. | PMIDs: 41651694; 41648607; 41735605; 41737534; 41709427\n\n### Cross-Mechanism Links\n\n- No mechanism bridge has reached writing-grade support yet.\n\n### Evidence Boundaries\n\n- Open blockers: needs source upgrade 1 Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.\n\n### Translational Hooks\n\n- Translational hook: CAT | Correcting Platelet Dysfunction After Traumatic Brain Injury (target_association; trial_landscape)\n\n### Immediate Next Actions\n\n- Upgrade the abstract-only support rows before locking final prose.\n\n## Neuroinflammation / Microglial Activation\n\nMicroglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. This is reinforced by evidence that NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery.\n\n### Causal Sequence\n\n- `early_molecular_cascade` | `ready` | Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release. | PMIDs: 41737534; 41179995; 41622228; 41683989; 41642456\n- `cellular_response` | `caution` | GAS6 in 3D-sEVs drives M1 to M2 microglial polarization. | PMIDs: 41612383; 41737534; 41859452; 41327381; 41642456\n- `tissue_network_consequence` | `ready` | NK cell depletion reduces neuroinflammation and improves sensorimotor/cognitive recovery. | PMIDs: 41622228; 41648607; 41792174; 41867797; 41612383\n\n### Cross-Mechanism Links\n\n- The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism. Related mechanism: Blood-Brain Barrier Dysfunction. PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n\n### Evidence Boundaries\n\n- Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.\n\n### Translational Hooks\n\n- Translational hook: GFAP (target_association)\n- Translational hook: IL10 (target_association)\n- Translational hook: IL6 (target_association)\n\n### Immediate Next Actions\n\n- Use the stable blocks as the first atlas-writing paragraph set and keep provisional rows as bounded support.\n\n## Cross-Mechanism Synthesis\n\n- The current atlas is strongest when it treats BBB dysfunction as an early vascular gate that can feed forward into later inflammatory biology.\n- Mitochondrial dysfunction remains the best comparative intracellular injury program, but it still needs a denser bridge into the broader inflammatory layer.\n- Neuroinflammation is better handled as an integrating response layer than as the lead chapter until more bridge rows and cleanup reduce its burden.\n\n### Explicit Bridge Statements\n\n- Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI. | PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n- The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism. | PMIDs: 41683989; 41673382; 41801080; 41765742; 41786390\n\n## Practical Follow-On\n\n- Keep the BBB section as the lead writing section.\n- Use mitochondrial dysfunction as the second section and keep its provisional rows clearly marked.\n- Treat neuroinflammation as the integrating downstream section rather than the opening chapter.\n- Finish the remaining BBB source upgrades before declaring the section locked.\n- Expand mitochondrial translational rows so the second section has a clearer intervention bridge.\n"
  },
  "ledger": [
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "mechanism_display_name": "Blood-Brain Barrier Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "atlas_layer": "early_molecular_cascade",
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
      "promotion_note": "ready to write"
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "mechanism_display_name": "Blood-Brain Barrier Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "atlas_layer": "tissue_network_consequence",
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
      "promotion_note": "ready to write"
    },
    {
      "canonical_mechanism": "blood_brain_barrier_disruption",
      "mechanism_display_name": "Blood-Brain Barrier Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "atlas_layer": "cellular_response",
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
      "promotion_note": "needs source upgrade"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "mechanism_display_name": "Mitochondrial Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "atlas_layer": "cellular_response",
      "paper_count": "8",
      "supporting_pmids": "41480492; 41648326; 41651694; 41735605; 41737251",
      "proposed_narrative_claim": "MAM-mediated Ca2+ overload drives mitochondrial-dependent apoptosis.",
      "best_anchor_claim_text": "Excessive Ca2+ influx at MAMs triggers mPTP opening, leading to cytochrome c release and caspase-3 activation.",
      "best_anchor_pmid": "41480492",
      "source_quality_mix": "full_text_like:7; abstract_only:1",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "mechanism_display_name": "Mitochondrial Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "atlas_layer": "early_molecular_cascade",
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
      "promotion_note": "ready to write"
    },
    {
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "mechanism_display_name": "Mitochondrial Dysfunction",
      "mechanism_promotion_status": "near_ready",
      "atlas_layer": "tissue_network_consequence",
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
      "promotion_note": "needs source upgrade"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "atlas_layer": "early_molecular_cascade",
      "paper_count": "29",
      "supporting_pmids": "41737534; 41179995; 41622228; 41683989; 41642456",
      "proposed_narrative_claim": "Microglial NLRP3 inflammasome activation promotes pro-inflammatory cytokine release.",
      "best_anchor_claim_text": "NLRP3 inflammasome activation in microglia drives caspase-1-mediated maturation of IL-1\u03b2 and IL-18, exacerbating neuroinflammation in AD and TBI.",
      "best_anchor_pmid": "41737534",
      "source_quality_mix": "full_text_like:27; abstract_only:2",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "stable",
      "promotion_note": "ready to write"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "atlas_layer": "tissue_network_consequence",
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
      "promotion_note": "ready to write"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "mechanism_display_name": "Neuroinflammation / Microglial Activation",
      "mechanism_promotion_status": "hold",
      "atlas_layer": "cellular_response",
      "paper_count": "46",
      "supporting_pmids": "41612383; 41737534; 41859452; 41327381; 41642456",
      "proposed_narrative_claim": "GAS6 in 3D-sEVs drives M1 to M2 microglial polarization.",
      "best_anchor_claim_text": "3D-sEVs promote M1 to M2 microglial polarization via GAS6 delivery.",
      "best_anchor_pmid": "41612383",
      "source_quality_mix": "full_text_like:37; abstract_only:9",
      "quality_mix": "high_signal:5",
      "contradiction_signal": "none_detected",
      "action_blockers": "none",
      "confidence_bucket": "provisional",
      "promotion_note": "ready to write"
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
      "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
      "biomarker_seed": "CAT",
      "target_entity": "CAT",
      "compound_entity": "",
      "trial_entity": "Correcting Platelet Dysfunction After Traumatic Brain Injury",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "clinicaltrials_gov; open_targets",
      "evidence_tiers": "target_association; trial_landscape",
      "provenance_ref": "ClinicalTrials.gov query.term=traumatic brain injury Mitochondrial Dysfunction; Open Targets search: CAT"
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
      "provenance_ref": "Open Targets search: GFAP"
    },
    {
      "canonical_mechanism": "neuroinflammation_microglial_activation",
      "biomarker_seed": "IL-10",
      "target_entity": "IL10",
      "compound_entity": "",
      "trial_entity": "",
      "preprint_entity": "",
      "genomics_entity": "",
      "connector_source": "open_targets",
      "evidence_tiers": "target_association",
      "provenance_ref": "Open Targets search: IL-10"
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
      "provenance_ref": "Open Targets search: IL-6"
    }
  ],
  "release_manifest": {
    "summary": {
      "lead_chapter_candidate": "Blood-Brain Barrier Dysfunction",
      "core_atlas_now": 0,
      "core_atlas_candidates": 0,
      "review_track": 1,
      "hold": 2
    },
    "rows": [
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "promotion_status": "near_ready",
        "readiness_score": "29",
        "gate_status": "write_with_caution",
        "stable_rows": "2",
        "provisional_rows": "1",
        "blocked_rows": "1",
        "bridge_rows": "1",
        "translational_hook_rows": "0",
        "queue_burden": "6",
        "target_rows": "0",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "review_track",
        "chapter_role": "lead_section",
        "recommended_action": "upgrade_remaining_abstract_support"
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "promotion_status": "hold",
        "readiness_score": "4",
        "gate_status": "hold",
        "stable_rows": "2",
        "provisional_rows": "1",
        "blocked_rows": "0",
        "bridge_rows": "1",
        "translational_hook_rows": "3",
        "queue_burden": "17",
        "target_rows": "3",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "none",
        "recommended_next_move": "add_target_and_compound_enrichment",
        "release_bucket": "hold",
        "chapter_role": "hold",
        "recommended_action": "add_target_and_compound_enrichment"
      },
      {
        "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
        "display_name": "Mitochondrial Dysfunction",
        "promotion_status": "near_ready",
        "readiness_score": "1",
        "gate_status": "hold",
        "stable_rows": "1",
        "provisional_rows": "2",
        "blocked_rows": "1",
        "bridge_rows": "0",
        "translational_hook_rows": "1",
        "queue_burden": "5",
        "target_rows": "1",
        "compound_rows": "0",
        "trial_rows": "1",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "hold",
        "chapter_role": "hold",
        "recommended_action": "upgrade_remaining_abstract_support"
      }
    ],
    "quality_gate_csv": "reports/atlas_quality_gate/atlas_quality_gate_2026-03-26_001414.csv"
  },
  "decision_brief": {
    "generated_at": "2026-03-26T00:36:27",
    "review_date": "Thursday, March 26, 2026",
    "lead_mechanism": "Blood-Brain Barrier Dysfunction",
    "stable_rows": 5,
    "provisional_rows": 4,
    "blocked_rows": 2,
    "release_summary": {
      "lead_chapter_candidate": "Blood-Brain Barrier Dysfunction",
      "core_atlas_now": 0,
      "core_atlas_candidates": 0,
      "review_track": 1,
      "hold": 2
    },
    "release_rows": [
      {
        "canonical_mechanism": "blood_brain_barrier_disruption",
        "display_name": "Blood-Brain Barrier Dysfunction",
        "promotion_status": "near_ready",
        "readiness_score": "29",
        "gate_status": "write_with_caution",
        "stable_rows": "2",
        "provisional_rows": "1",
        "blocked_rows": "1",
        "bridge_rows": "1",
        "translational_hook_rows": "0",
        "queue_burden": "6",
        "target_rows": "0",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "review_track",
        "chapter_role": "lead_section",
        "recommended_action": "upgrade_remaining_abstract_support"
      },
      {
        "canonical_mechanism": "neuroinflammation_microglial_activation",
        "display_name": "Neuroinflammation / Microglial Activation",
        "promotion_status": "hold",
        "readiness_score": "4",
        "gate_status": "hold",
        "stable_rows": "2",
        "provisional_rows": "1",
        "blocked_rows": "0",
        "bridge_rows": "1",
        "translational_hook_rows": "3",
        "queue_burden": "17",
        "target_rows": "3",
        "compound_rows": "0",
        "trial_rows": "0",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "none",
        "recommended_next_move": "add_target_and_compound_enrichment",
        "release_bucket": "hold",
        "chapter_role": "hold",
        "recommended_action": "add_target_and_compound_enrichment"
      },
      {
        "canonical_mechanism": "mitochondrial_bioenergetic_dysfunction",
        "display_name": "Mitochondrial Dysfunction",
        "promotion_status": "near_ready",
        "readiness_score": "1",
        "gate_status": "hold",
        "stable_rows": "1",
        "provisional_rows": "2",
        "blocked_rows": "1",
        "bridge_rows": "0",
        "translational_hook_rows": "1",
        "queue_burden": "5",
        "target_rows": "1",
        "compound_rows": "0",
        "trial_rows": "1",
        "preprint_rows": "0",
        "genomics_rows": "0",
        "blocker_summary": "needs source upgrade",
        "recommended_next_move": "upgrade_remaining_abstract_support",
        "release_bucket": "hold",
        "chapter_role": "hold",
        "recommended_action": "upgrade_remaining_abstract_support"
      }
    ],
    "target_priorities": [],
    "human_actions": [
      "Review whether **Blood-Brain Barrier Dysfunction** has enough support to move beyond `review_track`.",
      "Fill the top BBB target rows in the ChEMBL/Open Targets templates.",
      "Decide whether any weekly public-enrichment additions should be accepted, ignored, or manually curated further.",
      "Confirm whether any real 10x exports are ready to import this week."
    ],
    "decisions": [
      {
        "title": "Keep Blood-Brain Barrier Dysfunction as the lead proof-of-concept chapter",
        "recommended_decision": "Yes",
        "why": "Blood-Brain Barrier Dysfunction remains the strongest mechanism in scope, but it is still in `review_track` because some support still needs cleanup.",
        "what_i_need_from_you": "Confirm that we should keep investing the next manual science pass in BBB rather than shifting to a different lead mechanism.",
        "if_yes": "We keep the atlas centered on BBB and use the next human pass to strengthen the evidence needed for promotion."
      },
      {
        "title": "Decide whether there is real 10x data to import this week",
        "recommended_decision": "No unless real exports are available",
        "why": "The 10x lane is valuable, but only when it is backed by real exported analysis results.",
        "what_i_need_from_you": "Tell us whether you have actual 10x outputs ready. If not, we keep moving without blocking the atlas.",
        "if_yes": "We import the 10x results and rerun the atlas enrichment loop."
      }
    ],
    "release_manifest_path": "/home/runner/work/testfile/testfile/reports/atlas_release_manifest/atlas_release_manifest_2026-03-26_001414.json",
    "target_packet_index_path": "",
    "program_status_path": "/home/runner/work/testfile/testfile/reports/program_status/program_status_report_2026-03-26_001414.md"
  }
};

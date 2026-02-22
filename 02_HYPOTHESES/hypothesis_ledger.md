# PROJECT LONGEVITY — Hypothesis Ledger
**Version:** 1.0 | **Last Updated:** 2026-02-21 | **Pipeline Status:** Initializing

---

## Scoring Quick Reference

| Tier | Convergence Score | Requirements |
|------|------------------|-------------|
| Provisional | 0–3 | Single-source claim, awaiting cross-validation |
| Emerging | 4–6 | ≥2 in TWO prongs |
| Evidence-Backed | 7–12 | Strong multi-prong support |
| Cornerstone | 13–15 | Near-consensus, clinical-grade evidence |

**Prong Scoring (0–5 each):**
- Prong 1 (Observational): GEO, GTEx, ENCODE, UK Biobank
- Prong 2 (Perturbation): LINCS L1000, DrugAge, CMap
- Prong 3 (Clinical): ClinicalTrials.gov, CALERIE, TAME, OpenFDA

---

## VALIDATION TRACK

### 1. Epigenetic / Information Aging

#### Evidence-Backed
*(No claims yet — pipeline initializing)*

#### Emerging
- **[HYP-0001]** Epigenetic Clock Reversal
  - Keywords: Horvath clock, OSKM, partial reprogramming, methylation, rejuvenation
  - Domain tags: epigenetic, reprogramming
  - Expected: target=biological age direction=decrease
- **[HYP-0002]** Histone Acetylation Restoration
  - Keywords: H4K16ac, sirtuins, histone acetylation, transcriptional noise
  - Domain tags: epigenetic, genomic_instability
  - Expected: target=transcriptional noise direction=decrease

---

### 2. Cellular Senescence / Inflammaging

#### Evidence-Backed
*(No claims yet)*

#### Emerging
- **[HYP-0003]** Senolytic Clearance
  - Keywords: senolytics, p16INK4a, dasatinib, quercetin, fisetin
  - Domain tags: senescence, inflammaging
  - Expected: target=senescent cell burden direction=decrease
- **[HYP-0004]** SASP Inhibition
  - Keywords: SASP, senomorphics, IL-6, NF-kB, rapamycin
  - Domain tags: senescence, immunosenescence
  - Expected: target=inflammation direction=decrease

---

### 3. Mitochondrial Dysfunction

#### Evidence-Backed
*(No claims yet)*

#### Emerging
- **[HYP-0005]** NAD+ Restoration
  - Keywords: NAD+, NMN, NR, sirtuins, mitochondrial biogenesis
  - Domain tags: mitochondrial, metabolism
  - Expected: target=mitochondrial function direction=increase
- **[HYP-0006]** Mitophagy Induction
  - Keywords: mitophagy, urolithin A, PINK1, Parkin, ROS
  - Domain tags: mitochondrial, autophagy
  - Expected: target=ROS production direction=decrease

---

### 4. Nutrient Sensing / Proteostasis

#### Evidence-Backed
*(No claims yet)*

#### Emerging
- **[HYP-0007]** mTOR Inhibition
  - Keywords: mTOR, rapamycin, autophagy, longevity, caloric restriction
  - Domain tags: nutrient_sensing, autophagy
  - Expected: target=lifespan direction=increase
- **[HYP-0008]** AMPK Activation
  - Keywords: AMPK, metformin, metabolism, insulin sensitivity
  - Domain tags: nutrient_sensing, metabolism
  - Expected: target=insulin sensitivity direction=increase

---

### 5. Stem Cell Exhaustion / ECM Remodeling

#### Evidence-Backed
*(No claims yet)*

#### Emerging
- **[HYP-0009]** Niche Rejuvenation
  - Keywords: stem cell niche, parabiosis, GDF11, regeneration
  - Domain tags: stem_cell_ecm, regeneration
  - Expected: target=regenerative capacity direction=increase
- **[HYP-0010]** ECM Crosslinking
  - Keywords: ECM, stiffness, AGEs, crosslinking, fibrosis
  - Domain tags: stem_cell_ecm, fibrosis
  - Expected: target=arterial stiffness direction=decrease

---

### 6. Comparative Longevity Biology

#### Evidence-Backed
*(No claims yet)*

#### Emerging
- **[HYP-0011]** DNA Repair Efficiency
  - Keywords: DNA repair, DSB, naked mole rat, comparative biology
  - Domain tags: comparative, genomics
  - Expected: target=mutation rate direction=decrease
- **[HYP-0012]** Retrotransposon Silencing
  - Keywords: retrotransposons, LINE-1, SIRT6, sterile inflammation
  - Domain tags: comparative, genomic_instability
  - Expected: target=inflammation direction=decrease

---

## DISCOVERY TRACK

### Active Hypotheses
*(No discoveries yet — requires cross-domain pattern detection)*

### Clinical Trial Candidates
*(None yet)*

---

## Provisional Queue
*(Claims awaiting initial scoring)*

**Template:**
```
- **[CLAIM_ID]** | Status: Provisional | Score: 0/15 | Priority: TBD
  - Claim: "[Exact extracted claim text]"
  - Source: PMID:XXXXXXXX | Domain: [primary] | Cross-domains: [list]
  - Evidence FOR: [list PMIDs]
  - Evidence AGAINST: [list PMIDs]
  - Prong 1 (Obs): 0/5 | Prong 2 (Pert): 0/5 | Prong 3 (Clin): 0/5
  - Last updated: YYYY-MM-DD
  - Needs: [next validation step]
```

---

## Contested Claims
*(Claims with contradictory evidence — flagged by contradiction_scan.py)*

---

## Deprecated Claims
*(Claims removed due to retraction, failed replication, or score collapse)*

---

## Audit Log

| Date | Action | Claim ID | Details |
|------|--------|----------|---------|
| 2026-02-21 | INIT | — | Ledger created. Pipeline initializing. |

---

## Weekly Claim Counts

| Week | New Claims | Promoted | Contested | Deprecated | Discovery Hypotheses |
|------|-----------|----------|-----------|------------|---------------------|
| 2026-W08 | 0 | 0 | 0 | 0 | 0 |

---

*Maintained by the PROJECT LONGEVITY autonomous pipeline.*
*Manual edits by LTC Matthew D. Holtkamp, DO are marked with [MANUAL] tag.*


<!-- HYPOTHESIS_REGISTRY_JSON_START -->
[
  {
    "id": "HYP-0001",
    "hypothesis_id": "HYP-0001",
    "title": "Epigenetic Clock Reversal",
    "description": "Partial reprogramming using OSKM factors restores youthful DNA methylation patterns and reverses biological age without loss of cellular identity.",
    "text": "Partial reprogramming using OSKM factors restores youthful DNA methylation patterns and reverses biological age without loss of cellular identity.",
    "domain": "epigenetic",
    "domain_tags": [
      "epigenetic",
      "reprogramming"
    ],
    "keywords": [
      "Horvath clock",
      "OSKM",
      "partial reprogramming",
      "methylation",
      "rejuvenation"
    ],
    "entities": {
      "interventions": [
        "OSKM",
        "cyclic reprogramming"
      ],
      "targets": [
        "DNA methylation",
        "histone markers"
      ],
      "tissues": [
        "multi-tissue",
        "skin",
        "optic nerve"
      ]
    },
    "expected_effect": [
      {
        "target": "biological age",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0002",
    "hypothesis_id": "HYP-0002",
    "title": "Histone Acetylation Restoration",
    "description": "Loss of H4K16 acetylation drives transcriptional noise and genomic instability during aging; restoring it extends lifespan.",
    "text": "Loss of H4K16 acetylation drives transcriptional noise and genomic instability during aging; restoring it extends lifespan.",
    "domain": "epigenetic",
    "domain_tags": [
      "epigenetic",
      "genomic_instability"
    ],
    "keywords": [
      "H4K16ac",
      "sirtuins",
      "histone acetylation",
      "transcriptional noise"
    ],
    "entities": {
      "interventions": [
        "HDAC inhibitors",
        "sirtuin activators"
      ],
      "targets": [
        "H4K16ac",
        "SIRT1"
      ],
      "tissues": [
        "liver",
        "muscle"
      ]
    },
    "expected_effect": [
      {
        "target": "transcriptional noise",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0003",
    "hypothesis_id": "HYP-0003",
    "title": "Senolytic Clearance",
    "description": "Targeted elimination of p16+ senescent cells ameliorates age-related tissue dysfunction and extends healthspan.",
    "text": "Targeted elimination of p16+ senescent cells ameliorates age-related tissue dysfunction and extends healthspan.",
    "domain": "senescence",
    "domain_tags": [
      "senescence",
      "inflammaging"
    ],
    "keywords": [
      "senolytics",
      "p16INK4a",
      "dasatinib",
      "quercetin",
      "fisetin"
    ],
    "entities": {
      "interventions": [
        "dasatinib",
        "quercetin",
        "fisetin",
        "navitoclax"
      ],
      "targets": [
        "p16",
        "BCL-2"
      ],
      "tissues": [
        "adipose",
        "kidney",
        "lung"
      ]
    },
    "expected_effect": [
      {
        "target": "senescent cell burden",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0004",
    "hypothesis_id": "HYP-0004",
    "title": "SASP Inhibition",
    "description": "Inhibiting the Senescence-Associated Secretory Phenotype (SASP) without killing cells reduces chronic inflammation and improves regeneration.",
    "text": "Inhibiting the Senescence-Associated Secretory Phenotype (SASP) without killing cells reduces chronic inflammation and improves regeneration.",
    "domain": "senescence",
    "domain_tags": [
      "senescence",
      "immunosenescence"
    ],
    "keywords": [
      "SASP",
      "senomorphics",
      "IL-6",
      "NF-kB",
      "rapamycin"
    ],
    "entities": {
      "interventions": [
        "rapamycin",
        "metformin",
        "JAK inhibitors"
      ],
      "targets": [
        "NF-kB",
        "mTOR",
        "IL-6"
      ],
      "tissues": [
        "systemic"
      ]
    },
    "expected_effect": [
      {
        "target": "inflammation",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0005",
    "hypothesis_id": "HYP-0005",
    "title": "NAD+ Restoration",
    "description": "Age-related decline in NAD+ levels compromises mitochondrial function; supplementation with precursors restores energetics and sirtuin activity.",
    "text": "Age-related decline in NAD+ levels compromises mitochondrial function; supplementation with precursors restores energetics and sirtuin activity.",
    "domain": "mitochondrial",
    "domain_tags": [
      "mitochondrial",
      "metabolism"
    ],
    "keywords": [
      "NAD+",
      "NMN",
      "NR",
      "sirtuins",
      "mitochondrial biogenesis"
    ],
    "entities": {
      "interventions": [
        "NMN",
        "Nicotinamide Riboside"
      ],
      "targets": [
        "SIRT1",
        "SIRT3",
        "Complex I"
      ],
      "tissues": [
        "skeletal muscle",
        "brain"
      ]
    },
    "expected_effect": [
      {
        "target": "mitochondrial function",
        "direction": "increase"
      }
    ]
  },
  {
    "id": "HYP-0006",
    "hypothesis_id": "HYP-0006",
    "title": "Mitophagy Induction",
    "description": "Enhancing mitophagy clears damaged mitochondria, preventing ROS accumulation and preserving cellular bioenergetics.",
    "text": "Enhancing mitophagy clears damaged mitochondria, preventing ROS accumulation and preserving cellular bioenergetics.",
    "domain": "mitochondrial",
    "domain_tags": [
      "mitochondrial",
      "autophagy"
    ],
    "keywords": [
      "mitophagy",
      "urolithin A",
      "PINK1",
      "Parkin",
      "ROS"
    ],
    "entities": {
      "interventions": [
        "urolithin A",
        "spermidine"
      ],
      "targets": [
        "PINK1",
        "Parkin"
      ],
      "tissues": [
        "muscle",
        "heart"
      ]
    },
    "expected_effect": [
      {
        "target": "ROS production",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0007",
    "hypothesis_id": "HYP-0007",
    "title": "mTOR Inhibition",
    "description": "Inhibition of mTORC1 signaling mimics caloric restriction, enhances autophagy, and extends lifespan across species.",
    "text": "Inhibition of mTORC1 signaling mimics caloric restriction, enhances autophagy, and extends lifespan across species.",
    "domain": "nutrient_sensing",
    "domain_tags": [
      "nutrient_sensing",
      "autophagy"
    ],
    "keywords": [
      "mTOR",
      "rapamycin",
      "autophagy",
      "longevity",
      "caloric restriction"
    ],
    "entities": {
      "interventions": [
        "rapamycin",
        "everolimus"
      ],
      "targets": [
        "mTORC1",
        "S6K"
      ],
      "tissues": [
        "systemic"
      ]
    },
    "expected_effect": [
      {
        "target": "lifespan",
        "direction": "increase"
      }
    ]
  },
  {
    "id": "HYP-0008",
    "hypothesis_id": "HYP-0008",
    "title": "AMPK Activation",
    "description": "Activation of AMPK improves insulin sensitivity, enhances mitochondrial biogenesis, and promotes healthy aging.",
    "text": "Activation of AMPK improves insulin sensitivity, enhances mitochondrial biogenesis, and promotes healthy aging.",
    "domain": "nutrient_sensing",
    "domain_tags": [
      "nutrient_sensing",
      "metabolism"
    ],
    "keywords": [
      "AMPK",
      "metformin",
      "metabolism",
      "insulin sensitivity"
    ],
    "entities": {
      "interventions": [
        "metformin",
        "berberine"
      ],
      "targets": [
        "AMPK"
      ],
      "tissues": [
        "liver",
        "muscle"
      ]
    },
    "expected_effect": [
      {
        "target": "insulin sensitivity",
        "direction": "increase"
      }
    ]
  },
  {
    "id": "HYP-0009",
    "hypothesis_id": "HYP-0009",
    "title": "Niche Rejuvenation",
    "description": "Rejuvenating the stem cell niche through parabolic factors or ECM remodeling restores regenerative capacity in aged tissues.",
    "text": "Rejuvenating the stem cell niche through parabolic factors or ECM remodeling restores regenerative capacity in aged tissues.",
    "domain": "stem_cell_ecm",
    "domain_tags": [
      "stem_cell_ecm",
      "regeneration"
    ],
    "keywords": [
      "stem cell niche",
      "parabiosis",
      "GDF11",
      "regeneration"
    ],
    "entities": {
      "interventions": [
        "GDF11",
        "young plasma"
      ],
      "targets": [
        "HSCs",
        "satellite cells"
      ],
      "tissues": [
        "blood",
        "muscle"
      ]
    },
    "expected_effect": [
      {
        "target": "regenerative capacity",
        "direction": "increase"
      }
    ]
  },
  {
    "id": "HYP-0010",
    "hypothesis_id": "HYP-0010",
    "title": "ECM Crosslinking",
    "description": "Accumulation of Advanced Glycation End-products (AGEs) causes ECM stiffness and fibrosis; breaking crosslinks restores elasticity.",
    "text": "Accumulation of Advanced Glycation End-products (AGEs) causes ECM stiffness and fibrosis; breaking crosslinks restores elasticity.",
    "domain": "stem_cell_ecm",
    "domain_tags": [
      "stem_cell_ecm",
      "fibrosis"
    ],
    "keywords": [
      "ECM",
      "stiffness",
      "AGEs",
      "crosslinking",
      "fibrosis"
    ],
    "entities": {
      "interventions": [
        "AGE breakers",
        "alt711"
      ],
      "targets": [
        "collagen",
        "elastin"
      ],
      "tissues": [
        "cardiovascular",
        "skin"
      ]
    },
    "expected_effect": [
      {
        "target": "arterial stiffness",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0011",
    "hypothesis_id": "HYP-0011",
    "title": "DNA Repair Efficiency",
    "description": "Long-lived species (e.g., bowhead whale, naked mole rat) possess superior double-strand break repair mechanisms compared to short-lived kin.",
    "text": "Long-lived species (e.g., bowhead whale, naked mole rat) possess superior double-strand break repair mechanisms compared to short-lived kin.",
    "domain": "comparative",
    "domain_tags": [
      "comparative",
      "genomics"
    ],
    "keywords": [
      "DNA repair",
      "DSB",
      "naked mole rat",
      "comparative biology"
    ],
    "entities": {
      "interventions": [
        "SIRT6 overexpression"
      ],
      "targets": [
        "DNA-PKcs",
        "Ku70/80"
      ],
      "tissues": [
        "global"
      ]
    },
    "expected_effect": [
      {
        "target": "mutation rate",
        "direction": "decrease"
      }
    ]
  },
  {
    "id": "HYP-0012",
    "hypothesis_id": "HYP-0012",
    "title": "Retrotransposon Silencing",
    "description": "Efficient silencing of retrotransposons (LINE-1) via SIRT6 contributes to the extreme longevity and cancer resistance of certain species.",
    "text": "Efficient silencing of retrotransposons (LINE-1) via SIRT6 contributes to the extreme longevity and cancer resistance of certain species.",
    "domain": "comparative",
    "domain_tags": [
      "comparative",
      "genomic_instability"
    ],
    "keywords": [
      "retrotransposons",
      "LINE-1",
      "SIRT6",
      "sterile inflammation"
    ],
    "entities": {
      "interventions": [
        "SIRT6 activation",
        "reverse transcriptase inhibitors"
      ],
      "targets": [
        "LINE-1",
        "SIRT6"
      ],
      "tissues": [
        "global"
      ]
    },
    "expected_effect": [
      {
        "target": "inflammation",
        "direction": "decrease"
      }
    ]
  }
]
<!-- HYPOTHESIS_REGISTRY_JSON_END -->

import argparse
import csv
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STARTER_MECHANISMS = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]
DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}
PRIORITY_MODE_ORDERS = {
    'default': STARTER_MECHANISMS,
    'mitochondrial_first': [
        'mitochondrial_bioenergetic_dysfunction',
        'blood_brain_barrier_disruption',
        'neuroinflammation_microglial_activation',
    ],
}
GOOD_BUCKETS = {'high_signal', 'usable'}
EXCLUDED_LANES = {'manual_review'}
TOP_BIOMARKERS_PER_MECHANISM = 3
TOP_ANCHORS_PER_MECHANISM = 3
TOP_EXACT_TARGETS_PER_MECHANISM = 5
CHEMBL_CONTEXT_TERMS = {
    'blood_brain_barrier_disruption': ['blood-brain barrier', 'tight junction', 'barrier permeability', 'microvascular injury'],
    'mitochondrial_bioenergetic_dysfunction': ['mitochondrial dysfunction', 'mitophagy', 'oxidative stress', 'bioenergetic failure', 'calcium overload', 'apoptosis'],
    'neuroinflammation_microglial_activation': ['microglia', 'neuroinflammation', 'inflammasome', 'cytokine signaling'],
}
POLICY_FIELDS = [
    'policy_species_scope',
    'policy_compound_scope',
    'policy_trial_statuses',
    'policy_trial_phases',
    'policy_literature_window_years',
    'policy_preprint_window_days',
    'sanctioned_overrides',
    'policy_summary',
]

TEMPLATE_SCHEMAS = {
    'open_targets': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'target_name',
        'association_score', 'relation', 'status', 'provenance_ref', 'retrieved_at',
        'mechanism_context', 'priority_score', 'priority_reason',
        *POLICY_FIELDS,
    ],
    'chembl': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'compound_name',
        'chembl_id', 'mechanism_of_action', 'bioactivity_summary', 'bioactivity_score',
        'status', 'provenance_ref', 'retrieved_at', 'target_name', 'query_strategy',
        'query_terms', 'assay_keywords', 'mechanism_context', 'priority_score', 'priority_reason',
        *POLICY_FIELDS,
    ],
    'clinicaltrials_gov': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'nct_id', 'trial_title',
        'phase', 'status', 'intervention_name', 'provenance_ref', 'retrieved_at',
        'query_terms', 'mechanism_context', 'priority_score', 'priority_reason',
        *POLICY_FIELDS,
    ],
    'biorxiv_medrxiv': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'doi', 'preprint_title',
        'server', 'posted_date', 'status', 'provenance_ref', 'retrieved_at',
        'priority_score', 'priority_reason',
        *POLICY_FIELDS,
    ],
    'tenx_genomics': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'analysis_id', 'project_name',
        'entity_type', 'entity_id', 'entity_label', 'relation', 'value', 'score', 'status',
        'provenance_ref', 'retrieved_at', 'priority_score', 'priority_reason',
        *POLICY_FIELDS,
    ],
}


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def latest_optional_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def unique_preserve_order(items):
    seen = set()
    ordered = []
    for item in items:
        normalized = normalize_spaces(item)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def normalize_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


def split_multi(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def slugify(value):
    return normalize_spaces(value).lower().replace(' ', '_').replace('/', '_')


def normalize_text(value):
    value = normalize_spaces(value).lower()
    value = value.replace('-', ' ')
    return ' '.join(value.split())


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def load_alias_map(path):
    payload = load_yaml(path)
    starter = payload.get('starter_mechanism_aliases', {})
    alias_map = {}
    for mechanism, targets in starter.items():
        alias_map[mechanism] = {}
        for symbol, aliases in (targets or {}).items():
            normalized_aliases = {normalize_text(symbol)}
            normalized_aliases.update(normalize_text(alias) for alias in (aliases or []))
            alias_map[mechanism][symbol] = normalized_aliases
    return alias_map


def mechanism_priority_rank(mechanism, priority_mode):
    order = PRIORITY_MODE_ORDERS.get(priority_mode, PRIORITY_MODE_ORDERS['mitochondrial_first'])
    return order.index(mechanism) if mechanism in order else 99


def build_priority_score(mechanism, connector, anchor_priority, exact_target=False, match_count=0):
    score = 0
    if mechanism == 'mitochondrial_bioenergetic_dysfunction':
        score += 20
    elif mechanism == 'blood_brain_barrier_disruption':
        score += 8
    if anchor_priority == 'primary':
        score += 6
    if connector == 'chembl':
        score += 12
    elif connector == 'clinicaltrials_gov':
        score += 10
    elif connector == 'open_targets':
        score += 8
    if exact_target:
        score += 30
    score += match_count * 4
    return score


def build_priority_reason(mechanism, connector, exact_target=False, match_count=0):
    parts = []
    if mechanism == 'mitochondrial_bioenergetic_dysfunction':
        parts.append('mitochondrial-first enrichment focus')
    if exact_target:
        parts.append('exact target symbol seed')
    if match_count:
        parts.append(f'{match_count} claim match(es)')
    parts.append(f'{connector} follow-on')
    return '; '.join(parts)


def build_query_terms(mechanism, query_seed, connector, aliases=None):
    mechanism_label = DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' '))
    terms = [query_seed]
    terms.extend(aliases or [])
    if connector in {'chembl', 'clinicaltrials_gov'}:
        terms.append(f'{query_seed} AND traumatic brain injury')
        if mechanism == 'mitochondrial_bioenergetic_dysfunction':
            terms.extend([
                f'{query_seed} AND mitochondrial dysfunction',
                f'{query_seed} AND oxidative stress',
                f'{query_seed} AND mitophagy',
            ])
        else:
            terms.append(f'{query_seed} AND {mechanism_label.lower()}')
    elif connector == 'biorxiv_medrxiv':
        terms.append(f'traumatic brain injury AND {mechanism_label.lower()}')
    return '; '.join(unique_preserve_order(terms))


def build_assay_keywords(mechanism, aliases=None):
    return '; '.join(unique_preserve_order((aliases or []) + CHEMBL_CONTEXT_TERMS.get(mechanism, [])))


def unique_join(items):
    return '; '.join(unique_preserve_order(items))


def listify(value):
    if isinstance(value, list):
        return [normalize_spaces(item) for item in value if normalize_spaces(item)]
    if isinstance(value, str):
        return split_multi(value)
    return []


def connector_policy(config, preset_name, connector):
    config = config or {}
    defaults = config.get('defaults', {}) or {}
    connector_defaults = (config.get('connectors', {}) or {}).get(connector, {}) or {}
    preset_defaults = (config.get('presets', {}) or {}).get(preset_name, {}) or {}
    policy = {
        'policy_species_scope': normalize_spaces(
            preset_defaults.get('species_scope')
            or connector_defaults.get('species_scope')
            or defaults.get('species_scope')
        ),
        'policy_compound_scope': normalize_spaces(
            preset_defaults.get('compound_scope')
            or connector_defaults.get('compound_scope')
            or defaults.get('compound_scope')
        ),
        'policy_trial_statuses': unique_join(
            listify(preset_defaults.get('trial_statuses'))
            or listify(connector_defaults.get('trial_statuses'))
            or listify(defaults.get('trial_statuses'))
        ),
        'policy_trial_phases': unique_join(
            listify(preset_defaults.get('trial_phases'))
            or listify(connector_defaults.get('trial_phases'))
            or listify(defaults.get('trial_phases'))
        ),
        'policy_literature_window_years': str(
            preset_defaults.get('literature_window_years')
            or connector_defaults.get('literature_window_years')
            or defaults.get('literature_window_years')
            or ''
        ),
        'policy_preprint_window_days': str(
            preset_defaults.get('preprint_window_days')
            or connector_defaults.get('preprint_window_days')
            or defaults.get('preprint_window_days')
            or ''
        ),
        'sanctioned_overrides': unique_join(
            listify(preset_defaults.get('sanctioned_overrides'))
            or listify(connector_defaults.get('sanctioned_overrides'))
            or listify(defaults.get('sanctioned_overrides'))
        ),
    }
    summary_parts = []
    if policy['policy_compound_scope']:
        summary_parts.append(f"compound={policy['policy_compound_scope']}")
    if policy['policy_trial_statuses']:
        summary_parts.append(f"trial_status={policy['policy_trial_statuses']}")
    if policy['policy_trial_phases']:
        summary_parts.append(f"trial_phase={policy['policy_trial_phases']}")
    if policy['policy_species_scope']:
        summary_parts.append(f"species={policy['policy_species_scope']}")
    if policy['policy_preprint_window_days']:
        summary_parts.append(f"preprint_window={policy['policy_preprint_window_days']}d")
    if policy['policy_literature_window_years']:
        summary_parts.append(f"literature_window={policy['policy_literature_window_years']}y")
    if policy['sanctioned_overrides']:
        summary_parts.append(f"overrides={policy['sanctioned_overrides']}")
    policy['policy_summary'] = ' | '.join(summary_parts)
    return policy


def build_manifest_row(
    mechanism,
    connector,
    preset_name,
    query_seed,
    evidence_tier_target,
    anchor_priority,
    pmid,
    title,
    source_quality_tier,
    quality_bucket,
    atlas_layer,
    biomarker_families,
    top_claim_example,
    provenance_source,
    notes,
    exact_target=False,
    match_count=0,
    aliases=None,
    policy_config=None,
):
    priority_score = build_priority_score(mechanism, connector, anchor_priority, exact_target=exact_target, match_count=match_count)
    priority_reason = build_priority_reason(mechanism, connector, exact_target=exact_target, match_count=match_count)
    mechanism_context = f"{DISPLAY_NAMES.get(mechanism, mechanism)} | {normalize_spaces(atlas_layer) or 'mechanism'} | {normalize_spaces(top_claim_example)}"
    row = {
        'canonical_mechanism': mechanism,
        'pmid': pmid,
        'title': title,
        'source_quality_tier': source_quality_tier,
        'quality_bucket': quality_bucket,
        'atlas_layer': atlas_layer,
        'anchor_priority': anchor_priority,
        'biomarker_families': biomarker_families,
        'top_claim_example': top_claim_example,
        'requested_connector': connector,
        'preset_name': preset_name,
        'query_seed': query_seed,
        'evidence_tier_target': evidence_tier_target,
        'provenance_source': provenance_source,
        'notes': notes,
        'priority_score': priority_score,
        'priority_reason': priority_reason,
        'focus_track': 'mitochondrial_focus' if mechanism == 'mitochondrial_bioenergetic_dysfunction' else 'supporting_mechanism',
        'query_terms': build_query_terms(mechanism, query_seed, connector, aliases=aliases),
        'assay_keywords': build_assay_keywords(mechanism, aliases=aliases) if connector == 'chembl' else '',
        'mechanism_context': mechanism_context,
        'query_strategy': 'target_symbol_exact_then_alias_then_mechanism' if connector == 'chembl' and exact_target else '',
    }
    row.update(connector_policy(policy_config, preset_name, connector))
    return row


def rank_anchor_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            row.get('source_quality_tier') != 'full_text_like',
            row.get('quality_bucket') != 'high_signal',
            -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('avg_confidence_score')) or 0.0),
            row.get('pmid', ''),
        ),
    )


def top_biomarker_rows(claim_rows, limit):
    counter = Counter()
    seed_map = defaultdict(list)
    for row in claim_rows:
        for biomarker in split_multi(row.get('biomarker_families') or row.get('biomarkers')):
            counter[biomarker] += 1
            seed_map[biomarker].append(row)
    items = []
    for biomarker, count in counter.most_common(limit):
        seed_rows = sorted(
            seed_map[biomarker],
            key=lambda row: (
                row.get('source_quality_tier') != 'full_text_like',
                -(normalize_float(row.get('mechanistic_depth_score')) or 0.0),
                -(normalize_float(row.get('confidence_score')) or 0.0),
                row.get('pmid', ''),
            ),
        )
        top_row = seed_rows[0]
        items.append({
            'biomarker_family': biomarker,
            'count': count,
            'pmid': top_row.get('pmid', ''),
            'title': top_row.get('title', ''),
            'atlas_layer': top_row.get('atlas_layer', ''),
            'top_claim_example': top_row.get('normalized_claim') or top_row.get('claim_text', ''),
        })
    return items


def exact_target_seed_rows(mechanism, claim_rows, alias_map, paper_lookup, limit):
    mechanism_aliases = alias_map.get(mechanism, {})
    if not mechanism_aliases:
        return []

    candidates = []
    for symbol, aliases in mechanism_aliases.items():
        matched_rows = []
        for row in claim_rows:
            haystack = normalize_text(' '.join([
                row.get('normalized_claim', ''),
                row.get('claim_text', ''),
                row.get('biomarker_families', ''),
                row.get('biomarkers', ''),
                row.get('anatomy_context', ''),
            ]))
            if not haystack:
                continue
            if any(alias and alias in haystack for alias in aliases):
                matched_rows.append(row)
        if not matched_rows:
            continue
        matched_rows.sort(
            key=lambda row: (
                paper_lookup.get(normalize_spaces(row.get('pmid', '')), {}).get('source_quality_tier') != 'full_text_like',
                paper_lookup.get(normalize_spaces(row.get('pmid', '')), {}).get('quality_bucket') != 'high_signal',
                -(normalize_float(row.get('mechanistic_depth_score')) or 0.0),
                -(normalize_float(row.get('confidence_score')) or 0.0),
                row.get('pmid', ''),
            )
        )
        top_row = matched_rows[0]
        candidates.append({
            'symbol': symbol,
            'aliases': sorted(alias for alias in aliases if alias != normalize_text(symbol)),
            'match_count': len(matched_rows),
            'pmid': normalize_spaces(top_row.get('pmid', '')),
            'title': top_row.get('title', ''),
            'atlas_layer': top_row.get('atlas_layer', ''),
            'top_claim_example': top_row.get('normalized_claim') or top_row.get('claim_text', ''),
        })

    candidates.sort(key=lambda item: (-item['match_count'], item['symbol']))
    return candidates[:limit]


def build_rows(claim_rows, paper_rows, action_rows, backbone_rows, anchor_rows, alias_map, priority_mode, policy_config):
    paper_lookup = {normalize_spaces(row.get('pmid', '')): row for row in paper_rows if normalize_spaces(row.get('pmid', ''))}
    action_lookup = {normalize_spaces(row.get('pmid', '')): row for row in action_rows if normalize_spaces(row.get('pmid', ''))}
    anchors_by_mechanism = defaultdict(list)
    for row in anchor_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            anchors_by_mechanism[mechanism].append(row)
    for mechanism in anchors_by_mechanism:
        anchors_by_mechanism[mechanism] = rank_anchor_rows(anchors_by_mechanism[mechanism])

    backbone_by_mechanism = defaultdict(list)
    for row in backbone_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            backbone_by_mechanism[mechanism].append(row)
    for mechanism in backbone_by_mechanism:
        backbone_by_mechanism[mechanism].sort(
            key=lambda row: (
                -int(row.get('full_text_like_papers', 0) or 0),
                -int(row.get('paper_count', 0) or 0),
                -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
                row.get('atlas_layer', ''),
            )
        )

    claims_by_mechanism = defaultdict(list)
    for row in claim_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        pmid = normalize_spaces(row.get('pmid', ''))
        if mechanism in STARTER_MECHANISMS and pmid:
            paper = paper_lookup.get(pmid, {})
            action = action_lookup.get(pmid, {})
            if paper.get('topic_bucket', 'tbi_anchor') != 'tbi_anchor':
                continue
            if paper.get('quality_bucket', '') not in GOOD_BUCKETS:
                continue
            if parse_bool(paper.get('whether_needs_manual_review')):
                continue
            if action.get('action_lane', '') in EXCLUDED_LANES:
                continue
            claims_by_mechanism[mechanism].append(row)

    rows = []
    for mechanism in STARTER_MECHANISMS:
        mechanism_claims = claims_by_mechanism.get(mechanism, [])
        if not mechanism_claims:
            continue
        display_name = DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' ').title())
        top_anchors = anchors_by_mechanism.get(mechanism, [])[:TOP_ANCHORS_PER_MECHANISM]
        top_backbone = backbone_by_mechanism.get(mechanism, [])
        strongest_layer = top_backbone[0].get('atlas_layer', '') if top_backbone else ''
        top_anchor = top_anchors[0] if top_anchors else {}
        top_anchor_pmid = normalize_spaces(top_anchor.get('pmid', ''))
        top_anchor_title = top_anchor.get('title', '')
        top_anchor_quality = top_anchor.get('quality_bucket', '')
        top_claim_example = top_anchor.get('example_claim', '')
        top_biomarkers = top_biomarker_rows(mechanism_claims, TOP_BIOMARKERS_PER_MECHANISM)
        exact_targets = exact_target_seed_rows(mechanism, mechanism_claims, alias_map, paper_lookup, TOP_EXACT_TARGETS_PER_MECHANISM)
        biomarker_summary = '; '.join(item['biomarker_family'] for item in top_biomarkers)

        rows.extend([
            build_manifest_row(
                mechanism=mechanism,
                connector='open_targets',
                preset_name='mechanism_to_therapeutic',
                query_seed=display_name,
                evidence_tier_target='target_association',
                anchor_priority='primary',
                pmid=top_anchor_pmid,
                title=top_anchor_title,
                source_quality_tier=top_anchor.get('source_quality_tier', ''),
                quality_bucket=top_anchor_quality,
                atlas_layer=strongest_layer,
                biomarker_families=biomarker_summary,
                top_claim_example=top_claim_example,
                provenance_source='investigation_claims+atlas_backbone+atlas_anchors',
                notes=f'Use {display_name} as the mechanism-level target seeding concept.',
                policy_config=policy_config,
            ),
            build_manifest_row(
                mechanism=mechanism,
                connector='chembl',
                preset_name='mechanism_to_therapeutic',
                query_seed=display_name,
                evidence_tier_target='compound_mechanism',
                anchor_priority='primary',
                pmid=top_anchor_pmid,
                title=top_anchor_title,
                source_quality_tier=top_anchor.get('source_quality_tier', ''),
                quality_bucket=top_anchor_quality,
                atlas_layer=strongest_layer,
                biomarker_families=biomarker_summary,
                top_claim_example=top_claim_example,
                provenance_source='investigation_claims+atlas_backbone+atlas_anchors',
                notes=f'Use {display_name} to seed translational mechanism and compound review.',
                policy_config=policy_config,
            ),
            build_manifest_row(
                mechanism=mechanism,
                connector='clinicaltrials_gov',
                preset_name='mechanism_to_therapeutic',
                query_seed=display_name,
                evidence_tier_target='trial_landscape',
                anchor_priority='primary',
                pmid=top_anchor_pmid,
                title=top_anchor_title,
                source_quality_tier=top_anchor.get('source_quality_tier', ''),
                quality_bucket=top_anchor_quality,
                atlas_layer=strongest_layer,
                biomarker_families=biomarker_summary,
                top_claim_example=top_claim_example,
                provenance_source='investigation_claims+atlas_backbone+atlas_anchors',
                notes=f'Check intervention and target-aligned trials for {display_name}.',
                policy_config=policy_config,
            ),
            build_manifest_row(
                mechanism=mechanism,
                connector='biorxiv_medrxiv',
                preset_name='preprint_surveillance',
                query_seed=f'traumatic brain injury AND {display_name.lower()}',
                evidence_tier_target='preprint_only',
                anchor_priority='primary',
                pmid=top_anchor_pmid,
                title=top_anchor_title,
                source_quality_tier=top_anchor.get('source_quality_tier', ''),
                quality_bucket=top_anchor_quality,
                atlas_layer=strongest_layer,
                biomarker_families=biomarker_summary,
                top_claim_example=top_claim_example,
                provenance_source='investigation_claims+atlas_backbone+atlas_anchors',
                notes=f'Frontier scan for {display_name} in TBI-focused preprints.',
                policy_config=policy_config,
            ),
            build_manifest_row(
                mechanism=mechanism,
                connector='tenx_genomics',
                preset_name='single_cell_mechanism_deep_dive',
                query_seed=display_name,
                evidence_tier_target='genomics_expression',
                anchor_priority='primary',
                pmid=top_anchor_pmid,
                title=top_anchor_title,
                source_quality_tier=top_anchor.get('source_quality_tier', ''),
                quality_bucket=top_anchor_quality,
                atlas_layer=strongest_layer,
                biomarker_families=biomarker_summary,
                top_claim_example=top_claim_example,
                provenance_source='investigation_claims+atlas_backbone+atlas_anchors',
                notes='Optional local import lane for 10x outputs linked to this canonical mechanism.',
                policy_config=policy_config,
            ),
        ])

        for idx, biomarker_row in enumerate(top_biomarkers, start=1):
            rows.append(build_manifest_row(
                mechanism=mechanism,
                connector='open_targets',
                preset_name='biomarker_to_target',
                query_seed=biomarker_row['biomarker_family'],
                evidence_tier_target='target_association',
                anchor_priority='primary' if idx == 1 else 'secondary',
                pmid=biomarker_row['pmid'],
                title=biomarker_row['title'],
                source_quality_tier=paper_lookup.get(biomarker_row['pmid'], {}).get('source_quality_tier', ''),
                quality_bucket=paper_lookup.get(biomarker_row['pmid'], {}).get('quality_bucket', ''),
                atlas_layer=biomarker_row['atlas_layer'],
                biomarker_families=biomarker_row['biomarker_family'],
                top_claim_example=biomarker_row['top_claim_example'],
                provenance_source='investigation_claims',
                notes=f"Top biomarker family for {display_name}; seed target lookup from biomarker context.",
                policy_config=policy_config,
            ))

        for idx, target_row in enumerate(exact_targets, start=1):
            anchor_priority = 'primary' if idx == 1 else 'secondary'
            common_kwargs = {
                'mechanism': mechanism,
                'anchor_priority': anchor_priority,
                'pmid': target_row['pmid'],
                'title': target_row['title'],
                'source_quality_tier': paper_lookup.get(target_row['pmid'], {}).get('source_quality_tier', ''),
                'quality_bucket': paper_lookup.get(target_row['pmid'], {}).get('quality_bucket', ''),
                'atlas_layer': target_row['atlas_layer'],
                'biomarker_families': target_row['symbol'],
                'top_claim_example': target_row['top_claim_example'],
                'provenance_source': 'investigation_claims+manual_target_aliases',
                'exact_target': True,
                'match_count': target_row['match_count'],
                'aliases': target_row.get('aliases', []),
            }
            rows.append(build_manifest_row(
                connector='open_targets',
                preset_name='biomarker_to_target',
                query_seed=target_row['symbol'],
                evidence_tier_target='target_association',
                notes=f"Exact target symbol matched in starter-mechanism claims for {display_name}; prioritize precise target lookup for {target_row['symbol']}.",
                policy_config=policy_config,
                **common_kwargs,
            ))
            rows.append(build_manifest_row(
                connector='chembl',
                preset_name='biomarker_to_target',
                query_seed=target_row['symbol'],
                evidence_tier_target='compound_mechanism',
                notes=f"Exact target symbol matched in starter-mechanism claims for {display_name}; use target-first ChEMBL search for {target_row['symbol']} before broader mechanism terms.",
                policy_config=policy_config,
                **common_kwargs,
            ))
            rows.append(build_manifest_row(
                connector='clinicaltrials_gov',
                preset_name='biomarker_to_target',
                query_seed=target_row['symbol'],
                evidence_tier_target='trial_landscape',
                notes=f"Prioritize target-linked trial searching for {target_row['symbol']} in the {display_name} lane.",
                policy_config=policy_config,
                **common_kwargs,
            ))

    deduped = {}
    for row in rows:
        key = (
            row['canonical_mechanism'],
            row['requested_connector'],
            normalize_spaces(row['query_seed']).lower(),
            normalize_spaces(row['pmid']),
        )
        deduped.setdefault(key, row)

    rows = list(deduped.values())
    rows.sort(key=lambda row: (
        mechanism_priority_rank(row['canonical_mechanism'], priority_mode),
        -int(row.get('priority_score') or 0),
        row['requested_connector'],
        row['anchor_priority'],
        row['query_seed'],
    ))
    return rows


def render_markdown(rows):
    connector_counts = Counter(row['requested_connector'] for row in rows)
    mechanism_counts = Counter(row['canonical_mechanism'] for row in rows)
    lines = [
        '# Connector Candidate Manifest',
        '',
        f'- Candidate rows: `{len(rows)}`',
        '',
        '## Connectors Requested',
        '',
    ]
    for connector, count in sorted(connector_counts.items()):
        lines.append(f'- {connector}: `{count}`')
    lines.extend(['', '## Mechanisms Covered', ''])
    for mechanism, count in sorted(mechanism_counts.items()):
        lines.append(f'- {mechanism}: `{count}`')
    lines.extend([
        '',
        '## Preview',
        '',
        '| Mechanism | Connector | Score | Preset | PMID | Atlas Layer | Query Seed | Evidence Tier |',
        '| --- | --- | ---: | --- | --- | --- | --- | --- |',
    ])
    for row in rows[:40]:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['requested_connector']} | {row['priority_score']} | {row['preset_name']} | {row['pmid']} | "
            f"{row['atlas_layer']} | {row['query_seed']} | {row['evidence_tier_target']} |"
        )
    return '\n'.join(lines) + '\n'


def template_row_from_manifest(connector, row):
    base = {field: '' for field in TEMPLATE_SCHEMAS[connector]}
    for key, value in {
        'canonical_mechanism': row['canonical_mechanism'],
        'pmid': row['pmid'],
        'title': row['title'],
        'query_seed': row['query_seed'],
        'status': 'seed_from_manifest',
        'provenance_ref': f"manifest_seed | {row['provenance_source']}",
        'retrieved_at': '',
        'mechanism_context': row.get('mechanism_context', ''),
        'priority_score': row.get('priority_score', ''),
        'priority_reason': row.get('priority_reason', ''),
        'policy_species_scope': row.get('policy_species_scope', ''),
        'policy_compound_scope': row.get('policy_compound_scope', ''),
        'policy_trial_statuses': row.get('policy_trial_statuses', ''),
        'policy_trial_phases': row.get('policy_trial_phases', ''),
        'policy_literature_window_years': row.get('policy_literature_window_years', ''),
        'policy_preprint_window_days': row.get('policy_preprint_window_days', ''),
        'sanctioned_overrides': row.get('sanctioned_overrides', ''),
        'policy_summary': row.get('policy_summary', ''),
    }.items():
        if key in base:
            base[key] = value
    if connector == 'open_targets':
        base.update({
            'target_name': row['query_seed'],
            'relation': 'associated_target',
        })
    elif connector == 'chembl':
        base.update({
            'target_id': row['query_seed'] if row.get('query_strategy') else '',
            'target_name': row['query_seed'] if row.get('query_strategy') else '',
            'query_strategy': row.get('query_strategy', ''),
            'query_terms': row.get('query_terms', ''),
            'assay_keywords': row.get('assay_keywords', ''),
        })
    elif connector == 'clinicaltrials_gov':
        base['query_terms'] = row.get('query_terms', '')
    return base


def write_templates(output_dir, ts, manifest_rows):
    template_dir = os.path.join(output_dir, 'templates')
    os.makedirs(template_dir, exist_ok=True)
    for connector, fieldnames in TEMPLATE_SCHEMAS.items():
        path = os.path.join(template_dir, f'{connector}_import_template_{ts}.csv')
        connector_rows = [template_row_from_manifest(connector, row) for row in manifest_rows if row['requested_connector'] == connector]
        write_csv(path, connector_rows, fieldnames)


def main():
    parser = argparse.ArgumentParser(description='Build a connector candidate manifest from investigation artifacts.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--action-queue-csv', default='', help='Path to investigation_action_queue CSV. Defaults to latest report.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix CSV. Defaults to latest report if available.')
    parser.add_argument('--anchors-csv', default='', help='Path to atlas_backbone_anchors CSV. Defaults to latest report if available.')
    parser.add_argument('--alias-yaml', default='config/manual_target_aliases.yaml', help='Path to manual target alias YAML.')
    parser.add_argument('--query-policy-yaml', default='config/query_policy_defaults.yaml', help='Path to connector query-policy defaults YAML.')
    parser.add_argument('--priority-mode', choices=sorted(PRIORITY_MODE_ORDERS), default='mitochondrial_first', help='Manifest ranking mode.')
    parser.add_argument('--output-dir', default='reports/connector_candidate_manifest', help='Directory for output artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')
    action_queue_csv = args.action_queue_csv or latest_report_path('investigation_action_queue_*.csv')
    backbone_csv = args.backbone_csv or latest_optional_report_path('atlas_backbone_matrix_*.csv')
    anchors_csv = args.anchors_csv or latest_optional_report_path('atlas_backbone_anchors_*.csv')

    registry = load_yaml(os.path.join(REPO_ROOT, 'config', 'connector_registry.yaml'))
    presets = load_yaml(os.path.join(REPO_ROOT, 'config', 'enrichment_presets.yaml'))
    alias_map = load_alias_map(os.path.join(REPO_ROOT, args.alias_yaml))
    policy_config = load_yaml(os.path.join(REPO_ROOT, args.query_policy_yaml))
    _ = registry, presets

    rows = build_rows(
        read_csv(claims_csv),
        read_csv(paper_qa_csv),
        read_csv(action_queue_csv),
        read_csv(backbone_csv) if backbone_csv else [],
        read_csv(anchors_csv) if anchors_csv else [],
        alias_map,
        args.priority_mode,
        policy_config,
    )

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f'connector_candidate_manifest_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'connector_candidate_manifest_{ts}.md')
    fieldnames = [
        'canonical_mechanism', 'pmid', 'title', 'source_quality_tier', 'quality_bucket',
        'atlas_layer', 'anchor_priority', 'biomarker_families', 'top_claim_example',
        'requested_connector', 'preset_name', 'query_seed', 'evidence_tier_target',
        'provenance_source', 'notes', 'priority_score', 'priority_reason', 'focus_track',
        'query_terms', 'assay_keywords', 'mechanism_context', 'query_strategy',
        *POLICY_FIELDS,
    ]
    write_csv(csv_path, rows, fieldnames)
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(rows))
    write_templates(args.output_dir, ts, rows)

    print(f'Connector candidate manifest written: {csv_path}')
    print(f'Connector candidate summary written: {md_path}')
    print(f'Candidate rows: {len(rows)}')


if __name__ == '__main__':
    main()

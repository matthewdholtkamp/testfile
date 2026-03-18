import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.run_pipeline as rp
from scripts.mechanism_normalization import normalize_mechanism


EXTRACTION_COLLECTIONS = {
    'paper_summaries': 'paper_summary',
    'claims': 'claims',
    'decisions': 'decision',
    'graph_edges': 'edges',
}
INVENTORY_REQUIRED_COLUMNS = {'pmid', 'full_path', 'topic_bucket', 'modified_time'}
LOW_SCORE_THRESHOLD = 2.5
HIGH_SIGNAL_DEPTH_THRESHOLD = 3.5
NA_LABELS = {'', 'n/a', 'na', 'none', 'unknown', 'unspecified', 'not specified'}
BIOMARKER_CANONICAL_RULES = [
    (re.compile(r'^(?:fractional anisotropy(?: \(fa\))?|fa)$', re.IGNORECASE), 'Fractional anisotropy (FA)'),
    (re.compile(r'^(?:mean diffusivity(?: \(md\))?|md)$', re.IGNORECASE), 'Mean diffusivity (MD)'),
    (re.compile(r'^(?:radial diffusivity(?: \(rd\))?|rd)$', re.IGNORECASE), 'Radial diffusivity (RD)'),
    (re.compile(r'^(?:axial diffusivity(?: \(ad\))?|ad)$', re.IGNORECASE), 'Axial diffusivity (AD)'),
    (re.compile(r'^gfap$', re.IGNORECASE), 'GFAP'),
    (re.compile(r'^(?:uch-l1|uchl1)$', re.IGNORECASE), 'UCH-L1'),
    (re.compile(r'^(?:il[\s-]?6)$', re.IGNORECASE), 'IL-6'),
    (re.compile(r'^(?:il[\s-]?1(?:β|b))$', re.IGNORECASE), 'IL-1β'),
    (re.compile(r'^crp$', re.IGNORECASE), 'CRP'),
    (re.compile(r'^bdnf$', re.IGNORECASE), 'BDNF'),
    (re.compile(r'^s100b$', re.IGNORECASE), 'S100B'),
]


def latest_inventory_path():
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', 'drive_inventory_*.csv'), recursive=True))
    if not candidates:
        raise FileNotFoundError('No drive_inventory CSV found under reports/.')
    valid_candidates = [path for path in candidates if inventory_has_required_columns(path)]
    if not valid_candidates:
        raise FileNotFoundError(
            f'No drive_inventory CSV with required columns {sorted(INVENTORY_REQUIRED_COLUMNS)} found under reports/.'
        )
    return valid_candidates[-1]


def inventory_has_required_columns(path):
    try:
        with open(path, newline='', encoding='utf-8') as handle:
            reader = csv.reader(handle)
            header = next(reader)
    except (FileNotFoundError, StopIteration):
        return False
    return INVENTORY_REQUIRED_COLUMNS.issubset(set(header))


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        if not INVENTORY_REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f'Inventory CSV {path} is missing required columns {sorted(INVENTORY_REQUIRED_COLUMNS)}. '
                f'Found columns: {reader.fieldnames or []}'
            )
        return list(reader)


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def normalize_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def average(values):
    usable = [value for value in values if value is not None]
    if not usable:
        return ''
    return round(sum(usable) / len(usable), 3)


def join_sorted(values):
    clean = sorted({value for value in values if value})
    return '; '.join(clean)


def numeric_or_default(value, default=0.0):
    parsed = normalize_float(value)
    return parsed if parsed is not None else default


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


def normalize_spaces(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def normalize_label(value):
    cleaned = normalize_spaces(value)
    if cleaned.casefold() in NA_LABELS:
        return ''
    return cleaned


def canonicalize_by_rules(value, rules):
    cleaned = normalize_label(value)
    if not cleaned:
        return ''
    for pattern, label in rules:
        if pattern.search(cleaned):
            return label
    return cleaned


def canonicalize_biomarker(value):
    return canonicalize_by_rules(value, BIOMARKER_CANONICAL_RULES)


def normalize_node_key(value):
    cleaned = normalize_label(value).casefold()
    cleaned = re.sub(r'\bmtbi\b', 'mild traumatic brain injury', cleaned)
    cleaned = re.sub(r'\btbi\b', 'traumatic brain injury', cleaned)
    return re.sub(r'[^a-z0-9]+', ' ', cleaned).strip()


def top_counter_items(counter, limit=10):
    return '; '.join(label for label, _ in counter.most_common(limit))


def representative_label(values):
    counter = Counter(normalize_label(value) for value in values if normalize_label(value))
    if not counter:
        return ''
    return sorted(counter.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))[0][0]


def extract_collection(full_path):
    match = re.match(r'^extraction_outputs/([^/]+)/', full_path or '')
    if not match:
        return ''
    return match.group(1)


def choose_latest(rows):
    return max(rows, key=lambda row: row.get('modified_time', '') or '')


def build_source_map(rows):
    source_rows = [
        row for row in rows
        if row.get('pmid') and not (row.get('full_path') or '').startswith('extraction_outputs/')
    ]
    source_map = {}
    for row in source_rows:
        pmid = row['pmid']
        current = source_map.get(pmid)
        if current is None or (row.get('modified_time', '') or '') > (current.get('modified_time', '') or ''):
            source_map[pmid] = row
    return source_map


def build_output_index(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        full_path = row.get('full_path') or ''
        if not full_path.startswith('extraction_outputs/'):
            continue
        pmid = row.get('pmid') or ''
        if not pmid:
            continue
        collection = extract_collection(full_path)
        kind = EXTRACTION_COLLECTIONS.get(collection)
        if not kind:
            continue
        grouped[pmid][kind].append(row)

    output_index = {}
    for pmid, kinds in grouped.items():
        output_index[pmid] = {
            kind: choose_latest(kind_rows)
            for kind, kind_rows in kinds.items()
        }
    return output_index


def load_json_artifact(service, row, expected_type, artifact_name):
    if not row:
        return None, f'missing_{artifact_name}_artifact'
    try:
        content = rp.download_file_content(service, row['file_id'])
    except Exception:
        return None, f'{artifact_name}_download_error'
    if not content:
        return None, f'{artifact_name}_empty_content'
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None, f'{artifact_name}_json_decode_error'
    if not isinstance(payload, expected_type):
        return None, f'{artifact_name}_wrong_type'
    return payload, ''


def source_quality_tier(source_row):
    rank = str(source_row.get('extraction_rank', '') or '')
    if rank == '1':
        return 'abstract_only'
    if rank in {'2', '3', '4', '5'}:
        return 'full_text_like'
    return 'unknown'


def quality_bucket(source_tier, claim_count, edge_count, avg_depth, needs_review, artifact_error_count):
    if artifact_error_count:
        return 'artifact_error'
    if needs_review:
        return 'review_needed'
    if claim_count == 0 and edge_count == 0:
        return 'empty'
    if source_tier == 'abstract_only' and claim_count <= 2 and edge_count == 0:
        return 'sparse_abstract'
    if avg_depth != '' and avg_depth >= HIGH_SIGNAL_DEPTH_THRESHOLD and (claim_count >= 3 or edge_count >= 2):
        return 'high_signal'
    if claim_count >= 5 or edge_count >= 4:
        return 'high_signal'
    if claim_count >= 2 or edge_count >= 1:
        return 'usable'
    return 'sparse'


def investigation_priority(source_tier, claim_count, edge_count, needs_review, artifact_error_count):
    if needs_review or artifact_error_count:
        return 'manual_review'
    if source_tier == 'full_text_like' and (claim_count >= 4 or edge_count >= 2):
        return 'high'
    if claim_count >= 2 or edge_count >= 1:
        return 'medium'
    return 'low'


def build_paper_rows(service, source_map, output_index, on_topic_only):
    pmids = sorted(output_index)
    paper_rows = []
    claim_export_rows = []
    edge_export_rows = []
    mechanism_accumulator = defaultdict(list)
    atlas_accumulator = defaultdict(list)
    biomarker_accumulator = defaultdict(list)
    biomarker_raw_labels = defaultdict(Counter)

    for pmid in pmids:
        source_row = source_map.get(pmid, {})
        if on_topic_only and source_row.get('topic_bucket') != 'tbi_anchor':
            continue

        output_rows = output_index.get(pmid, {})
        summary_json, summary_error = load_json_artifact(service, output_rows.get('paper_summary'), dict, 'summary')
        claims_json, claims_error = load_json_artifact(service, output_rows.get('claims'), list, 'claims')
        decision_json, decision_error = load_json_artifact(service, output_rows.get('decision'), dict, 'decision')
        edges_json, edges_error = load_json_artifact(service, output_rows.get('edges'), list, 'edges')

        artifact_errors = [error for error in [summary_error, claims_error, decision_error, edges_error] if error]
        claims_json = claims_json or []
        edges_json = edges_json or []
        summary_json = summary_json or {}
        decision_json = decision_json or {}

        claim_count = len(claims_json)
        edge_count = len(edges_json)
        avg_confidence = average([normalize_float(claim.get('confidence_score')) for claim in claims_json if isinstance(claim, dict)])
        avg_depth = average([normalize_float(claim.get('mechanistic_depth_score')) for claim in claims_json if isinstance(claim, dict)])
        avg_translational = average([normalize_float(claim.get('translational_relevance_score')) for claim in claims_json if isinstance(claim, dict)])

        claim_mechanisms = [claim.get('mechanism', '') for claim in claims_json if isinstance(claim, dict)]
        summary_mechanisms = summary_json.get('major_mechanisms', []) or []
        raw_mechanisms = list(claim_mechanisms) + list(summary_mechanisms)
        atlas_layers = [claim.get('atlas_layer', '') for claim in claims_json if isinstance(claim, dict)]
        atlas_layers.extend(summary_json.get('dominant_atlas_layers', []) or [])
        raw_biomarkers = []
        interventions = []
        outcomes = []
        contradiction_edge_count = 0
        for claim in claims_json:
            if not isinstance(claim, dict):
                continue
            raw_biomarkers.extend(claim.get('biomarkers', []) or [])
            interventions.extend(claim.get('interventions', []) or [])
            outcomes.extend(claim.get('outcome_measures', []) or [])
        for edge in edges_json:
            if isinstance(edge, dict) and parse_bool(edge.get('contradiction_flag')):
                contradiction_edge_count += 1

        normalized_claim_mechanisms = [normalize_label(value) for value in claim_mechanisms if normalize_label(value)]
        normalized_raw_mechanisms = [normalize_label(value) for value in raw_mechanisms if normalize_label(value)]
        biomarker_families = [canonicalize_biomarker(value) for value in raw_biomarkers]

        source_tier = source_quality_tier(source_row)
        needs_review = parse_bool(decision_json.get('whether_needs_manual_review'))
        artifact_read_error_count = sum(1 for error in artifact_errors if error.endswith('_download_error') or error.endswith('_empty_content'))
        artifact_parse_error_count = sum(1 for error in artifact_errors if error.endswith('_json_decode_error') or error.endswith('_wrong_type'))
        artifact_missing_count = sum(1 for error in artifact_errors if error.startswith('missing_'))
        science_quality_bucket = quality_bucket(source_tier, claim_count, edge_count, avg_depth, needs_review, 0)

        paper_row = {
            'pmid': pmid,
            'paper_id': summary_json.get('paper_id', f'PMID{pmid}'),
            'title': summary_json.get('title', '') or source_row.get('title_excerpt', ''),
            'topic_bucket': source_row.get('topic_bucket', ''),
            'topic_anchor': source_row.get('topic_anchor', ''),
            'source_rank': source_row.get('extraction_rank', ''),
            'source_type': source_row.get('extraction_source', ''),
            'source_quality_tier': source_tier,
            'claim_count': claim_count,
            'edge_count': edge_count,
            'contradiction_edge_count': contradiction_edge_count,
            'avg_confidence_score': avg_confidence,
            'avg_mechanistic_depth_score': avg_depth,
            'avg_translational_relevance_score': avg_translational,
            'dominant_atlas_layers': join_sorted(atlas_layers),
            'major_mechanisms': join_sorted(normalized_raw_mechanisms),
            'claim_mechanisms': join_sorted(normalized_claim_mechanisms),
            'summary_major_mechanisms': join_sorted(summary_mechanisms),
            'biomarker_count': len({value for value in raw_biomarkers if normalize_label(value)}),
            'biomarker_families': join_sorted(biomarker_families),
            'intervention_count': len({value for value in interventions if normalize_label(value)}),
            'outcome_measure_count': len({value for value in outcomes if normalize_label(value)}),
            'include_in_core_atlas': decision_json.get('include_in_core_atlas', ''),
            'whether_human_relevant': decision_json.get('whether_human_relevant', ''),
            'whether_mechanistically_informative': decision_json.get('whether_mechanistically_informative', ''),
            'whether_needs_manual_review': needs_review,
            'novelty_estimate': decision_json.get('novelty_estimate', ''),
            'primary_domain': decision_json.get('primary_domain', ''),
            'artifact_error_count': len(artifact_errors),
            'artifact_error_labels': '; '.join(artifact_errors),
            'artifact_read_error_count': artifact_read_error_count,
            'artifact_parse_error_count': artifact_parse_error_count,
            'artifact_missing_count': artifact_missing_count,
            'science_quality_bucket': science_quality_bucket,
            'quality_bucket': quality_bucket(source_tier, claim_count, edge_count, avg_depth, needs_review, len(artifact_errors)),
            'investigation_priority': investigation_priority(source_tier, claim_count, edge_count, needs_review, len(artifact_errors)),
        }
        paper_rows.append(paper_row)

        for claim in claims_json:
            if not isinstance(claim, dict):
                continue
            claim_mechanism = normalize_label(claim.get('mechanism', ''))
            claim_mechanism_normalization = normalize_mechanism(
                claim_mechanism,
                normalized_claim=claim.get('normalized_claim', ''),
                atlas_layer=claim.get('atlas_layer', ''),
                confidence_score=claim.get('confidence_score'),
                mechanistic_depth_score=claim.get('mechanistic_depth_score'),
            )
            claim_biomarkers = [normalize_label(value) for value in (claim.get('biomarkers', []) or [])]
            claim_biomarker_families = [canonicalize_biomarker(value) for value in claim_biomarkers]
            claim_export_rows.append({
                'pmid': pmid,
                'paper_id': paper_row['paper_id'],
                'title': paper_row['title'],
                'source_quality_tier': source_tier,
                'topic_anchor': paper_row['topic_anchor'],
                'claim_id': claim.get('claim_id', ''),
                'claim_text': claim.get('claim_text', ''),
                'normalized_claim': claim.get('normalized_claim', ''),
                'atlas_layer': claim.get('atlas_layer', ''),
                'mechanism': claim_mechanism,
                'canonical_mechanism': claim_mechanism_normalization['canonical_mechanism'],
                'canonical_mechanism_status': claim_mechanism_normalization['canonical_mechanism_status'],
                'canonical_mechanism_basis': claim_mechanism_normalization['canonical_mechanism_basis'],
                'direction_of_effect': claim.get('direction_of_effect', ''),
                'causal_status': claim.get('causal_status', ''),
                'evidence_type': claim.get('evidence_type', ''),
                'species': claim.get('species', ''),
                'model': claim.get('model', ''),
                'anatomy': claim.get('anatomy', ''),
                'cell_type': claim.get('cell_type', ''),
                'timing_bin': claim.get('timing_bin', ''),
                'biomarkers': join_sorted(claim_biomarkers),
                'biomarker_families': join_sorted(claim_biomarker_families),
                'interventions': join_sorted(claim.get('interventions', []) or []),
                'outcome_measures': join_sorted(claim.get('outcome_measures', []) or []),
                'confidence_score': claim.get('confidence_score', ''),
                'mechanistic_depth_score': claim.get('mechanistic_depth_score', ''),
                'translational_relevance_score': claim.get('translational_relevance_score', ''),
                'include_in_core_atlas': decision_json.get('include_in_core_atlas', ''),
                'whether_human_relevant': decision_json.get('whether_human_relevant', ''),
                'whether_mechanistically_informative': decision_json.get('whether_mechanistically_informative', ''),
                'whether_needs_manual_review': needs_review,
                'artifact_error_count': len(artifact_errors),
                'artifact_error_labels': '; '.join(artifact_errors),
                'artifact_read_error_count': artifact_read_error_count,
                'artifact_parse_error_count': artifact_parse_error_count,
                'artifact_missing_count': artifact_missing_count,
                'primary_domain': decision_json.get('primary_domain', ''),
                'novelty_estimate': decision_json.get('novelty_estimate', ''),
            })

        for edge in edges_json:
            if not isinstance(edge, dict):
                continue
            source_node = normalize_label(edge.get('source_node', ''))
            target_node = normalize_label(edge.get('target_node', ''))
            relation = normalize_label(edge.get('relation', ''))
            source_node_key = normalize_node_key(source_node)
            target_node_key = normalize_node_key(target_node)
            edge_key = '|'.join([source_node_key, relation.casefold(), target_node_key]).strip('|')
            edge_export_rows.append({
                'pmid': pmid,
                'paper_id': paper_row['paper_id'],
                'title': paper_row['title'],
                'source_quality_tier': source_tier,
                'topic_anchor': paper_row['topic_anchor'],
                'edge_id': edge.get('edge_id', ''),
                'source_node': source_node,
                'source_node_key': source_node_key,
                'relation': relation,
                'target_node': target_node,
                'target_node_key': target_node_key,
                'edge_key': edge_key,
                'atlas_layer': edge.get('atlas_layer', ''),
                'anatomy': edge.get('anatomy', ''),
                'cell_type': edge.get('cell_type', ''),
                'timing_bin': edge.get('timing_bin', ''),
                'species': edge.get('species', ''),
                'evidence_strength': edge.get('evidence_strength', ''),
                'contradiction_flag': parse_bool(edge.get('contradiction_flag')),
                'notes': edge.get('notes', ''),
                'include_in_core_atlas': decision_json.get('include_in_core_atlas', ''),
                'whether_human_relevant': decision_json.get('whether_human_relevant', ''),
                'whether_mechanistically_informative': decision_json.get('whether_mechanistically_informative', ''),
                'whether_needs_manual_review': needs_review,
                'artifact_error_count': len(artifact_errors),
                'artifact_error_labels': '; '.join(artifact_errors),
                'artifact_read_error_count': artifact_read_error_count,
                'artifact_parse_error_count': artifact_parse_error_count,
                'artifact_missing_count': artifact_missing_count,
                'primary_domain': decision_json.get('primary_domain', ''),
                'novelty_estimate': decision_json.get('novelty_estimate', ''),
            })

        for mechanism in set(normalized_raw_mechanisms):
            mechanism_accumulator[mechanism].append(paper_row)
        for atlas_layer in {normalize_label(value) for value in atlas_layers if normalize_label(value)}:
            atlas_accumulator[atlas_layer].append(paper_row)
        for biomarker in {value for value in biomarker_families if value}:
            biomarker_accumulator[biomarker].append(paper_row)
        for biomarker in [normalize_label(value) for value in raw_biomarkers]:
            family = canonicalize_biomarker(biomarker)
            if family and biomarker:
                biomarker_raw_labels[family][biomarker] += 1

    return (
        paper_rows,
        claim_export_rows,
        edge_export_rows,
        mechanism_accumulator,
        atlas_accumulator,
        biomarker_accumulator,
        biomarker_raw_labels,
    )


def aggregate_group(grouped_rows, label_name, raw_label_counters=None):
    aggregated_rows = []
    for label, rows in sorted(grouped_rows.items(), key=lambda item: (-len(item[1]), item[0])):
        aggregated = {
            label_name: label,
            'paper_count': len({row['pmid'] for row in rows}),
            'claim_total': sum(int(row['claim_count']) for row in rows),
            'edge_total': sum(int(row['edge_count']) for row in rows),
            'full_text_like_papers': sum(1 for row in rows if row['source_quality_tier'] == 'full_text_like'),
            'abstract_only_papers': sum(1 for row in rows if row['source_quality_tier'] == 'abstract_only'),
            'review_needed_papers': sum(1 for row in rows if row['whether_needs_manual_review'] is True),
            'avg_confidence_score': average([normalize_float(row['avg_confidence_score']) for row in rows]),
            'avg_mechanistic_depth_score': average([normalize_float(row['avg_mechanistic_depth_score']) for row in rows]),
            'top_pmids': '; '.join(sorted({row['pmid'] for row in rows})[:10]),
        }
        if raw_label_counters is not None:
            counter = raw_label_counters.get(label, Counter())
            aggregated['raw_label_count'] = len(counter)
            aggregated['raw_label_examples'] = top_counter_items(counter)
        aggregated_rows.append(aggregated)
    return aggregated_rows


def build_contradiction_rows(edge_export_rows):
    grouped = defaultdict(list)
    for row in edge_export_rows:
        key = row.get('edge_key', '')
        if not key:
            continue
        grouped[key].append(row)

    contradiction_rows = []
    for key, rows in grouped.items():
        contradiction_rows_for_key = [row for row in rows if parse_bool(row.get('contradiction_flag'))]
        support_rows_for_key = [row for row in rows if not parse_bool(row.get('contradiction_flag'))]
        pmids = sorted({row['pmid'] for row in rows})
        if not contradiction_rows_for_key and len(pmids) < 2:
            continue

        contradiction_rows.append({
            'edge_key': key,
            'source_node': representative_label(row.get('source_node', '') for row in rows),
            'relation': representative_label(row.get('relation', '') for row in rows),
            'target_node': representative_label(row.get('target_node', '') for row in rows),
            'paper_count': len(pmids),
            'edge_mentions': len(rows),
            'supporting_edge_mentions': len(support_rows_for_key),
            'contradicting_edge_mentions': len(contradiction_rows_for_key),
            'supporting_papers': len({row['pmid'] for row in support_rows_for_key}),
            'contradicting_papers': len({row['pmid'] for row in contradiction_rows_for_key}),
            'full_text_like_papers': len({row['pmid'] for row in rows if row['source_quality_tier'] == 'full_text_like'}),
            'abstract_only_papers': len({row['pmid'] for row in rows if row['source_quality_tier'] == 'abstract_only'}),
            'signal_profile': (
                'mixed_signal' if contradiction_rows_for_key and support_rows_for_key
                else 'contradiction_only' if contradiction_rows_for_key
                else 'support_only'
            ),
            'support_example_notes': next((normalize_spaces(row.get('notes', '')) for row in support_rows_for_key if normalize_spaces(row.get('notes', ''))), ''),
            'contradiction_example_notes': next((normalize_spaces(row.get('notes', '')) for row in contradiction_rows_for_key if normalize_spaces(row.get('notes', ''))), ''),
            'top_pmids': '; '.join(pmids[:10]),
        })

    contradiction_rows.sort(
        key=lambda row: (
            row['signal_profile'] != 'mixed_signal',
            -int(row['contradicting_edge_mentions']),
            -int(row['paper_count']),
            row['edge_key'],
        )
    )
    return contradiction_rows


def build_canonical_mechanism_rows(claim_export_rows):
    grouped = defaultdict(list)
    raw_label_counters = defaultdict(Counter)

    for row in claim_export_rows:
        canonical = normalize_label(row.get('canonical_mechanism', ''))
        if not canonical:
            continue
        grouped[canonical].append(row)
        raw_label = normalize_label(row.get('mechanism', '')) or normalize_label(row.get('normalized_claim', ''))
        if raw_label:
            raw_label_counters[canonical][raw_label] += 1

    canonical_rows = []
    for canonical, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        canonical_rows.append({
            'canonical_mechanism': canonical,
            'paper_count': len({row['pmid'] for row in rows}),
            'claim_total': len(rows),
            'full_text_like_papers': len({row['pmid'] for row in rows if row['source_quality_tier'] == 'full_text_like'}),
            'abstract_only_papers': len({row['pmid'] for row in rows if row['source_quality_tier'] == 'abstract_only'}),
            'review_needed_papers': len({row['pmid'] for row in rows if parse_bool(row.get('whether_needs_manual_review'))}),
            'avg_confidence_score': average([normalize_float(row.get('confidence_score')) for row in rows]),
            'avg_mechanistic_depth_score': average([normalize_float(row.get('mechanistic_depth_score')) for row in rows]),
            'raw_label_examples': top_counter_items(raw_label_counters[canonical]),
            'top_pmids': '; '.join(sorted({row['pmid'] for row in rows})[:10]),
        })

    return rank_aggregates(canonical_rows)


def rank_aggregates(rows):
    return sorted(
        rows,
        key=lambda row: (
            -int(row.get('full_text_like_papers', 0) or 0),
            -int(row.get('paper_count', 0) or 0),
            -numeric_or_default(row.get('avg_mechanistic_depth_score')),
            -numeric_or_default(row.get('avg_confidence_score')),
            row.get('top_pmids', ''),
        ),
    )


def build_caution_rows(paper_rows, limit=15):
    caution_rows = [
        row for row in paper_rows
        if row['quality_bucket'] in {'artifact_error', 'review_needed', 'sparse_abstract', 'empty', 'sparse'}
        or numeric_or_default(row['avg_confidence_score'], 5.0) < LOW_SCORE_THRESHOLD
    ]
    caution_rows.sort(
        key=lambda row: (
            row['quality_bucket'] not in {'artifact_error', 'review_needed'},
            row['source_quality_tier'] != 'abstract_only',
            numeric_or_default(row['avg_confidence_score'], 5.0),
            numeric_or_default(row['avg_mechanistic_depth_score'], 5.0),
            row['pmid'],
        )
    )
    return caution_rows[:limit]


def build_core_atlas_candidates(paper_rows, limit=15):
    candidates = [
        row for row in paper_rows
        if row['include_in_core_atlas'] is True
        and row['whether_mechanistically_informative'] is True
        and row['whether_needs_manual_review'] is not True
        and int(row.get('artifact_error_count', 0) or 0) == 0
    ]
    candidates.sort(
        key=lambda row: (
            row['source_quality_tier'] != 'full_text_like',
            row['quality_bucket'] != 'high_signal',
            -numeric_or_default(row['avg_mechanistic_depth_score']),
            -numeric_or_default(row['avg_confidence_score']),
            -int(row['claim_count']),
            row['pmid'],
        )
    )
    return candidates[:limit]


def build_summary_payload(
    paper_rows,
    claim_export_rows,
    edge_export_rows,
    mechanism_rows,
    canonical_mechanism_rows,
    atlas_rows,
    biomarker_rows,
    contradiction_rows,
    inventory_path,
):
    quality_counts = Counter(row['quality_bucket'] for row in paper_rows)
    science_quality_counts = Counter(row['science_quality_bucket'] for row in paper_rows)
    tier_counts = Counter(row['source_quality_tier'] for row in paper_rows)
    priority_counts = Counter(row['investigation_priority'] for row in paper_rows)
    strongest_mechanisms = rank_aggregates(mechanism_rows)[:15]
    strongest_canonical_mechanisms = canonical_mechanism_rows[:15]
    strongest_atlas_layers = rank_aggregates(atlas_rows)[:15]
    biomarker_hotspots = rank_aggregates(biomarker_rows)[:15]
    contradiction_hotspots = contradiction_rows[:15]
    caution_rows = build_caution_rows(paper_rows)
    core_atlas_candidates = build_core_atlas_candidates(paper_rows)
    artifact_issue_counts = Counter()
    for row in paper_rows:
        for label in [value for value in (row.get('artifact_error_labels') or '').split('; ') if value]:
            artifact_issue_counts[label] += 1

    summary = {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'inventory_path': inventory_path,
        'paper_count': len(paper_rows),
        'claim_export_count': len(claim_export_rows),
        'edge_export_count': len(edge_export_rows),
        'canonical_mechanism_count': len(canonical_mechanism_rows),
        'contradiction_row_count': len(contradiction_rows),
        'source_quality_tier_counts': dict(tier_counts),
        'quality_bucket_counts': dict(quality_counts),
        'science_quality_bucket_counts': dict(science_quality_counts),
        'investigation_priority_counts': dict(priority_counts),
        'high_signal_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'high_signal'),
        'review_needed_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'review_needed'),
        'sparse_abstract_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'sparse_abstract'),
        'artifact_error_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'artifact_error'),
        'papers_with_any_artifact_issue_count': sum(1 for row in paper_rows if int(row.get('artifact_error_count', 0) or 0) > 0),
        'core_atlas_candidate_count': len(core_atlas_candidates),
        'caution_paper_count': len(caution_rows),
        'top_mechanisms': strongest_mechanisms,
        'top_canonical_mechanisms': strongest_canonical_mechanisms,
        'top_atlas_layers': strongest_atlas_layers,
        'top_biomarkers': biomarker_hotspots,
        'top_contradictions': contradiction_hotspots,
        'strongest_mechanisms': strongest_mechanisms,
        'strongest_canonical_mechanisms': strongest_canonical_mechanisms,
        'strongest_atlas_layers': strongest_atlas_layers,
        'biomarker_hotspots': biomarker_hotspots,
        'contradiction_hotspots': contradiction_hotspots,
        'papers_needing_caution': caution_rows,
        'core_atlas_candidates': core_atlas_candidates,
        'artifact_issue_counts': dict(artifact_issue_counts),
    }
    return summary


def render_markdown(summary):
    lines = [
        '# Post-Extraction Analysis Summary',
        '',
        f"- Generated at: `{summary['generated_at']}`",
        f"- Inventory path: `{summary['inventory_path']}`",
        f"- On-topic papers analyzed: `{summary['paper_count']}`",
        f"- Claim rows exported: `{summary['claim_export_count']}`",
        f"- Edge rows exported: `{summary['edge_export_count']}`",
        f"- Canonical mechanism families: `{summary['canonical_mechanism_count']}`",
        f"- Contradiction clusters: `{summary['contradiction_row_count']}`",
        f"- Core atlas candidates: `{summary['core_atlas_candidate_count']}`",
        f"- Caution papers: `{summary['caution_paper_count']}`",
        '',
        '## Source Quality Tiers',
        '',
    ]

    for label, count in sorted(summary['source_quality_tier_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend(['', '## Quality Buckets', ''])
    for label, count in sorted(summary['quality_bucket_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend(['', '## Science Signal Buckets', ''])
    for label, count in sorted(summary['science_quality_bucket_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    if summary.get('artifact_issue_counts'):
        lines.extend(['', '## Artifact Issues', ''])
        for label, count in sorted(summary['artifact_issue_counts'].items(), key=lambda item: (-item[1], item[0]))[:10]:
            lines.append(f"- {label}: `{count}`")

    lines.extend([
        '',
        '## Investigation Priority',
        '',
    ])
    for label, count in sorted(summary['investigation_priority_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend([
        '',
        '## Top Mechanisms',
        '',
        '| Mechanism | Papers | Full-text-like | Abstract-only | Avg Depth | Avg Confidence |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['top_mechanisms']:
        lines.append(
            f"| {row['mechanism']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_mechanistic_depth_score']} | {row['avg_confidence_score']} |"
        )

    lines.extend([
        '',
        '## Top Canonical Mechanisms',
        '',
        '| Canonical Mechanism | Papers | Full-text-like | Abstract-only | Avg Depth | Raw Labels |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['top_canonical_mechanisms']:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_mechanistic_depth_score']} | {row['raw_label_examples']} |"
        )

    lines.extend([
        '',
        '## Cross-Paper Tension Signals',
        '',
        '| Source | Relation | Target | Signal | Papers | Supporting | Contradicting |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['top_contradictions']:
        lines.append(
            f"| {row['source_node']} | {row['relation']} | {row['target_node']} | {row['signal_profile']} | "
            f"{row['paper_count']} | {row['supporting_edge_mentions']} | {row['contradicting_edge_mentions']} |"
        )

    lines.extend([
        '',
        '## Top Atlas Layers',
        '',
        '| Atlas Layer | Papers | Claims | Edges | Avg Depth |',
        '| --- | --- | --- | --- | --- |',
    ])
    for row in summary['top_atlas_layers']:
        lines.append(
            f"| {row['atlas_layer']} | {row['paper_count']} | {row['claim_total']} | {row['edge_total']} | {row['avg_mechanistic_depth_score']} |"
        )

    lines.extend([
        '',
        '## Top Biomarkers',
        '',
        '| Biomarker | Papers | Full-text-like | Abstract-only |',
        '| --- | --- | --- | --- |',
    ])
    for row in summary['top_biomarkers']:
        lines.append(
            f"| {row['biomarker']} | {row['paper_count']} | {row['full_text_like_papers']} | {row['abstract_only_papers']} |"
        )

    return '\n'.join(lines) + '\n'


def render_investigation_brief(summary):
    def caution_reason(row):
        reasons = []
        if int(row.get('artifact_error_count', 0) or 0) > 0:
            reasons.append(f"artifact issues: {row.get('artifact_error_labels', '')}")
        if row['whether_needs_manual_review']:
            reasons.append('manual review')
        if row['source_quality_tier'] == 'abstract_only':
            reasons.append('abstract-only')
        if row['quality_bucket'] in {'sparse_abstract', 'empty', 'sparse', 'artifact_error'}:
            reasons.append(row['quality_bucket'].replace('_', ' '))
        if numeric_or_default(row['avg_confidence_score'], 5.0) < LOW_SCORE_THRESHOLD:
            reasons.append('low confidence')
        if numeric_or_default(row['avg_mechanistic_depth_score'], 5.0) < LOW_SCORE_THRESHOLD:
            reasons.append('low depth')
        return ', '.join(dict.fromkeys(reasons)) or row['quality_bucket']

    lines = [
        '# TBI Investigation Brief',
        '',
        'This brief is the post-extraction synthesis layer for the current on-topic corpus. It is designed to help decide what mechanisms, atlas layers, and biomarkers deserve attention next, while keeping source-quality caveats visible.',
        '',
        f"- Generated at: `{summary['generated_at']}`",
        f"- On-topic papers analyzed: `{summary['paper_count']}`",
        f"- Full-text-like papers: `{summary['source_quality_tier_counts'].get('full_text_like', 0)}`",
        f"- Abstract-only papers: `{summary['source_quality_tier_counts'].get('abstract_only', 0)}`",
        f"- High-signal papers: `{summary['high_signal_paper_count']}`",
        f"- Review-needed papers: `{summary['review_needed_paper_count']}`",
        f"- Sparse abstract papers: `{summary['sparse_abstract_paper_count']}`",
        f"- Artifact-error papers: `{summary['artifact_error_paper_count']}`",
        "- Rankings favor recurrence across papers first, then full-text support, mechanistic depth, and confidence.",
        '',
        '## Strongest Mechanism Signals',
        '',
        '| Raw Mechanism Label | Papers | Full-text-like | Abstract-only | Avg Depth | Avg Confidence | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in summary['strongest_mechanisms'][:10]:
        lines.append(
            f"| {row['mechanism']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_mechanistic_depth_score']} | {row['avg_confidence_score']} | "
            f"{row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Cross-Paper Tension Signals',
        '',
        '| Source | Relation | Target | Signal | Papers | Supporting | Contradicting | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['contradiction_hotspots'][:10]:
        lines.append(
            f"| {row['source_node']} | {row['relation']} | {row['target_node']} | {row['signal_profile']} | "
            f"{row['paper_count']} | {row['supporting_edge_mentions']} | {row['contradicting_edge_mentions']} | "
            f"{row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Canonical Mechanism Backbone',
        '',
        '| Canonical Mechanism | Papers | Full-text-like | Avg Depth | Raw label examples |',
        '| --- | --- | --- | --- | --- |',
    ])
    for row in summary['strongest_canonical_mechanisms'][:10]:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['avg_mechanistic_depth_score']} | {row['raw_label_examples']} |"
        )

    lines.extend([
        '',
        '## Strongest Atlas Layers',
        '',
        '| Atlas Layer | Papers | Claims | Edges | Full-text-like | Avg Depth | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['strongest_atlas_layers'][:10]:
        lines.append(
            f"| {row['atlas_layer']} | {row['paper_count']} | {row['claim_total']} | {row['edge_total']} | "
            f"{row['full_text_like_papers']} | {row['avg_mechanistic_depth_score']} | {row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Biomarker Hotspots',
        '',
        '| Biomarker Family | Papers | Full-text-like | Abstract-only | Avg Confidence | Raw label examples | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['biomarker_hotspots'][:10]:
        lines.append(
            f"| {row['biomarker']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_confidence_score']} | {row.get('raw_label_examples', '')} | {row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Core Atlas Candidates',
        '',
        '| PMID | Title | Tier | Claims | Edges | Avg Depth | Avg Confidence | Mechanisms |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['core_atlas_candidates'][:10]:
        lines.append(
            f"| {row['pmid']} | {row['title']} | {row['source_quality_tier']} | {row['claim_count']} | "
            f"{row['edge_count']} | {row['avg_mechanistic_depth_score']} | {row['avg_confidence_score']} | "
            f"{row['major_mechanisms']} |"
        )

    lines.extend([
        '',
        '## Papers Needing Caution',
        '',
        '| PMID | Title | Tier | Bucket | Avg Confidence | Avg Depth | Why be careful |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['papers_needing_caution'][:10]:
        lines.append(
            f"| {row['pmid']} | {row['title']} | {row['source_quality_tier']} | {row['quality_bucket']} | "
            f"{row['avg_confidence_score']} | {row['avg_mechanistic_depth_score']} | "
            f"{caution_reason(row)} |"
        )

    lines.extend([
        '',
        '## How To Use This Brief',
        '',
        '- Treat the strongest mechanism and atlas-layer tables as the best starting point for the first mechanistic atlas slices.',
        '- Treat the cross-paper tension table as the shortlist for contradiction review, boundary conditions, and hypothesis refinement.',
        '- Treat the core atlas candidates as the safest papers to promote into deeper synthesis and contradiction review.',
        '- Treat the caution table as a do-not-overinterpret list until those papers get a deeper pass, better full text, or artifact repair.',
        '',
    ])

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build post-extraction QA and mechanism aggregation artifacts from Drive outputs.')
    parser.add_argument('--inventory', default='', help='Path to drive_inventory CSV. Defaults to latest reports/drive_inventory_*.csv')
    parser.add_argument('--output-dir', default='reports', help='Directory for output artifacts.')
    parser.add_argument('--folder-id', default=os.environ.get('DRIVE_FOLDER_ID', ''), help='Google Drive folder ID (optional if env var is set).')
    parser.add_argument('--include-off-topic', action='store_true', help='Include off-topic papers in the per-paper QA table.')
    args = parser.parse_args()

    inventory_path = args.inventory or latest_inventory_path()
    rows = read_csv(inventory_path)
    source_map = build_source_map(rows)
    output_index = build_output_index(rows)

    if not args.folder_id and not os.environ.get('DRIVE_FOLDER_ID'):
        raise SystemExit('Missing DRIVE_FOLDER_ID. Provide --folder-id or set DRIVE_FOLDER_ID env var.')

    if args.folder_id:
        os.environ['DRIVE_FOLDER_ID'] = args.folder_id

    service = rp.get_google_drive_service()

    (
        paper_rows,
        claim_export_rows,
        edge_export_rows,
        mechanism_accumulator,
        atlas_accumulator,
        biomarker_accumulator,
        biomarker_raw_labels,
    ) = build_paper_rows(
        service,
        source_map,
        output_index,
        on_topic_only=not args.include_off_topic,
    )

    mechanism_rows = aggregate_group(mechanism_accumulator, 'mechanism')
    canonical_mechanism_rows = build_canonical_mechanism_rows(claim_export_rows)
    atlas_rows = aggregate_group(atlas_accumulator, 'atlas_layer')
    biomarker_rows = aggregate_group(biomarker_accumulator, 'biomarker', raw_label_counters=biomarker_raw_labels)
    contradiction_rows = build_contradiction_rows(edge_export_rows)
    summary = build_summary_payload(
        paper_rows,
        claim_export_rows,
        edge_export_rows,
        mechanism_rows,
        canonical_mechanism_rows,
        atlas_rows,
        biomarker_rows,
        contradiction_rows,
        inventory_path,
    )

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)

    paper_qa_path = os.path.join(args.output_dir, f'post_extraction_paper_qa_{ts}.csv')
    mechanism_path = os.path.join(args.output_dir, f'mechanism_aggregation_{ts}.csv')
    canonical_mechanism_path = os.path.join(args.output_dir, f'canonical_mechanism_aggregation_{ts}.csv')
    atlas_path = os.path.join(args.output_dir, f'atlas_layer_aggregation_{ts}.csv')
    biomarker_path = os.path.join(args.output_dir, f'biomarker_aggregation_{ts}.csv')
    contradiction_path = os.path.join(args.output_dir, f'contradiction_aggregation_{ts}.csv')
    claim_export_path = os.path.join(args.output_dir, f'investigation_claims_{ts}.csv')
    edge_export_path = os.path.join(args.output_dir, f'investigation_edges_{ts}.csv')
    summary_json_path = os.path.join(args.output_dir, f'post_extraction_summary_{ts}.json')
    summary_md_path = os.path.join(args.output_dir, f'post_extraction_summary_{ts}.md')
    investigation_brief_path = os.path.join(args.output_dir, f'tbi_investigation_brief_{ts}.md')

    if paper_rows:
        write_csv(paper_qa_path, paper_rows, list(paper_rows[0].keys()))
    else:
        write_csv(paper_qa_path, [], [
            'pmid', 'paper_id', 'title', 'topic_bucket', 'topic_anchor', 'source_rank', 'source_type',
            'source_quality_tier', 'claim_count', 'edge_count', 'contradiction_edge_count', 'avg_confidence_score',
            'avg_mechanistic_depth_score', 'avg_translational_relevance_score', 'dominant_atlas_layers',
            'major_mechanisms', 'claim_mechanisms', 'summary_major_mechanisms',
            'biomarker_count', 'biomarker_families',
            'intervention_count', 'outcome_measure_count',
            'include_in_core_atlas', 'whether_human_relevant', 'whether_mechanistically_informative',
            'whether_needs_manual_review', 'novelty_estimate', 'primary_domain', 'artifact_error_count',
            'artifact_error_labels', 'artifact_read_error_count', 'artifact_parse_error_count',
            'artifact_missing_count', 'science_quality_bucket', 'quality_bucket', 'investigation_priority',
        ])

    write_csv(mechanism_path, mechanism_rows, list(mechanism_rows[0].keys()) if mechanism_rows else [
        'mechanism', 'paper_count', 'claim_total', 'edge_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'top_pmids',
    ])
    write_csv(canonical_mechanism_path, canonical_mechanism_rows, list(canonical_mechanism_rows[0].keys()) if canonical_mechanism_rows else [
        'canonical_mechanism', 'paper_count', 'claim_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'raw_label_examples', 'top_pmids',
    ])
    write_csv(atlas_path, atlas_rows, list(atlas_rows[0].keys()) if atlas_rows else [
        'atlas_layer', 'paper_count', 'claim_total', 'edge_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'top_pmids',
    ])
    write_csv(biomarker_path, biomarker_rows, list(biomarker_rows[0].keys()) if biomarker_rows else [
        'biomarker', 'paper_count', 'claim_total', 'edge_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'top_pmids', 'raw_label_count', 'raw_label_examples',
    ])
    write_csv(contradiction_path, contradiction_rows, list(contradiction_rows[0].keys()) if contradiction_rows else [
        'edge_key', 'source_node', 'relation', 'target_node', 'paper_count', 'edge_mentions',
        'supporting_edge_mentions', 'contradicting_edge_mentions', 'supporting_papers',
        'contradicting_papers', 'full_text_like_papers', 'abstract_only_papers', 'signal_profile',
        'support_example_notes', 'contradiction_example_notes', 'top_pmids',
    ])
    write_csv(claim_export_path, claim_export_rows, list(claim_export_rows[0].keys()) if claim_export_rows else [
        'pmid', 'paper_id', 'title', 'source_quality_tier', 'topic_anchor', 'claim_id', 'claim_text',
        'normalized_claim', 'atlas_layer', 'mechanism', 'canonical_mechanism',
        'canonical_mechanism_status', 'canonical_mechanism_basis', 'direction_of_effect', 'causal_status',
        'evidence_type', 'species', 'model', 'anatomy', 'cell_type', 'timing_bin', 'biomarkers',
        'biomarker_families', 'interventions', 'outcome_measures', 'confidence_score',
        'mechanistic_depth_score', 'translational_relevance_score', 'include_in_core_atlas',
        'whether_human_relevant', 'whether_mechanistically_informative', 'whether_needs_manual_review',
        'artifact_error_count', 'artifact_error_labels', 'artifact_read_error_count',
        'artifact_parse_error_count', 'artifact_missing_count', 'primary_domain', 'novelty_estimate',
    ])
    write_csv(edge_export_path, edge_export_rows, list(edge_export_rows[0].keys()) if edge_export_rows else [
        'pmid', 'paper_id', 'title', 'source_quality_tier', 'topic_anchor', 'edge_id', 'source_node',
        'source_node_key', 'relation', 'target_node', 'target_node_key', 'edge_key', 'atlas_layer',
        'anatomy', 'cell_type', 'timing_bin', 'species', 'evidence_strength', 'contradiction_flag',
        'notes', 'include_in_core_atlas', 'whether_human_relevant', 'whether_mechanistically_informative',
        'whether_needs_manual_review', 'artifact_error_count', 'artifact_error_labels',
        'artifact_read_error_count', 'artifact_parse_error_count', 'artifact_missing_count',
        'primary_domain', 'novelty_estimate',
    ])
    write_json(summary_json_path, summary)
    with open(summary_md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(summary))
    with open(investigation_brief_path, 'w', encoding='utf-8') as handle:
        handle.write(render_investigation_brief(summary))

    print(f'Post-extraction paper QA CSV written: {paper_qa_path}')
    print(f'Mechanism aggregation CSV written: {mechanism_path}')
    print(f'Canonical mechanism aggregation CSV written: {canonical_mechanism_path}')
    print(f'Atlas-layer aggregation CSV written: {atlas_path}')
    print(f'Biomarker aggregation CSV written: {biomarker_path}')
    print(f'Contradiction aggregation CSV written: {contradiction_path}')
    print(f'Investigation claims CSV written: {claim_export_path}')
    print(f'Investigation edges CSV written: {edge_export_path}')
    print(f'Post-extraction summary JSON written: {summary_json_path}')
    print(f'Post-extraction summary Markdown written: {summary_md_path}')
    print(f'TBI investigation brief written: {investigation_brief_path}')
    print(f'Papers analyzed: {summary["paper_count"]}')


if __name__ == '__main__':
    main()

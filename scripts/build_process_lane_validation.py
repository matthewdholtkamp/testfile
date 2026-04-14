import argparse
import json
import os
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_LANES = [
    'blood_brain_barrier_failure',
    'mitochondrial_bioenergetic_collapse',
    'neuroinflammation_microglial_state_change',
    'axonal_degeneration',
    'glymphatic_astroglial_clearance_failure',
    'tau_proteinopathy_progression',
]
REQUIRED_BUCKETS = ['acute', 'subacute', 'chronic']
VALID_STATUSES = {'supported', 'provisional', 'weak'}


def latest_report(pattern, preferred_dirs=None):
    preferred_dirs = preferred_dirs or []
    for directory in preferred_dirs:
        candidates = sorted(glob(os.path.join(REPO_ROOT, directory, pattern)))
        if candidates:
            return candidates[-1]
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def normalize(value):
    return ' '.join((value or '').split()).strip()


def main():
    parser = argparse.ArgumentParser(description='Validate Phase 1 process-lane artifacts.')
    parser.add_argument('--process-json', default='', help='Process lane JSON payload. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/process_lane_validation', help='Output directory for validation reports.')
    args = parser.parse_args()

    process_json = args.process_json or latest_report('process_lane_index_*.json', preferred_dirs=['reports/process_lanes'])
    payload = read_json(process_json)
    lanes = payload.get('lanes', [])
    summary_snapshot = payload.get('summary', {})
    lane_map = {normalize(lane.get('lane_id')): lane for lane in lanes}

    errors = []
    warnings = []

    for lane_id in REQUIRED_LANES:
        if lane_id not in lane_map:
            errors.append(f'Missing required lane: {lane_id}')

    for lane_id, lane in lane_map.items():
        canonical_mechanisms = lane.get('canonical_mechanisms', [])
        if not canonical_mechanisms:
            warnings.append(f'{lane_id} has no canonical atlas mechanism anchor yet; treat as seeded and monitor for drift')
            if int(lane.get('supported_buckets', 0) or 0) == 0:
                warnings.append(f'{lane_id} is regex/cross-signal seeded with zero supported buckets; do not treat it as a hardened longitudinal lane yet')
        buckets = lane.get('buckets', {})
        for bucket in REQUIRED_BUCKETS:
            if bucket not in buckets:
                errors.append(f'{lane_id} missing required bucket: {bucket}')
                continue
            bucket_summary = buckets[bucket]
            status = normalize(bucket_summary.get('status'))
            if status not in VALID_STATUSES:
                errors.append(f'{lane_id} {bucket} has invalid status: {status}')
            paper_count = int(bucket_summary.get('paper_count', 0) or 0)
            if status == 'supported' and paper_count == 0:
                errors.append(f'{lane_id} {bucket} is supported with zero papers')
            if status == 'weak' and paper_count > 0:
                warnings.append(f'{lane_id} {bucket} is weak despite {paper_count} papers; verify thresholding')
            if paper_count > 0 and not bucket_summary.get('anchor_pmids'):
                warnings.append(f'{lane_id} {bucket} has papers but no anchor PMIDs')
        if not lane.get('current_mechanism_overlap'):
            warnings.append(f'{lane_id} has no mapped overlap with current atlas mechanisms')
        if not lane.get('evidence_gaps'):
            warnings.append(f'{lane_id} has no evidence-gap notes')
        if not lane.get('lane_notes'):
            warnings.append(f'{lane_id} has no lane notes explaining provenance or current caution level')
        if not lane.get('causal_direction_notes'):
            warnings.append(f'{lane_id} has no causal-direction notes yet')

    metadata = payload.get('metadata', {})
    for field in ['claims_csv', 'edges_csv', 'paper_qa_csv']:
        if not normalize(metadata.get(field)):
            errors.append(f'Metadata missing provenance field: {field}')

    generated_at = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    report = {
        'validated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'valid': not errors,
        'process_json': os.path.relpath(process_json, REPO_ROOT),
        'summary': summary_snapshot,
        'summary_snapshot': summary_snapshot,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
        'validated_paths': {
            'process_json': os.path.relpath(process_json, REPO_ROOT),
        },
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    json_path = os.path.join(output_dir, f'process_lane_validation_{generated_at}.json')
    md_path = os.path.join(output_dir, f'process_lane_validation_{generated_at}.md')
    write_json(json_path, report)
    md_lines = [
        '# Process Lane Validation',
        '',
        f'- Valid: `{report["valid"]}`',
        f'- Source: `{report["process_json"]}`',
        f'- Lane count: `{summary_snapshot.get("lane_count", 0)}`',
        f'- Errors: `{len(errors)}`',
        f'- Warnings: `{len(warnings)}`',
        '',
        '## Summary',
        '',
        f'- Supported buckets: `{summary_snapshot.get("supported_buckets", 0)}`',
        f'- Provisional buckets: `{summary_snapshot.get("provisional_buckets", 0)}`',
        f'- Weak buckets: `{summary_snapshot.get("weak_buckets", 0)}`',
        f'- Longitudinally supported lanes: `{summary_snapshot.get("longitudinally_supported_lanes", 0)}`',
        f'- Longitudinally seeded lanes: `{summary_snapshot.get("longitudinally_seeded_lanes", 0)}`',
        '',
        '## Errors',
        '',
    ]
    if errors:
        md_lines.extend(f'- {item}' for item in errors)
    else:
        md_lines.append('- None')
    md_lines.extend(['', '## Warnings', ''])
    if warnings:
        md_lines.extend(f'- {item}' for item in warnings)
    else:
        md_lines.append('- None')
    write_text(md_path, '\n'.join(md_lines) + '\n')

    if errors:
        raise SystemExit(1)
    print(json_path)


if __name__ == '__main__':
    main()

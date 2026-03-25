import argparse
import os
import subprocess
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def has_csvs(path):
    return bool(path and os.path.isdir(path) and glob(os.path.join(path, '*.csv')))


def latest_optional_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def latest_csv_in_dir(path, pattern='*.csv'):
    candidates = sorted(glob(os.path.join(path, pattern)))
    return candidates[-1] if candidates else ''


def run_cmd(args):
    subprocess.run(args, check=True, cwd=REPO_ROOT)


def main():
    parser = argparse.ArgumentParser(
        description='Run the connector-enrichment sidecar locally: build candidate manifest, optionally normalize connector inputs, and rebuild mechanism dossiers.'
    )
    parser.add_argument(
        '--manifest-output-dir',
        default='reports/connector_candidate_manifest',
        help='Directory for connector candidate manifest outputs.',
    )
    parser.add_argument(
        '--enrichment-input-dir',
        default='local_connector_inputs',
        help='Directory containing connector CSV files to normalize before dossier rebuild.',
    )
    parser.add_argument(
        '--enrichment-output-dir',
        default='reports/connector_enrichment',
        help='Directory for normalized connector enrichment outputs.',
    )
    parser.add_argument(
        '--dossier-output-dir',
        default='reports/mechanism_dossiers',
        help='Directory for mechanism dossier outputs.',
    )
    parser.add_argument(
        '--curated-enrichment-output-dir',
        default='reports/connector_enrichment_curated',
        help='Directory for curated enrichment outputs when review decisions are applied.',
    )
    parser.add_argument(
        '--skip-manifest',
        action='store_true',
        help='Skip manifest generation and only normalize connector inputs / rebuild dossiers.',
    )
    parser.add_argument(
        '--mechanisms',
        default='',
        help='Optional comma-separated canonical mechanisms to forward to the dossier builder.',
    )
    parser.add_argument(
        '--fetch-public-connectors',
        action='store_true',
        help='Fetch first-pass Open Targets / ClinicalTrials.gov / bioRxiv-medRxiv CSVs into the enrichment input dir before normalization.',
    )
    parser.add_argument(
        '--public-connectors',
        default='open_targets,clinicaltrials_gov,biorxiv_medrxiv',
        help='Comma-separated public connectors for --fetch-public-connectors.',
    )
    parser.add_argument(
        '--review-csv',
        default='',
        help='Optional public_enrichment_review CSV to apply after normalization.',
    )
    parser.add_argument(
        '--apply-review',
        action='store_true',
        help='Apply the latest review sheet after normalization so curated enrichment becomes the dossier input.',
    )
    parser.add_argument(
        '--default-to-auto',
        action='store_true',
        help='When applying review decisions, use auto_recommendation if review_status is blank.',
    )
    args = parser.parse_args()

    manifest_csv = ''
    if not args.skip_manifest:
        run_cmd([
            'python3',
            'scripts/build_connector_candidate_manifest.py',
            '--output-dir',
            args.manifest_output_dir,
        ])
        manifest_csv = latest_csv_in_dir(args.manifest_output_dir, 'connector_candidate_manifest_*.csv')
    else:
        manifest_csv = latest_optional_report_path('connector_candidate_manifest_*.csv')

    enrichment_csv = ''
    if args.fetch_public_connectors:
        os.makedirs(args.enrichment_input_dir, exist_ok=True)
        run_cmd([
            'python3',
            'scripts/fetch_public_connector_enrichment.py',
            '--manifest-csv',
            manifest_csv,
            '--connectors',
            args.public_connectors,
            '--output-dir',
            args.enrichment_input_dir,
        ])

    if has_csvs(args.enrichment_input_dir):
        run_cmd([
            'python3',
            'scripts/merge_connector_enrichment.py',
            '--input-dir',
            args.enrichment_input_dir,
            '--output-dir',
            args.enrichment_output_dir,
        ])
        enrichment_csv = latest_optional_report_path('connector_enrichment_records_*.csv')
        if args.apply_review or args.review_csv:
            review_csv = args.review_csv or latest_optional_report_path('public_enrichment_review_*.csv')
            if not review_csv:
                raise FileNotFoundError('No review CSV found for --apply-review. Provide --review-csv or generate a review sheet first.')
            review_cmd = [
                'python3',
                'scripts/apply_enrichment_review.py',
                '--enrichment-csv',
                enrichment_csv,
                '--review-csv',
                review_csv,
                '--output-dir',
                args.curated_enrichment_output_dir,
            ]
            if args.default_to_auto:
                review_cmd.append('--default-to-auto')
            run_cmd(review_cmd)
            enrichment_csv = latest_optional_report_path('connector_enrichment_curated_*.csv')
    else:
        enrichment_csv = latest_optional_report_path('connector_enrichment_curated_*.csv') or latest_optional_report_path('connector_enrichment_records_*.csv')

    cmd = [
        'python3',
        'scripts/build_mechanism_dossiers.py',
        '--output-dir',
        args.dossier_output_dir,
    ]
    if enrichment_csv:
        cmd.extend(['--enrichment-csv', enrichment_csv])
    if args.mechanisms:
        cmd.extend(['--mechanisms', args.mechanisms])
    run_cmd(cmd)


if __name__ == '__main__':
    main()

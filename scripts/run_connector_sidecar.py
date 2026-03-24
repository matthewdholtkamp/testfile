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
        default='',
        help='Optional directory containing connector CSV files to normalize before dossier rebuild.',
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
        '--skip-manifest',
        action='store_true',
        help='Skip manifest generation and only normalize connector inputs / rebuild dossiers.',
    )
    parser.add_argument(
        '--mechanisms',
        default='',
        help='Optional comma-separated canonical mechanisms to forward to the dossier builder.',
    )
    args = parser.parse_args()

    if not args.skip_manifest:
        run_cmd([
            'python3',
            'scripts/build_connector_candidate_manifest.py',
            '--output-dir',
            args.manifest_output_dir,
        ])

    enrichment_csv = ''
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

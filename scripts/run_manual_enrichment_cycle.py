import argparse
import os
import subprocess
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_optional_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def latest_csv_in_dir(path, pattern):
    candidates = sorted(glob(os.path.join(path, pattern)))
    return candidates[-1] if candidates else ''


def run_cmd(args):
    subprocess.run(args, check=True, cwd=REPO_ROOT)


def main():
    parser = argparse.ArgumentParser(
        description='Run the local atlas curation loop: build manual seed packs, apply review decisions, rebuild curated dossiers, and emit a chapter draft.'
    )
    parser.add_argument(
        '--seed-pack-output-dir',
        default='reports/manual_enrichment_seed_pack',
        help='Directory for manual target/ChEMBL seed packs and review sheets.',
    )
    parser.add_argument(
        '--curated-enrichment-output-dir',
        default='reports/connector_enrichment_curated',
        help='Directory for curated enrichment outputs.',
    )
    parser.add_argument(
        '--dossier-output-dir',
        default='reports/mechanism_dossiers_curated',
        help='Directory for curated mechanism dossier outputs.',
    )
    parser.add_argument(
        '--chapter-output-dir',
        default='reports/atlas_chapter_draft_curated',
        help='Directory for the curated atlas chapter draft.',
    )
    parser.add_argument(
        '--chapter-synthesis-output-dir',
        default='reports/atlas_chapter_synthesis_draft_curated',
        help='Directory for the synthesis-driven atlas chapter draft.',
    )
    parser.add_argument(
        '--ledger-output-dir',
        default='reports/atlas_chapter_ledger_curated',
        help='Directory for the curated chapter evidence ledger.',
    )
    parser.add_argument(
        '--synthesis-output-dir',
        default='reports/mechanistic_synthesis_curated',
        help='Directory for the ledger-driven mechanistic synthesis packet.',
    )
    parser.add_argument(
        '--workpack-output-dir',
        default='reports/manual_enrichment_workpack',
        help='Directory for the manual enrichment workpack.',
    )
    parser.add_argument(
        '--viewer-output-dir',
        default='docs/atlas-viewer',
        help='Directory for the static atlas viewer bundle.',
    )
    parser.add_argument(
        '--atlas-output-dir',
        default='reports/starter_tbi_atlas',
        help='Directory for the consolidated atlas markdown/html outputs.',
    )
    parser.add_argument(
        '--atlas-site-dir',
        default='docs/atlas-book',
        help='Directory for the published atlas HTML site bundle.',
    )
    parser.add_argument(
        '--claims-csv',
        default='',
        help='Optional investigation_claims CSV for seed-pack generation.',
    )
    parser.add_argument(
        '--enrichment-csv',
        default='',
        help='Optional connector_enrichment_records CSV for seed-pack generation and review application.',
    )
    parser.add_argument(
        '--review-csv',
        default='',
        help='Optional review CSV. Defaults to the latest public_enrichment_review sheet.',
    )
    parser.add_argument(
        '--mechanisms',
        default='',
        help='Optional comma-separated canonical mechanisms to forward to the dossier builder.',
    )
    parser.add_argument(
        '--skip-seed-pack',
        action='store_true',
        help='Skip seed-pack generation and use the latest existing review sheet.',
    )
    parser.add_argument(
        '--skip-review-apply',
        action='store_true',
        help='Skip review application and rebuild dossiers from the latest curated or raw enrichment CSV.',
    )
    parser.add_argument(
        '--default-to-auto',
        action='store_true',
        help='Apply auto_recommendation when review_status is blank.',
    )
    args = parser.parse_args()

    enrichment_csv = args.enrichment_csv or latest_optional_report_path('connector_enrichment_records_*.csv')

    if not args.skip_seed_pack:
        cmd = [
            'python3',
            'scripts/build_manual_enrichment_seed_pack.py',
            '--output-dir',
            args.seed_pack_output_dir,
        ]
        if args.claims_csv:
            cmd.extend(['--claims-csv', args.claims_csv])
        if enrichment_csv:
            cmd.extend(['--enrichment-csv', enrichment_csv])
        run_cmd(cmd)

    review_csv = args.review_csv or latest_csv_in_dir(args.seed_pack_output_dir, 'public_enrichment_review_*.csv')
    curated_csv = ''

    if not args.skip_review_apply:
        if not review_csv:
            raise FileNotFoundError('No review CSV found. Run without --skip-seed-pack or provide --review-csv.')
        if not enrichment_csv:
            raise FileNotFoundError('No connector enrichment CSV found. Provide --enrichment-csv or generate enrichment first.')
        cmd = [
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
            cmd.append('--default-to-auto')
        run_cmd(cmd)
        curated_csv = latest_csv_in_dir(args.curated_enrichment_output_dir, 'connector_enrichment_curated_*.csv')
    else:
        curated_csv = latest_csv_in_dir(args.curated_enrichment_output_dir, 'connector_enrichment_curated_*.csv') or enrichment_csv

    dossier_cmd = [
        'python3',
        'scripts/build_mechanism_dossiers.py',
        '--output-dir',
        args.dossier_output_dir,
    ]
    if curated_csv:
        dossier_cmd.extend(['--enrichment-csv', curated_csv])
    if args.mechanisms:
        dossier_cmd.extend(['--mechanisms', args.mechanisms])
    run_cmd(dossier_cmd)

    run_cmd([
        'python3',
        'scripts/build_atlas_chapter_from_dossiers.py',
        '--dossier-dir',
        args.dossier_output_dir,
        '--output-dir',
        args.chapter_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_atlas_chapter_evidence_ledger.py',
        '--dossier-dir',
        args.dossier_output_dir,
        '--output-dir',
        args.ledger_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_mechanistic_synthesis.py',
        '--ledger-csv',
        latest_csv_in_dir(args.ledger_output_dir, 'starter_atlas_chapter_evidence_ledger_*.csv'),
        '--bridge-csv',
        latest_csv_in_dir(args.dossier_output_dir, 'translational_bridge_*.csv'),
        '--output-dir',
        args.synthesis_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_atlas_chapter_from_synthesis.py',
        '--synthesis-csv',
        latest_csv_in_dir(args.synthesis_output_dir, 'mechanistic_synthesis_blocks_*.csv'),
        '--output-dir',
        args.chapter_synthesis_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_manual_enrichment_workpack.py',
        '--seed-pack-csv',
        latest_csv_in_dir(args.seed_pack_output_dir, 'target_seed_pack_*.csv'),
        '--ledger-csv',
        latest_csv_in_dir(args.ledger_output_dir, 'starter_atlas_chapter_evidence_ledger_*.csv'),
        '--chembl-template-csv',
        latest_csv_in_dir(args.seed_pack_output_dir, 'chembl_manual_fill_template_*.csv'),
        '--open-targets-template-csv',
        latest_csv_in_dir(args.seed_pack_output_dir, 'open_targets_manual_fill_template_*.csv'),
        '--output-dir',
        args.workpack_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_atlas_viewer.py',
        '--output-dir',
        args.viewer_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_tbi_atlas_book.py',
        '--output-dir',
        args.atlas_output_dir,
        '--site-dir',
        args.atlas_site_dir,
    ])

    chapter_md = latest_csv_in_dir(args.chapter_output_dir, 'starter_atlas_chapter_draft_*.md')
    chapter_synthesis_md = latest_csv_in_dir(args.chapter_synthesis_output_dir, 'starter_atlas_chapter_synthesis_draft_*.md')
    ledger_md = latest_csv_in_dir(args.ledger_output_dir, 'starter_atlas_chapter_evidence_ledger_*.md')
    synthesis_md = latest_csv_in_dir(args.synthesis_output_dir, 'mechanistic_synthesis_index_*.md')
    workpack_md = latest_csv_in_dir(args.workpack_output_dir, 'manual_enrichment_workpack_*.md')
    viewer_path = os.path.join(args.viewer_output_dir, 'index.html')
    atlas_path = latest_csv_in_dir(args.atlas_output_dir, 'starter_tbi_atlas_*.html')
    print(f'Manual enrichment cycle complete. Latest chapter draft: {chapter_md}')
    print(f'Latest chapter synthesis draft: {chapter_synthesis_md}')
    print(f'Latest evidence ledger: {ledger_md}')
    print(f'Latest mechanistic synthesis index: {synthesis_md}')
    print(f'Latest manual workpack: {workpack_md}')
    print(f'Latest atlas viewer: {viewer_path}')
    print(f'Latest atlas book: {atlas_path}')


if __name__ == '__main__':
    main()

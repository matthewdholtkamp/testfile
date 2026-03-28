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
        description='Run the local atlas curation loop: build assisted manual seed packs, apply review decisions, rebuild curated dossiers, and emit atlas-facing outputs.'
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
        '--quality-gate-output-dir',
        default='reports/atlas_quality_gate',
        help='Directory for atlas quality-gate outputs.',
    )
    parser.add_argument(
        '--review-packet-output-dir',
        default='reports/mechanism_review_packets',
        help='Directory for mechanism review packet outputs.',
    )
    parser.add_argument(
        '--idea-gate-output-dir',
        default='reports/idea_generation_gate',
        help='Directory for idea-generation gate outputs.',
    )
    parser.add_argument(
        '--target-packet-output-dir',
        default='reports/target_enrichment_packets',
        help='Directory for target enrichment packet outputs.',
    )
    parser.add_argument(
        '--program-status-output-dir',
        default='reports/program_status',
        help='Directory for program-status outputs.',
    )
    parser.add_argument(
        '--release-manifest-output-dir',
        default='reports/atlas_release_manifest',
        help='Directory for atlas release-manifest outputs.',
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
    parser.add_argument(
        '--priority-mode',
        choices=['default', 'mitochondrial_first'],
        default='mitochondrial_first',
        help='Priority mode for manual seed packs and target packets.',
    )
    parser.add_argument(
        '--target-packet-top-n',
        type=int,
        default=10,
        help='Maximum number of target enrichment packets to emit.',
    )
    args = parser.parse_args()

    enrichment_csv = args.enrichment_csv or latest_optional_report_path('connector_enrichment_records_*.csv')

    if not args.skip_seed_pack:
        cmd = [
            'python3',
            'scripts/build_manual_enrichment_seed_pack.py',
            '--output-dir',
            args.seed_pack_output_dir,
            '--priority-mode',
            args.priority_mode,
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
        'scripts/build_atlas_quality_gate.py',
        '--output-dir',
        args.quality_gate_output_dir,
        '--synthesis-csv',
        latest_csv_in_dir(args.synthesis_output_dir, 'mechanistic_synthesis_blocks_*.csv'),
    ])
    run_cmd([
        'python3',
        'scripts/build_mechanism_review_packets.py',
        '--output-dir',
        args.review_packet_output_dir,
        '--quality-gate-csv',
        latest_csv_in_dir(args.quality_gate_output_dir, 'atlas_quality_gate_*.csv'),
        '--synthesis-csv',
        latest_csv_in_dir(args.synthesis_output_dir, 'mechanistic_synthesis_blocks_*.csv'),
    ])
    run_cmd([
        'python3',
        'scripts/build_atlas_release_manifest.py',
        '--output-dir',
        args.release_manifest_output_dir,
        '--quality-gate-csv',
        latest_csv_in_dir(args.quality_gate_output_dir, 'atlas_quality_gate_*.csv'),
    ])
    run_cmd([
        'python3',
        'scripts/build_idea_generation_gate.py',
        '--output-dir',
        args.idea_gate_output_dir,
        '--release-manifest-csv',
        latest_csv_in_dir(args.release_manifest_output_dir, 'atlas_release_manifest_*.csv'),
    ])
    run_cmd([
        'python3',
        'scripts/build_hypothesis_candidates.py',
        '--output-dir',
        'reports/hypothesis_candidates',
    ])
    run_cmd([
        'python3',
        'scripts/build_idea_briefs.py',
        '--output-dir',
        'reports/idea_briefs',
        '--site-dir',
        'docs/idea-briefs',
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
        'scripts/build_target_enrichment_packets.py',
        '--output-dir',
        args.target_packet_output_dir,
        '--target-seed-csv',
        latest_csv_in_dir(args.seed_pack_output_dir, 'target_seed_pack_*.csv'),
        '--open-targets-template-csv',
        latest_csv_in_dir(args.seed_pack_output_dir, 'open_targets_manual_fill_template_*.csv'),
        '--chembl-template-csv',
        latest_csv_in_dir(args.seed_pack_output_dir, 'chembl_manual_fill_template_*.csv'),
        '--priority-mode',
        args.priority_mode,
        '--top-n',
        str(args.target_packet_top_n),
    ])
    run_cmd([
        'python3',
        'scripts/build_atlas_viewer.py',
        '--output-dir',
        args.viewer_output_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_process_lanes.py',
        '--output-dir',
        'reports/process_lanes',
    ])
    latest_process_json = latest_csv_in_dir('reports/process_lanes', 'process_lane_index_*.json')
    run_cmd([
        'python3',
        'scripts/build_process_lane_validation.py',
        '--process-json',
        latest_process_json,
        '--output-dir',
        'reports/process_lane_validation',
    ])
    run_cmd([
        'python3',
        'scripts/build_process_engine_page.py',
        '--process-json',
        latest_process_json,
        '--output-dir',
        'docs/process-engine',
    ])
    run_cmd([
        'python3',
        'scripts/build_causal_transitions.py',
        '--output-dir',
        'reports/causal_transitions',
    ])
    latest_transition_json = latest_csv_in_dir('reports/causal_transitions', 'causal_transition_index_*.json')
    run_cmd([
        'python3',
        'scripts/build_causal_transition_validation.py',
        '--transition-json',
        latest_transition_json,
        '--output-dir',
        'reports/causal_transition_validation',
    ])
    run_cmd([
        'python3',
        'scripts/build_process_model_page.py',
        '--transition-json',
        latest_transition_json,
        '--output-dir',
        'docs/process-model',
    ])
    run_cmd([
        'python3',
        'scripts/build_progression_objects.py',
        '--output-dir',
        'reports/progression_objects',
    ])
    latest_progression_json = latest_csv_in_dir('reports/progression_objects', 'progression_object_index_*.json')
    run_cmd([
        'python3',
        'scripts/build_progression_object_validation.py',
        '--object-json',
        latest_progression_json,
        '--process-json',
        latest_process_json,
        '--transition-json',
        latest_transition_json,
        '--output-dir',
        'reports/progression_object_validation',
    ])
    run_cmd([
        'python3',
        'scripts/build_progression_object_page.py',
        '--object-json',
        latest_progression_json,
        '--output-dir',
        'docs/progression-objects',
    ])
    run_cmd([
        'python3',
        'scripts/build_translational_perturbation_logic.py',
        '--process-json',
        latest_process_json,
        '--transition-json',
        latest_transition_json,
        '--object-json',
        latest_progression_json,
        '--output-dir',
        'reports/translational_perturbation',
    ])
    latest_translational_json = latest_csv_in_dir('reports/translational_perturbation', 'translational_perturbation_index_*.json')
    run_cmd([
        'python3',
        'scripts/build_translational_perturbation_validation.py',
        '--translational-json',
        latest_translational_json,
        '--process-json',
        latest_process_json,
        '--transition-json',
        latest_transition_json,
        '--object-json',
        latest_progression_json,
        '--output-dir',
        'reports/translational_perturbation_validation',
    ])
    run_cmd([
        'python3',
        'scripts/build_translational_perturbation_page.py',
        '--translational-json',
        latest_translational_json,
        '--validation-json',
        latest_csv_in_dir('reports/translational_perturbation_validation', 'translational_perturbation_validation_*.json'),
        '--output-dir',
        'docs/translational-logic',
    ])
    run_cmd([
        'python3',
        'scripts/build_tbi_atlas_book.py',
        '--output-dir',
        args.atlas_output_dir,
        '--site-dir',
        args.atlas_site_dir,
    ])
    run_cmd([
        'python3',
        'scripts/build_portal_page.py',
        '--output-path',
        'docs/index.html',
    ])
    run_cmd([
        'python3',
        'scripts/build_run_center_page.py',
        '--output-path',
        'docs/run-center/index.html',
    ])
    run_cmd([
        'python3',
        'scripts/build_program_status_report.py',
        '--output-dir',
        args.program_status_output_dir,
        '--quality-gate-csv',
        latest_csv_in_dir(args.quality_gate_output_dir, 'atlas_quality_gate_*.csv'),
        '--idea-gate-csv',
        latest_csv_in_dir(args.idea_gate_output_dir, 'idea_generation_gate_*.csv'),
        '--review-packet-index-md',
        latest_csv_in_dir(args.review_packet_output_dir, 'mechanism_review_packet_index_*.md'),
        '--target-packet-index-md',
        latest_csv_in_dir(args.target_packet_output_dir, 'target_enrichment_packet_index_*.md'),
    ])

    chapter_md = latest_csv_in_dir(args.chapter_output_dir, 'starter_atlas_chapter_draft_*.md')
    chapter_synthesis_md = latest_csv_in_dir(args.chapter_synthesis_output_dir, 'starter_atlas_chapter_synthesis_draft_*.md')
    ledger_md = latest_csv_in_dir(args.ledger_output_dir, 'starter_atlas_chapter_evidence_ledger_*.md')
    synthesis_md = latest_csv_in_dir(args.synthesis_output_dir, 'mechanistic_synthesis_index_*.md')
    workpack_md = latest_csv_in_dir(args.workpack_output_dir, 'manual_enrichment_workpack_*.md')
    quality_gate_md = latest_csv_in_dir(args.quality_gate_output_dir, 'atlas_quality_gate_*.md')
    idea_gate_md = latest_csv_in_dir(args.idea_gate_output_dir, 'idea_generation_gate_*.md')
    review_packet_md = latest_csv_in_dir(args.review_packet_output_dir, 'mechanism_review_packet_index_*.md')
    target_packet_md = latest_csv_in_dir(args.target_packet_output_dir, 'target_enrichment_packet_index_*.md')
    program_status_md = latest_csv_in_dir(args.program_status_output_dir, 'program_status_report_*.md')
    viewer_path = os.path.join(args.viewer_output_dir, 'index.html')
    process_engine_path = os.path.join('docs', 'process-engine', 'index.html')
    process_model_path = os.path.join('docs', 'process-model', 'index.html')
    progression_object_path = os.path.join('docs', 'progression-objects', 'index.html')
    translational_logic_path = os.path.join('docs', 'translational-logic', 'index.html')
    atlas_path = latest_csv_in_dir(args.atlas_output_dir, 'starter_tbi_atlas_*.html')
    print(f'Manual enrichment cycle complete. Latest chapter draft: {chapter_md}')
    print(f'Latest chapter synthesis draft: {chapter_synthesis_md}')
    print(f'Latest evidence ledger: {ledger_md}')
    print(f'Latest mechanistic synthesis index: {synthesis_md}')
    print(f'Latest atlas quality gate: {quality_gate_md}')
    print(f'Latest idea generation gate: {idea_gate_md}')
    print(f'Latest mechanism review packets: {review_packet_md}')
    print(f'Latest manual workpack: {workpack_md}')
    print(f'Latest target enrichment packets: {target_packet_md}')
    print(f'Latest atlas viewer: {viewer_path}')
    print(f'Latest process engine page: {process_engine_path}')
    print(f'Latest process model page: {process_model_path}')
    print(f'Latest progression object page: {progression_object_path}')
    print(f'Latest translational logic page: {translational_logic_path}')
    print(f'Latest atlas book: {atlas_path}')
    print(f'Latest program status report: {program_status_md}')


if __name__ == '__main__':
    main()

import argparse
import csv
import json
import os
import sqlite3
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_optional(path_pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, path_pattern)))
    return candidates[-1] if candidates else ''


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def ensure_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_files (
            file_id TEXT PRIMARY KEY,
            name TEXT,
            pmid TEXT,
            extraction_rank TEXT,
            extraction_source TEXT,
            content_length INTEGER,
            valid_metadata_block TEXT,
            modified_time TEXT,
            mime_type TEXT,
            size INTEGER,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS extraction_manifest (
            paper_id TEXT PRIMARY KEY,
            md_path TEXT,
            source_query TEXT,
            domain TEXT,
            tier TEXT,
            retrieval_mode TEXT,
            extraction_status TEXT,
            extraction_version TEXT,
            extracted_at TEXT,
            checksum TEXT,
            last_error TEXT,
            drive_file_id TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS extraction_state (
            paper_id TEXT PRIMARY KEY,
            extraction_status TEXT,
            extracted_at TEXT,
            checksum TEXT,
            drive_file_id TEXT,
            last_error TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pipeline_state_kv (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inventory_summary (
            snapshot_key TEXT,
            metric_key TEXT,
            metric_value TEXT,
            PRIMARY KEY (snapshot_key, metric_key)
        );
        """
    )


def materialize_source_files(conn, inventory_csv):
    if not inventory_csv or not os.path.exists(inventory_csv):
        return 0
    rows = read_csv(inventory_csv)
    conn.execute('DELETE FROM source_files')
    for row in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO source_files (
                file_id, name, pmid, extraction_rank, extraction_source, content_length,
                valid_metadata_block, modified_time, mime_type, size, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalize(row.get('file_id')),
                normalize(row.get('name')),
                normalize(row.get('pmid')),
                normalize(row.get('extraction_rank')),
                normalize(row.get('extraction_source')),
                int(float(row.get('content_length') or 0)) if normalize(row.get('content_length')) else None,
                normalize(row.get('valid_metadata_block')),
                normalize(row.get('modified_time')),
                normalize(row.get('mime_type')),
                int(float(row.get('size') or 0)) if normalize(row.get('size')) else None,
                json.dumps(row, sort_keys=True),
            ),
        )
    return len(rows)


def materialize_extraction_manifest(conn, manifest_csv):
    if not manifest_csv or not os.path.exists(manifest_csv):
        return 0
    rows = read_csv(manifest_csv)
    conn.execute('DELETE FROM extraction_manifest')
    for row in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO extraction_manifest (
                paper_id, md_path, source_query, domain, tier, retrieval_mode,
                extraction_status, extraction_version, extracted_at, checksum,
                last_error, drive_file_id, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalize(row.get('paper_id')),
                normalize(row.get('md_path')),
                normalize(row.get('source_query')),
                normalize(row.get('domain')),
                normalize(row.get('tier')),
                normalize(row.get('retrieval_mode')),
                normalize(row.get('extraction_status')),
                normalize(row.get('extraction_version')),
                normalize(row.get('extracted_at')),
                normalize(row.get('checksum')),
                normalize(row.get('last_error')),
                normalize(row.get('drive_file_id')),
                json.dumps(row, sort_keys=True),
            ),
        )
    return len(rows)


def materialize_extraction_state(conn, extraction_state_json):
    if not extraction_state_json or not os.path.exists(extraction_state_json):
        return 0
    payload = read_json(extraction_state_json)
    conn.execute('DELETE FROM extraction_state')
    for paper_id, row in sorted((payload or {}).items()):
        row = row or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO extraction_state (
                paper_id, extraction_status, extracted_at, checksum, drive_file_id, last_error, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalize(paper_id),
                normalize(row.get('extraction_status')),
                normalize(row.get('extracted_at')),
                normalize(row.get('checksum')),
                normalize(row.get('drive_file_id')),
                normalize(row.get('last_error')),
                json.dumps(row, sort_keys=True),
            ),
        )
    return len(payload or {})


def materialize_pipeline_state(conn, pipeline_state_json):
    if not pipeline_state_json or not os.path.exists(pipeline_state_json):
        return 0
    payload = read_json(pipeline_state_json)
    conn.execute('DELETE FROM pipeline_state_kv')
    for key, value in sorted((payload or {}).items()):
        conn.execute(
            'INSERT OR REPLACE INTO pipeline_state_kv (key, value_json) VALUES (?, ?)',
            (normalize(key), json.dumps(value, sort_keys=True)),
        )
    return len(payload or {})


def materialize_inventory_summary(conn, summary_json):
    if not summary_json or not os.path.exists(summary_json):
        return 0
    payload = read_json(summary_json)
    snapshot_key = os.path.basename(summary_json)
    conn.execute('DELETE FROM inventory_summary')
    for key, value in sorted((payload or {}).items()):
        conn.execute(
            'INSERT OR REPLACE INTO inventory_summary (snapshot_key, metric_key, metric_value) VALUES (?, ?, ?)',
            (snapshot_key, normalize(key), json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)),
        )
    return len(payload or {})


def write_metadata(conn, metadata):
    conn.execute('DELETE FROM metadata')
    for key, value in sorted(metadata.items()):
        conn.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)', (key, normalize(value)))


def main():
    parser = argparse.ArgumentParser(description='Materialize a read-only SQLite sidecar from Drive inventory and pipeline state mirrors.')
    parser.add_argument('--inventory-csv', default='', help='Optional drive inventory CSV.')
    parser.add_argument('--inventory-summary-json', default='', help='Optional drive inventory summary JSON.')
    parser.add_argument('--manifest-csv', default='outputs/state/extraction_manifest.csv', help='Optional extraction manifest CSV.')
    parser.add_argument('--extraction-state-json', default='outputs/state/extraction_state.json', help='Optional extraction state JSON.')
    parser.add_argument('--pipeline-state-json', default='output/pipeline_state.json', help='Optional pipeline state JSON.')
    parser.add_argument('--output-path', default='outputs/state/corpus_index.sqlite3', help='SQLite output path.')
    args = parser.parse_args()

    inventory_csv = args.inventory_csv or latest_optional('reports/drive_inventory_*.csv')
    inventory_summary_json = args.inventory_summary_json or latest_optional('reports/drive_inventory_summary_*.json')
    manifest_csv = os.path.join(REPO_ROOT, args.manifest_csv) if not os.path.isabs(args.manifest_csv) else args.manifest_csv
    extraction_state_json = os.path.join(REPO_ROOT, args.extraction_state_json) if not os.path.isabs(args.extraction_state_json) else args.extraction_state_json
    pipeline_state_json = os.path.join(REPO_ROOT, args.pipeline_state_json) if not os.path.isabs(args.pipeline_state_json) else args.pipeline_state_json
    output_path = os.path.join(REPO_ROOT, args.output_path) if not os.path.isabs(args.output_path) else args.output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    conn = sqlite3.connect(output_path)
    try:
        ensure_schema(conn)
        source_count = materialize_source_files(conn, inventory_csv)
        manifest_count = materialize_extraction_manifest(conn, manifest_csv)
        state_count = materialize_extraction_state(conn, extraction_state_json)
        pipeline_key_count = materialize_pipeline_state(conn, pipeline_state_json)
        summary_key_count = materialize_inventory_summary(conn, inventory_summary_json)
        write_metadata(
            conn,
            {
                'generated_at': datetime.now().isoformat(timespec='seconds'),
                'inventory_csv': inventory_csv,
                'inventory_summary_json': inventory_summary_json,
                'manifest_csv': manifest_csv if os.path.exists(manifest_csv) else '',
                'extraction_state_json': extraction_state_json if os.path.exists(extraction_state_json) else '',
                'pipeline_state_json': pipeline_state_json if os.path.exists(pipeline_state_json) else '',
                'source_count': str(source_count),
                'manifest_count': str(manifest_count),
                'state_count': str(state_count),
                'pipeline_key_count': str(pipeline_key_count),
                'summary_key_count': str(summary_key_count),
            },
        )
        conn.commit()
    finally:
        conn.close()

    print(f'Sidecar SQLite written: {output_path}')
    print(f'Source rows: {source_count}')
    print(f'Extraction manifest rows: {manifest_count}')
    print(f'Extraction state rows: {state_count}')
    print(f'Pipeline state keys: {pipeline_key_count}')
    print(f'Inventory summary keys: {summary_key_count}')


if __name__ == '__main__':
    main()

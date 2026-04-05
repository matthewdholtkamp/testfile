import argparse
import json
import os
import sqlite3


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def main():
    parser = argparse.ArgumentParser(description='Query the read-only SQLite corpus sidecar.')
    parser.add_argument('--db-path', default='outputs/state/corpus_index.sqlite3', help='SQLite sidecar path.')
    parser.add_argument('--pmid', default='', help='Optional PMID filter.')
    parser.add_argument('--limit', type=int, default=20, help='Maximum rows to return.')
    args = parser.parse_args()

    db_path = os.path.join(REPO_ROOT, args.db_path) if not os.path.isabs(args.db_path) else args.db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if normalize(args.pmid):
            rows = conn.execute(
                """
                SELECT source_files.file_id, source_files.name, source_files.pmid, source_files.modified_time,
                       extraction_manifest.extraction_status, extraction_manifest.extracted_at
                FROM source_files
                LEFT JOIN extraction_manifest
                  ON extraction_manifest.paper_id = CASE
                      WHEN source_files.pmid LIKE 'PMID%' THEN source_files.pmid
                      WHEN source_files.pmid != '' THEN 'PMID' || source_files.pmid
                      ELSE ''
                  END
                WHERE source_files.pmid = ? OR source_files.pmid = ?
                ORDER BY source_files.modified_time DESC
                LIMIT ?
                """,
                (args.pmid.replace('PMID', ''), normalize(args.pmid), args.limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT file_id, name, pmid, modified_time, mime_type
                FROM source_files
                ORDER BY modified_time DESC
                LIMIT ?
                """,
                (args.limit,),
            ).fetchall()
        print(json.dumps([dict(row) for row in rows], indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()

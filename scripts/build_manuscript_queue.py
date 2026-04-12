import json

from dashboard_ui import load_direction_registry, load_project_state
from manuscript_phase8 import (
    JOURNAL_REGISTRY_PATH,
    MANUSCRIPT_QUEUE_STATE_PATH,
    MANUSCRIPT_ROOT,
    PUBLICATION_TRACKER_STATE_PATH,
    load_journal_registry,
    load_publication_tracker,
    materialize_manuscript_outputs,
)


def main():
    state = load_project_state()
    direction_registry = load_direction_registry()
    publication_tracker = load_publication_tracker(PUBLICATION_TRACKER_STATE_PATH)
    journal_registry = load_journal_registry(JOURNAL_REGISTRY_PATH)
    queue = materialize_manuscript_outputs(
        state,
        direction_registry=direction_registry,
        publication_tracker=publication_tracker,
        journal_registry=journal_registry,
        manuscript_root=MANUSCRIPT_ROOT,
        queue_state_path=MANUSCRIPT_QUEUE_STATE_PATH,
        publication_state_path=PUBLICATION_TRACKER_STATE_PATH,
    )
    print(json.dumps({
        'generated_at': queue.get('generated_at'),
        'active_candidates': len(queue.get('active_candidates') or []),
        'watchlist': len(queue.get('watchlist') or []),
        'tracked_publications': len(queue.get('publication_tracker') or []),
    }, indent=2))


if __name__ == '__main__':
    main()

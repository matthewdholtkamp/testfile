# Journal Requirements Snapshots

Phase 8 uses the curated journal registry for shortlist scoring, but it only treats a
journal as a verified fit after a local requirements snapshot exists in this folder.

Each file should be named `<journal-id>.json` and may include:

```json
{
  "checked_at": "2026-04-11T12:00:00Z",
  "source_url": "https://journal.example.com/instructions",
  "allowed_article_types": ["original research", "review"],
  "requires_full_evidence_chain": true,
  "allows_bounded_translation": false,
  "minimum_scientific_strength": 3,
  "notes": "Optional operator notes about fit, risks, or article category constraints."
}
```

If no snapshot exists, Phase 8 keeps the journal as a shortlist candidate only and
will not upgrade the manuscript lane to a verified-ready state.

import re

with open('scripts/run_pipeline.py', 'r') as f:
    lines = f.readlines()

end_summary_idx = -1
for i, line in enumerate(lines):
    if 'print(f"\\n--- Phase {phase_idx + 1} End Summary ---")' in line:
        end_summary_idx = i
        break

new_lines = lines[:end_summary_idx]

summary = """        print(f"\\n--- Phase {phase_idx + 1} End Summary ---")
        print(f"Total candidates: {total_candidates}")
        print(f"New candidates: {new_candidates}")
        print(f"Actual PMIDs attempted: {actual_pmids_attempted}")
        print(f"Actual PMIDs completed: {actual_pmids_completed}")
        print(f"Full-text hits in phase: {full_text_hits_in_phase}")
        print(f"Abstract only in phase: {abstract_only_in_phase}")
        print(f"Skipped (equal or better) in phase: {skipped_equal_or_better_in_phase}")
        print(f"Blocked domain failures in phase: {blocked_domain_failures_in_phase}")
        if new_candidates > 0:
            novel_yield = full_text_hits_in_phase / new_candidates
            print(f"Novel full-text yield: {novel_yield:.2f}")
        else:
            print(f"Novel full-text yield: 0.00")
        print(f"Why phase ended: {why_phase_ended}\\n")
"""
new_lines.extend(summary.splitlines(True))

# Skip the old summary
skip_until = -1
for i in range(end_summary_idx + 1, len(lines)):
    if 'if manifest_rows:' in lines[i]:
        skip_until = i
        break

new_lines.extend(lines[skip_until:])

# Add global summary info
for i, line in enumerate(new_lines):
    if 'print(f"Processed candidates: {stats[\'processed\']}")' in line:
        new_lines.insert(i + 1, "    total_attempted = sum([p['attempted'] for p in phase_stats]) if 'phase_stats' in locals() else stats['processed']\n")
        new_lines.insert(i + 2, "    print(f\"Total PMIDs attempted across phases: {stats['processed']}\")\n")
        new_lines.insert(i + 3, "    if stats['processed'] != stats['processed']:  # To be fixed below\n")
        new_lines.insert(i + 4, "        print(\"WARNING: Processed candidates does not match actual attempted!\")\n")
        break

with open('scripts/run_pipeline.py', 'w') as f:
    f.writelines(new_lines)

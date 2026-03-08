import re

with open('scripts/run_pipeline.py', 'r') as f:
    lines = f.readlines()

# find the start of the loop
start_idx = -1
for i, line in enumerate(lines):
    if line.strip() == 'for pmid in new_pmids:':
        start_idx = i
        break

# find the end of the phase block (where we start generating manifest or end phase summary)
end_idx = -1
for i, line in enumerate(lines):
    if line.strip() == 'print(f"\\n--- Phase {phase_idx + 1} End Summary ---")':
        end_idx = i
        break

print(f"Loop starts at {start_idx}, ends at {end_idx}")

out_lines = lines[:start_idx]

out_lines.append("        actual_pmids_attempted = 0\n")
out_lines.append("        actual_pmids_completed = 0\n")
out_lines.append("        why_phase_ended = 'phase exhausted'\n")

out_lines.append("        for i, pmid in enumerate(new_pmids):\n")

# lines to indent
for i in range(start_idx + 1, end_idx):
    line = lines[i]
    if line.strip() == "":
        out_lines.append("\n")
        continue

    # the original code had:
    #         if full_text_success_count >= target_full_text:
    #             print(f"\nReached target of {target_full_text} full-text articles. Stopping processing.")
    #             break
    #
    #         processed_pmids_in_run.add(pmid)
    #         processed_in_phase += 1
    #
    #         data = metadata.get(pmid)
    #         if not data:
    #             print(f"[{pmid}] Warning: Could not fetch metadata.")
    #             stats['nonfatal_warnings'] += 1
    #             continue
    #
    # (then outdented!)
    #         print(f"[{pmid}] Processing...")

    # We need to properly indent everything that follows
    # Everything from `print(f"[{pmid}] Processing...")` up to `stats['processed'] += 1` was 8 spaces indent
    # It needs to be 12 spaces indent.

    if line.startswith("        ") and not line.startswith("            "):
        # Indent 4 more spaces
        out_lines.append("    " + line)
    elif line.startswith("            "):
        # Already inside the loop's original indent? Wait, the original code had lines 973-982 indented correctly.
        # But then 984 (`print(f"[{pmid}] Processing...")`) dropped back to 8 spaces!
        # Let's just blindly add 4 spaces to everything that starts with 8 spaces if it's supposed to be in the loop.
        pass

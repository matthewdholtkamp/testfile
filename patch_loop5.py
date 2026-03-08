import re

with open('scripts/run_pipeline.py', 'r') as f:
    lines = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if line.strip() == 'for pmid in new_pmids:':
        start_idx = i
        break

end_idx = -1
for i, line in enumerate(lines):
    if line.strip() == 'print(f"\\n--- Phase {phase_idx + 1} End Summary ---")':
        end_idx = i
        break

new_lines = []
new_lines.extend(lines[:start_idx])

new_lines.append("        actual_pmids_attempted = 0\n")
new_lines.append("        actual_pmids_completed = 0\n")
new_lines.append("        why_phase_ended = 'phase exhausted'\n")
new_lines.append("        for i, pmid in enumerate(new_pmids):\n")
new_lines.append("            actual_pmids_attempted += 1\n")
new_lines.append("            print(f\"Phase {phase_idx + 1} | PMID {pmid} | Index {i + 1}/{len(new_pmids)}\")\n")

for i in range(start_idx + 1, end_idx):
    line = lines[i]
    if line.strip() == "":
        new_lines.append(line)
        continue

    # We want everything in the loop to be correctly indented.
    # Lines originally inside the loop (up to `continue`) have 12 spaces.
    # Lines originally outside the loop (from `print(f"[{pmid}] Processing...")`) have 8 spaces.

    current_indent = len(line) - len(line.lstrip(' '))

    if "print(f\"[{pmid}] Processing...\")" in line:
        # Start indenting everything by 4 spaces
        new_lines.append("    " + line)
        for j in range(i + 1, end_idx):
            line_j = lines[j]
            if line_j.strip() == "":
                new_lines.append(line_j)
            else:
                new_lines.append("    " + line_j)
        break
    else:
        new_lines.append(line)

# Now iterate over new_lines to fix specific accounting things
final_lines = []
for idx, line in enumerate(new_lines):
    if line.strip() == "stats['processed'] += 1":
        final_lines.append("            stats['processed'] += 1\n")
        final_lines.append("            actual_pmids_completed += 1\n")
        continue

    if "Reached target of {target_full_text} full-text articles. Stopping processing." in line:
        final_lines.append(line)
        final_lines.append("                why_phase_ended = 'target reached'\n")
        continue

    if line.strip() == "continue" and "stats['nonfatal_warnings'] += 1" in new_lines[idx-1]:
        final_lines.append("                actual_pmids_completed += 1\n")
        final_lines.append(line)
        continue

    final_lines.append(line)

final_lines.extend(lines[end_idx:])

with open('scripts/run_pipeline_fixed.py', 'w') as f:
    f.writelines(final_lines)

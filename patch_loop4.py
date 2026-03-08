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
    # Lines originally inside the loop (up to `continue`) have 12-16 spaces.
    # Lines originally outside the loop (from `print(f"[{pmid}] Processing...")`) have 8 spaces.

    current_indent = len(line) - len(line.lstrip(' '))

    if i < 978:
        # Keep original indentation
        new_lines.append(line)
    else:
        # Indent everything originally outside the loop by 4 spaces
        new_lines.append("    " + line)

# Update processed_in_phase behavior
for i in range(len(new_lines)):
    if new_lines[i].strip() == "processed_in_phase += 1":
        new_lines[i] = "            processed_in_phase += 1\n"

    if new_lines[i].strip() == "stats['processed'] += 1":
        new_lines[i] = "            actual_pmids_completed += 1\n"

    # the original early exit was:
    # if full_text_success_count >= target_full_text:
    #     print(...)
    #     break
    # we need to set why_phase_ended here
    if "Reached target of {target_full_text} full-text articles. Stopping processing." in new_lines[i]:
        new_lines.insert(i + 1, "                why_phase_ended = 'target reached'\n")
        break

# check the early `continue` in missing metadata:
# if not data:
#     print(f"[{pmid}] Warning: Could not fetch metadata.")
#     stats['nonfatal_warnings'] += 1
#     continue
for i in range(len(new_lines)):
    if new_lines[i].strip() == "continue" and "stats['nonfatal_warnings'] += 1" in new_lines[i-1]:
        # Insert actual_pmids_completed increment before the continue
        new_lines.insert(i, "                actual_pmids_completed += 1\n")
        break

new_lines.extend(lines[end_idx:])

with open('scripts/run_pipeline_fixed.py', 'w') as f:
    f.writelines(new_lines)

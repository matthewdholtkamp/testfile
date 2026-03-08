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

# The `for pmid in new_pmids:` is at indent 8. Everything inside should be at least 12.
new_lines.append("        actual_pmids_attempted = 0\n")
new_lines.append("        actual_pmids_completed = 0\n")
new_lines.append("        why_phase_ended = 'phase exhausted'\n")
new_lines.append("        for i, pmid in enumerate(new_pmids):\n")

for i in range(start_idx + 1, end_idx):
    line = lines[i]
    if line.strip() == "":
        new_lines.append(line)
        continue

    # Let's count current indentation
    current_indent = len(line) - len(line.lstrip(' '))

    # If the current line is indented at 8 spaces, it was mistakenly outdented. We push it to 12.
    # If it is 12 spaces, it's correct. Wait, if it was inside an `if` at 8 spaces, it would be 12.
    # Let's just blindly add 4 spaces to everything after line 978 (the first outdented line).

    if i >= 978:
        new_lines.append("    " + line)
    else:
        new_lines.append(line)

new_lines.extend(lines[end_idx:])

with open('scripts/run_pipeline_fixed.py', 'w') as f:
    f.writelines(new_lines)

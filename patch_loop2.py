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

for i in range(start_idx + 1, end_idx):
    line = lines[i]
    if line.strip() == "":
        new_lines.append(line)
        continue

    # We want to properly indent everything inside the loop.
    # Lines 968-977 were indented at 12 spaces (inside the for loop).
    # Line 978 (print(f"[{pmid}] Processing...")) dropped to 8 spaces (outside the for loop).
    # We want to re-indent everything from 968 to end_idx-1.

    # Let's just strip leading spaces and add 12 spaces, but we need to keep relative indentation.
    # The minimum indentation from line 978 onwards is 8 spaces.

    current_indent = len(line) - len(line.lstrip(' '))
    if current_indent >= 8:
        # if it's currently at 8 spaces (which is the block level of the `for` statement),
        # or inside the loop, we need to adjust.
        # Lines 968-977 are correctly 12 spaces.
        # Lines 978+ are 8 spaces but should be 12.

        if i >= 978:
            new_lines.append("    " + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

new_lines.extend(lines[end_idx:])

with open('scripts/run_pipeline_fixed.py', 'w') as f:
    f.writelines(new_lines)

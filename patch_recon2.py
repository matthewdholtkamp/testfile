import re

with open('scripts/run_pipeline.py', 'r') as f:
    lines = f.readlines()

# add total_attempted_across_phases tracking
start_idx = -1
for i, line in enumerate(lines):
    if "processed_pmids_in_run = set()" in line:
        start_idx = i
        break

lines.insert(start_idx + 1, "    total_attempted_across_phases = 0\n")

# add it to the phase loop
for i, line in enumerate(lines):
    if line.strip() == "print(f\"\\n--- Phase {phase_idx + 1} End Summary ---\")":
        lines.insert(i, "        total_attempted_across_phases += actual_pmids_attempted\n")
        break

# fix the global summary
for i, line in enumerate(lines):
    if "print(f\"Processed candidates: {stats['processed']}\")" in line:
        # replace the next 4 lines which we just added
        # they are at i+1 to i+4
        lines[i+1] = "    print(f\"Sum of actual_pmids_attempted across phases: {total_attempted_across_phases}\")\n"
        lines[i+2] = "    if stats['processed'] != total_attempted_across_phases:\n"
        lines[i+3] = "        print(\"\\n=======================================================\")\n"
        lines[i+4] = "        print(\"LOUD WARNING: stats['processed'] DOES NOT MATCH total actual attempted PMIDs!\")\n"
        lines.insert(i+5, "        print(\"=======================================================\\n\")\n")
        break

with open('scripts/run_pipeline.py', 'w') as f:
    f.writelines(lines)

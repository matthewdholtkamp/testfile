from pathlib import Path
import subprocess
import sys
import json


def test_build_xml_corpus(tmp_path: Path):
    inbox = tmp_path / "inbox"
    out = tmp_path / "xml_daily"
    inbox.mkdir()

    (inbox / "Paper One.md").write_text("Aging claim text", encoding="utf-8")
    (inbox / "record.json").write_text('{"x": 1}', encoding="utf-8")

    cmd = [
        sys.executable,
        "tools/build_xml_corpus.py",
        "--input",
        str(inbox),
        "--output",
        str(out),
        "--date",
        "2026-01-01",
    ]
    subprocess.run(cmd, check=True)

    day = out / "2026-01-01"
    assert (day / "paper-one.xml").exists()
    assert (day / "record.xml").exists()

    lines = (day / "manifest.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert "source" in row and "xml" in row and "chars" in row

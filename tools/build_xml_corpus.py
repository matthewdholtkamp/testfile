#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

SUPPORTED = {".txt", ".md", ".json", ".xml", ".csv"}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "document"


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)
    return path.read_text(encoding="utf-8", errors="replace")


def build_xml_record(path: Path, content: str) -> ET.Element:
    root = ET.Element(
        "document",
        {
            "source_name": path.name,
            "source_ext": path.suffix.lower().replace(".", "") or "none",
            "sha1": hashlib.sha1(content.encode("utf-8")).hexdigest(),
        },
    )
    title = ET.SubElement(root, "title")
    title.text = path.stem

    body = ET.SubElement(root, "body")
    body.text = content
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily XML corpus from flat inbox.")
    parser.add_argument("--input", default="data/inbox", help="Folder with source docs")
    parser.add_argument("--output", default="data/xml_daily", help="Base output folder")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Day folder (YYYY-MM-DD)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    day_dir = Path(args.output) / args.date
    day_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = day_dir / "manifest.jsonl"
    count = 0

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for src in sorted(input_dir.iterdir()):
            if not src.is_file() or src.suffix.lower() not in SUPPORTED:
                continue
            content = read_text(src)
            xml_root = build_xml_record(src, content)

            xml_name = f"{slugify(src.stem)}.xml"
            xml_path = day_dir / xml_name
            ET.ElementTree(xml_root).write(xml_path, encoding="utf-8", xml_declaration=True)

            row = {
                "source": str(src),
                "xml": str(xml_path),
                "chars": len(content),
            }
            manifest.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    print(f"Built {count} XML files in {day_dir}")


if __name__ == "__main__":
    main()

# themes_fabric_export.py
import os
import json
from pathlib import Path

EXPORT_DIR = Path("~/themes_fabric/exports").expanduser()
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_pattern_to_markdown(pattern: dict, filename: str):
    md_path = EXPORT_DIR / f"{filename}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {pattern.get('title', 'Untitled')}")
        f.write("\n\n")

        if pattern.get("tags"):
            tags = ", ".join(pattern["tags"])
            f.write(f"**Tags**: {tags}\n\n")

        if pattern.get("description"):
            f.write(f"## Description\n{pattern['description']}\n\n")

        if pattern.get("extract"):
            f.write(f"## Extract\n{pattern['extract']}\n\n")

        if pattern.get("metadata"):
            f.write("## Metadata\n")
            for k, v in pattern["metadata"].items():
                f.write(f"- **{k}**: {v}\n")

    print(f"Exported: {md_path}")


def batch_export_from_json(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        patterns = json.load(f)

    for key, pattern in patterns.items():
        export_pattern_to_markdown(pattern, key)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--json", type=str, required=True, help="Path to JSON file with patterns")
    args = parser.parse_args()

    batch_export_from_json(Path(args.json))


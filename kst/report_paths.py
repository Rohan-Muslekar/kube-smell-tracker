"""Remove machine-specific prefixes from rendered manifest paths in analyzer reports."""

import json
import sys
from pathlib import Path

RENDERED_PREFIX = "/work/rendered/"


def _normalize_field(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.startswith("/"):
        return False

    _, separator, suffix = value.rpartition(RENDERED_PREFIX)
    if not separator or not suffix:
        return False

    record[key] = f"work/rendered/{suffix}"
    return True


def normalize_report(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Leave invalid analyzer output for the existing validator to report.
        return

    changed = False
    if isinstance(data, dict):
        for report in data.get("Reports") or []:
            metadata = report.get("Object", {}).get("Metadata", {})
            changed |= _normalize_field(metadata, "FilePath")
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                changed |= _normalize_field(entry, "file_name")

    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        normalize_report(Path(filename))
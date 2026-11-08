"""Report probable object-pair transitions and invalid tags from a collected dataset."""
import argparse
import csv
import json
from pathlib import Path

from kst.__main__ import load_findings, load_objects, valid_versions
from kst.track import probable_renames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("raw"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()
    versions = valid_versions(args.data / "versions.csv")
    findings, _ = load_findings(args.raw, versions)
    candidates = probable_renames(findings, versions, load_objects(args.raw, versions))
    with (args.data / "versions.csv").open(newline="") as stream:
        invalid = [row for row in csv.DictReader(stream) if row["valid"] != "1"]
    print(json.dumps({"candidate_object_pair_transitions": len(candidates),
                      "invalid_tags": invalid, "candidates": candidates}, indent=2))


if __name__ == "__main__":
    main()

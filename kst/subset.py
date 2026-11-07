"""Copy data/ with versions.csv cut down to the tags listed under one field of repos.json.

Usage: python3 -m kst.subset --field tags_milestone2 --out /tmp/m2tags
       python3 -m kst --data /tmp/m2tags --out /tmp/m2tags/out

Lets the same raw output be analysed on fewer tags, e.g. the five Milestone 2 tags of a dense run,
so a change of input (rendering) can be compared without a change of sampling.
"""
import argparse
import csv
import json
import shutil
from pathlib import Path


def make_subset(data, field, out):
    data, out = Path(data), Path(out)
    shutil.copytree(data, out, dirs_exist_ok=True)
    keep = {r["name"]: set(r[field]) for r in json.loads((data / "repos.json").read_text())["included"]}
    with open(data / "versions.csv", newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r["tag"] in keep.get(r["repo"], ())]
        fields = reader.fieldnames
    with open(out / "versions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--field", required=True, help="tag list in repos.json, e.g. tags_milestone2")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    make_subset(args.data, args.field, args.out)
    print(f"{args.out}/versions.csv: tags from {args.field}")


if __name__ == "__main__":
    main()

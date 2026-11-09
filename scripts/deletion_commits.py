"""Find the commits behind the object deletions in out/instances.csv.

Usage: python3 scripts/deletion_commits.py [--work work]
Groups every removal whose object is gone (smells only, not `other`) by the pair of consecutive
tags it falls between, then lists the commits in `git log --diff-filter=D from..to` that delete
files under the system's manifest paths (data/repos.json), using the clones under work/.
"""
import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def deletion_steps(instances, tags):
    """Count the removals with the object gone per (repo, from_tag, to_tag)."""
    steps = Counter()
    for r in instances:
        if r["category"] == "other" or r["removed_object_gone"] == "0":
            continue
        p = r["presence"]
        for i in range(1, len(p)):
            if p[i - 1] == "1" and p[i] == "0":
                steps[(r["repo"], tags[r["repo"]][i - 1], tags[r["repo"]][i])] += 1
    return dict(steps)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=ROOT / "work")
    args = ap.parse_args(argv)
    tags = {}
    with open(ROOT / "data" / "versions.csv", newline="") as f:
        for v in csv.DictReader(f):
            if v["valid"] == "1":
                tags.setdefault(v["repo"], []).append(v["tag"])
    paths = {r["name"]: r["manifest_paths"] for r in json.loads((ROOT / "data" / "repos.json").read_text())["included"]}
    with open(ROOT / "out" / "instances.csv", newline="") as f:
        steps = deletion_steps(csv.DictReader(f), tags)
    for (repo, a, b), n in sorted(steps.items()):
        log = subprocess.run(["git", "-C", str(args.work / repo), "log", "--diff-filter=D",
                              "--format=%h %cs %s", f"{a}..{b}", "--", *paths[repo]],
                             capture_output=True, text=True, check=True).stdout.splitlines()
        print(f"{repo} {a}..{b}: {n} deletions, {len(log)} deleting commit(s)")
        for line in log:
            print(f"  {line}")
    print(f"{sum(steps.values())} deletions in {len(steps)} tag steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())

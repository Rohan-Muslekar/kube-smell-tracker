"""Check every traced transition in data/rq3_investigations.csv against the data and the clones.

Usage: python3 scripts/check_rq3.py [--work work]
For each fixed, introduced or object_deleted row: from_tag and to_tag must be consecutive study
tags, the instance's presence in out/instances.csv must change between them, and the traced
commit must be in `git log from_tag..to_tag` of the clone under work/. Prints one line per
problem and exits non-zero if there is any.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGE = {"fixed": ("1", "0"), "object_deleted": ("1", "0"), "introduced": ("0", "1")}


def step_problem(presence, tags, transition, from_tag, to_tag):
    """None if the transition happens exactly between the two consecutive tags, else why not."""
    i, j = tags.index(from_tag), tags.index(to_tag)
    if j != i + 1:
        return f"{from_tag}..{to_tag} is not consecutive"
    if (presence[i], presence[j]) != CHANGE[transition]:
        return f"no {transition} between {from_tag} and {to_tag}"
    return None


def in_range(clone, sha, from_tag, to_tag):
    def ancestor(a, b):
        return subprocess.run(["git", "-C", str(clone), "merge-base", "--is-ancestor", a, b],
                              capture_output=True).returncode == 0
    return ancestor(sha, to_tag) and not ancestor(sha, from_tag)


def check_rows(rows, presence, tags, commit_in_range):
    """Return (problems, absent) as lists of (csv line, text). `absent` holds rows whose
    instance is not in out/ at all, e.g. a stored-manifest patch fragment after rendering."""
    problems, absent = [], []
    for n, r in enumerate(rows, start=2):
        if r["transition"] not in CHANGE:
            continue
        key = (r["repo"], r["object_kind"], r["namespace"], r["object_name"], r["check"])
        label = f"{r['repo']} {r['object_name']} {r['check']}"
        if key not in presence:
            absent.append((n, label))
            continue
        why = step_problem(presence[key], tags[r["repo"]], r["transition"], r["from_tag"], r["to_tag"])
        sha = r["commit_url"].rstrip("/").split("/")[-1]
        if why is None and not commit_in_range(r["repo"], sha, r["from_tag"], r["to_tag"]):
            why = f"commit {sha[:9]} is not in {r['from_tag']}..{r['to_tag']}"
        if why:
            problems.append((n, f"{label}: {why}"))
    return problems, absent


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=ROOT / "work")
    args = ap.parse_args(argv)
    tags = {}
    with open(ROOT / "data" / "versions.csv", newline="") as f:
        for v in csv.DictReader(f):
            if v["valid"] == "1":
                tags.setdefault(v["repo"], []).append(v["tag"])
    with open(ROOT / "out" / "instances.csv", newline="") as f:
        presence = {(r["repo"], r["kind"], r["namespace"], r["name"], r["check"]): r["presence"]
                    for r in csv.DictReader(f)}
    with open(ROOT / "data" / "rq3_investigations.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    problems, absent = check_rows(rows, presence, tags,
                                  lambda repo, *rest: in_range(args.work / repo, *rest))
    for n, why in problems:
        print(f"line {n}: {why}")
    for n, why in absent:
        print(f"line {n}: {why} (not in out/; a stored-manifest object rendering removes?)")
    checked = sum(r["transition"] in CHANGE for r in rows)
    print(f"{checked} transitions checked, {len(problems)} problems, {len(absent)} not in this out/")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

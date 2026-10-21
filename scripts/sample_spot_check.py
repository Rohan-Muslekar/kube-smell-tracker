#!/usr/bin/env python3
"""Draw the manual spot-check sample from out/instances.csv (fixed seed, so reruns draw the same rows).

Strata (5 each, smell categories only): persisted, fixed (removed while the object stays),
object deleted (removed with its object), introduced. Writes data/spot_check.csv with empty
verdict columns that the reviewer fills in by reading the YAML at both tags. It refuses to
overwrite an existing file, so recorded verdicts are never lost.
"""
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kst.__main__ import valid_versions  # noqa: E402

PER_STRATUM = 5
SEED = 5570


def first_step(presence, want):
    """Index of the first (prev, cur) step matching want: 'persisted', 'removed' or 'introduced'."""
    for i in range(1, len(presence)):
        prev, cur = presence[i - 1] == "1", presence[i] == "1"
        if (want == "persisted" and prev and cur) or (want == "removed" and prev and not cur) \
                or (want == "introduced" and cur and not prev):
            return i
    return None


def main():
    target = ROOT / "data/spot_check.csv"
    if target.exists():
        sys.exit(f"{target} exists (it holds manual verdicts); delete it first to draw a new sample")
    rows = [r for r in csv.DictReader(open(ROOT / "out/instances.csv")) if r["category"] != "other"]
    strata = {
        "persisted": [r for r in rows if r["presence"] == "1" * len(r["presence"])],
        "fixed": [r for r in rows if int(r["removed"]) > int(r["removed_object_gone"])],
        "object deleted": [r for r in rows if int(r["removed_object_gone"]) > 0],
        "introduced": [r for r in rows if int(r["introduced"]) > 0],
    }
    versions = valid_versions(ROOT / "data/versions.csv")
    rng = random.Random(SEED)
    out = []
    for stratum, pool in strata.items():
        step = {"persisted": "persisted", "fixed": "removed", "object deleted": "removed",
                "introduced": "introduced"}[stratum]
        for r in rng.sample(pool, min(PER_STRATUM, len(pool))):
            i = first_step(r["presence"], step)
            tags = versions[r["repo"]]
            out.append({"stratum": stratum, "repo": r["repo"], "tool": r["tool"], "check": r["check"],
                        "category": r["category"], "kind": r["kind"], "namespace": r["namespace"],
                        "name": r["name"], "presence": r["presence"], "from_tag": tags[i - 1], "to_tag": tags[i],
                        "confirmed": "", "cause": "", "note": ""})
    with open(target, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} rows -> {target}")


if __name__ == "__main__":
    main()

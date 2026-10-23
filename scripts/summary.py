#!/usr/bin/env python3
"""Print the headline numbers of the study from out/ (run `python3 -m kst` first).

Smell categories only ("other" is left out). Counts are per tool unless the line says merged.
kube-score's pod-probes-identical removals are reported apart from fixes: kube-score stops
comparing probes once they use grpc, so those removals are not fixes (see data/spot_check.csv).
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_CHECKS = {("kube-score", "pod-probes-identical")}


def rows(path):
    with open(ROOT / path, newline="") as f:
        return list(csv.DictReader(f))


def pct(a, b):
    return f"{100 * a / b:.1f}%"


def main():
    smell = [r for r in rows("out/instances.csv") if r["category"] != "other"]
    total = lambda k: sum(int(r[k]) for r in smell)
    merged = {(r["repo"], r["kind"], r["namespace"], r["name"], r["category"]) for r in smell}
    base = [r for r in smell if r["presence"][0] == "1"]
    survivors = [r for r in base if r["presence"][-1] == "1"]
    removed, gone = total("removed"), total("removed_object_gone")
    artifacts = sum(int(r["removed"]) - int(r["removed_object_gone"]) for r in smell
                    if (r["tool"], r["check"]) in ARTIFACT_CHECKS)

    print(f"smell instances      {len(smell)}  ({len(merged)} merged object-category pairs)")
    for tool in ("kube-linter", "kube-score"):
        b = [r for r in base if r["tool"] == tool]
        s = [r for r in b if r["presence"][-1] == "1"]
        n = sum(1 for r in smell if r["tool"] == tool)
        print(f"  {tool:<18} {n} instances, {len(s)}/{len(b)} baseline survive ({pct(len(s), len(b))})")
    print(f"baseline survivors   {len(survivors)}/{len(base)} ({pct(len(survivors), len(base))})")
    print(f"removed              {removed}, of which object deleted {gone} ({pct(gone, removed)})")
    print(f"fixes (object kept)  {removed - gone}, of which probe artifacts {artifacts}, "
          f"real fixes {removed - gone - artifacts}")
    print(f"introduced           {total('introduced')}, with a new object {total('introduced_new_object')}")
    print(f"reappeared           {total('reappeared')}")

    overlap = rows("out/overlap_summary.csv")
    for label, part in (("all categories", overlap),
                        ("without hygiene", [o for o in overlap if o["category"] != "hygiene"])):
        both = sum(int(o["both"]) for o in part)
        flagged = sum(int(o["both"]) + int(o["linter_only"]) + int(o["score_only"]) for o in part)
        print(f"tools agree          {both}/{flagged} pairs ({pct(both, flagged)}), {label}")

    print("instances by category")
    for tool in ("kube-linter", "kube-score"):
        counts = Counter(r["category"] for r in smell if r["tool"] == tool)
        print(f"  {tool:<18} " + ", ".join(f"{c} {n}" for c, n in counts.most_common()))


if __name__ == "__main__":
    main()

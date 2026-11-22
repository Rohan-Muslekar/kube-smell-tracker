#!/usr/bin/env python3
"""Compare stored and rendered Kubernetes smell results per system.

Run from the directory where results/render_comparison.csv should be written.
Object-version observations sum distinct (kind, namespace, name) identities
per inventory tag.
Survival is first-tag instances still present at the final tag. Percentages are
blank when their denominator is zero. Missing systems have blank metrics.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

from summary import ARTIFACT_CHECKS

METRICS = (
    "object_version_observations", "instances", "baseline", "survivors", "survival_pct",
    "removals", "deletions", "deletion_pct", "real_fixes", "reappearances",
)


def percentage(count, total):
    return round(100 * count / total, 1) if total else ""


def summarize(root):
    inventories = root / "raw" / "objects"
    if not inventories.is_dir():
        raise FileNotFoundError(inventories)

    counts = {}
    for path in inventories.glob("*__*.tsv"):
        repo, _ = path.stem.split("__", 1)
        with path.open(encoding="utf-8") as stream:
            identities = {tuple(line.rstrip("\n").split("\t")[:3]) for line in stream}
        counts.setdefault(repo, Counter())["object_version_observations"] += len(identities)

    with (root / "out" / "instances.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            system = counts.setdefault(row["repo"], Counter())
            if row["category"] == "other":
                continue
            removed = int(row["removed"])
            deleted = int(row["removed_object_gone"])
            presence = row["presence"]
            system["instances"] += 1
            system["baseline"] += presence.startswith("1")
            system["survivors"] += presence.startswith("1") and presence.endswith("1")
            system["removals"] += removed
            system["deletions"] += deleted
            system["reappearances"] += int(row["reappeared"])
            if (row["tool"], row["check"]) not in ARTIFACT_CHECKS:
                system["real_fixes"] += removed - deleted

    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stored", type=Path, required=True)
    parser.add_argument("--rendered", type=Path, required=True)
    args = parser.parse_args()

    try:
        stored = summarize(args.stored)
        rendered = summarize(args.rendered)
    except (OSError, KeyError, ValueError) as exc:
        parser.error(str(exc))

    output = Path("results/render_comparison.csv")
    output.parent.mkdir(exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("system", "source", *METRICS))
        print("\t".join(("system", "source", *METRICS)))
        for repo in sorted(stored.keys() | rendered.keys()):
            for source, systems in (("stored", stored), ("rendered", rendered)):
                system = systems.get(repo)
                if system is None:
                    values = [""] * len(METRICS)
                else:
                    system["survival_pct"] = percentage(system["survivors"], system["baseline"])
                    system["deletion_pct"] = percentage(system["deletions"], system["removals"])
                    values = [system[metric] for metric in METRICS]
                row = (repo, source, *values)
                writer.writerow(row)
                print("\t".join(map(str, row)))


if __name__ == "__main__":
    main()

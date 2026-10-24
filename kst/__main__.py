"""Build every table in out/ from raw analyzer output.

Usage: python3 -m kst [--raw raw] [--data data] [--out out]
Exits non-zero when an analyzer check has no category in data/check_categories.csv.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from kst.normalize import Finding, categorize, load_categories, parse_kube_linter, parse_kube_score
from kst.overlap import overlap, overlap_summary
from kst.track import LABELS, track

COUNTS = ("at_baseline", *LABELS, "removed_object_gone", "introduced_new_object")

PARSERS = {"kube-linter": parse_kube_linter, "kube-score": parse_kube_score}


def finding_order(f):
    return (f.repo, f.version, f.tool, f.kind, f.namespace, f.name, f.check, f.file)


def valid_versions(path):
    """repo -> valid tags in collection order (oldest first, as listed in repos.json)."""
    versions = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["valid"] == "1":
                versions[row["repo"]].append(row["tag"])
    return dict(versions)


def load_findings(raw, versions):
    findings, scored_kinds = [], set()
    for repo, tags in versions.items():
        for tag in tags:
            for tool, parse in PARSERS.items():
                data = json.loads((raw / tool / f"{repo}__{tag}.json").read_text())
                findings.extend(parse(data, repo, tag))
                if tool == "kube-score":
                    scored_kinds.update(obj["type_meta"]["kind"] for obj in data or [])
    return findings, scored_kinds


def load_objects(raw, versions):
    """(repo, tag) -> set of (kind, namespace, name) from raw/objects/<repo>__<tag>.tsv."""
    objects = {}
    for repo, tags in versions.items():
        for tag in tags:
            with open(raw / "objects" / f"{repo}__{tag}.tsv") as f:
                objects[(repo, tag)] = {tuple(line.rstrip("\n").split("\t")[:3]) for line in f}
    return objects


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def summarize(instances, by):
    totals = defaultdict(Counter)
    for r in instances:
        totals[tuple(r[k] for k in by)].update({k: r[k] for k in COUNTS})
    return [dict(zip(by, key), **{k: c[k] for k in COUNTS})
            for key, c in sorted(totals.items())]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="out")
    args = ap.parse_args(argv)
    raw, data, out = Path(args.raw), Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    versions = valid_versions(data / "versions.csv")
    findings, scored_kinds = load_findings(raw, versions)
    findings, unmapped = categorize(findings, load_categories(data / "check_categories.csv"))
    (out / "unmapped_checks.txt").write_text("".join(f"{t},{c}\n" for t, c in sorted(unmapped)))

    dups = Counter(findings)
    fields = list(Finding.__dataclass_fields__)
    write_csv(out / "findings.csv",
              [dict(asdict(f), dup_count=dups[f]) for f in sorted(dups, key=finding_order)],
              fields + ["dup_count"])

    instances = track(findings, versions, load_objects(raw, versions))
    write_csv(out / "instances.csv", instances, list(instances[0]) if instances else [])

    prevalence = defaultdict(lambda: [0, set()])
    for f in findings:
        p = prevalence[(f.repo, f.version, f.tool, f.category)]
        p[0] += 1
        p[1].add((f.kind, f.namespace, f.name, f.check))
    write_csv(out / "prevalence.csv",
              [{"repo": k[0], "version": k[1], "tool": k[2], "category": k[3], "findings": n, "instances": len(s)}
               for k, (n, s) in sorted(prevalence.items())],
              ["repo", "version", "tool", "category", "findings", "instances"])

    label_fields = list(COUNTS)
    write_csv(out / "transitions_summary.csv", summarize(instances, ("tool", "category")),
              ["tool", "category", *label_fields])
    write_csv(out / "transitions_by_repo.csv", summarize(instances, ("repo", "tool", "category")),
              ["repo", "tool", "category", *label_fields])

    write_csv(out / "overlap_summary.csv", overlap_summary(overlap(findings, kinds=scored_kinds)),
              ["category", "linter_only", "score_only", "both"])

    if unmapped:
        print(f"{len(unmapped)} unmapped checks; see {out / 'unmapped_checks.txt'}", file=sys.stderr)
        return 1
    print(f"{len(findings)} findings, {len(instances)} instances, {sum(len(v) for v in versions.values())} versions -> {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

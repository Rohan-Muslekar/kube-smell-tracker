"""Kaplan-Meier time to first observed removal, using only the standard library."""
import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

FIELDS = ["group", "time_days", "at_risk", "events", "censored", "survival"]


def kaplan_meier(observations):
    """(duration_days, event) observations; events precede censoring at tied times."""
    counts = defaultdict(Counter)
    for duration, event in observations:
        if duration < 0:
            raise ValueError("Negative follow-up duration")
        counts[duration]["events" if event else "censored"] += 1
    risk = sum(sum(c.values()) for c in counts.values())
    survival, points = 1.0, []
    for duration, c in sorted(counts.items()):
        survival *= 1 - c["events"] / risk
        points.append(dict(time_days=duration, at_risk=risk, events=c["events"],
                           censored=c["censored"], survival=survival))
        risk -= c["events"] + c["censored"]
    return points


# Removals that are not fixes when event="fix": kube-score's gRPC-probe artifact (the same set
# as ARTIFACT_CHECKS in scripts/summary.py) and removals where the object itself was deleted.
ARTIFACT_CHECKS = {("kube-score", "pod-probes-identical")}


def is_fix(row):
    """True if the instance's removal left its object in place and is not a known artifact."""
    if (row.get("tool"), row.get("check")) in ARTIFACT_CHECKS:
        return False
    return int(row.get("removed_object_gone") or 0) < int(row.get("removed") or 0)


def curves(instances, dates, group, event="removal"):
    """event="removal": any first removal is the event. event="fix": a deletion or an
    analyzer artifact is censored at the tag where the smell disappears instead."""
    if event not in ("removal", "fix"):
        raise ValueError(f"Unknown event type: {event}")
    observations = defaultdict(list)
    for row in instances:
        if row["category"] == "other":
            continue
        history, days = row["presence"], dates[row["repo"]]
        if len(history) != len(days) or "1" not in history or set(history) - {"0", "1"}:
            raise ValueError(f"Invalid presence/date alignment for {row['repo']}")
        if any(a > b for a, b in zip(days, days[1:])):
            raise ValueError(f"Nonchronological dates for {row['repo']}")
        first = history.index("1")
        removed = history.find("0", first)
        end = removed if removed != -1 else len(history) - 1
        happened = removed != -1 and (event == "removal" or is_fix(row))
        observations[row[group]].append(((days[end] - days[first]).days, happened))
    return [dict(group=name, **point) for name, obs in sorted(observations.items())
            for point in kaplan_meier(obs)]


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_curves(instances, data, out):
    """Use minor release dates (not late patch dates), aligned to valid tags only."""
    minor = {(r["repo"], r["tag"]): date.fromisoformat(r["minor_first_date"])
             for r in read_csv(Path(data) / "minor_dates.csv")}
    dates = defaultdict(list)
    for row in read_csv(Path(data) / "versions.csv"):
        if row["valid"] == "1":
            dates[row["repo"]].append(minor[(row["repo"], row["tag"])])
    for field, event, filename in (("category", "removal", "km_by_category.csv"),
                                   ("repo", "removal", "km_by_system.csv"),
                                   ("category", "fix", "km_fix_by_category.csv"),
                                   ("repo", "fix", "km_fix_by_system.csv")):
        points = curves(instances, dates, field, event)
        with (Path(out) / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(points)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()
    write_curves(read_csv(args.out / "instances.csv"), args.data, args.out)


if __name__ == "__main__":
    main()

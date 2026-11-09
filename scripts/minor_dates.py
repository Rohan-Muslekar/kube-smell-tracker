"""Date each sampled tag by the first release of its minor (its x.y.0 tag).

Usage: python3 scripts/minor_dates.py [--work work] [--out data/minor_dates.csv]
Reads data/versions.csv and the clones under work/. A study tag is the latest patch of its
minor, so its own commit date can be years after the minor shipped (microservices-demo
v0.10.7 is dated 2026-09-18, v0.10.0 2024-04-23). Ages and the survival figure use the
x.y.0 date instead, which also keeps the tags of a repo in time order.
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kst.select_tags import minor_zero, tag_dates  # noqa: E402

FIELDS = ["repo", "tag", "minor_first_tag", "minor_first_date"]


def rows(versions, dates):
    """One row per version; `dates` maps repo -> {tag: commit date}."""
    out = []
    for v in versions:
        first = minor_zero(v["tag"])
        if first not in dates[v["repo"]]:
            raise ValueError(f"{v['repo']}: no {first} tag for {v['tag']}")
        out.append({"repo": v["repo"], "tag": v["tag"], "minor_first_tag": first,
                    "minor_first_date": dates[v["repo"]][first]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=ROOT / "work")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "minor_dates.csv")
    args = ap.parse_args(argv)
    with open(ROOT / "data" / "versions.csv", newline="") as f:
        versions = [v for v in csv.DictReader(f) if v["valid"] == "1"]
    dates = {repo: tag_dates(str(args.work / repo)) for repo in {v["repo"] for v in versions}}
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows(versions, dates))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

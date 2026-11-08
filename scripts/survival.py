"""Survival figure: share of each system's first-tag smell instances still present at every later tag.

Usage: python3 scripts/survival.py [--out results]
Reads out/instances.csv, data/versions.csv and data/repos.json. Writes survival.csv always and
survival.pdf (one IEEE column wide, x axis = the tag's commit date) when matplotlib is installed.
Smells in the `other` category are left out, as in the rest of the analysis.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def series(instances, tags):
    """repo -> [(tag index, % of first-tag instances present at that tag)], for repos with any."""
    out = {}
    for repo, repo_tags in tags.items():
        first = [r["presence"] for r in instances
                 if r["repo"] == repo and r["category"] != "other" and r["presence"][0] == "1"]
        if first:
            out[repo] = [(i, 100 * sum(p[i] == "1" for p in first) / len(first)) for i in range(len(repo_tags))]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    args = ap.parse_args(argv)

    with open(ROOT / "data" / "versions.csv", newline="") as f:
        versions = [v for v in csv.DictReader(f) if v["valid"] == "1"]
    tags = {}
    for v in versions:
        tags.setdefault(v["repo"], []).append(v["tag"])
    when = {(v["repo"], v["tag"]): v["commit_date"] for v in versions}
    with open(ROOT / "out" / "instances.csv", newline="") as f:
        data = series(list(csv.DictReader(f)), tags)
    order = [r["name"] for r in json.loads((ROOT / "data" / "repos.json").read_text())["included"]]

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "survival.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["repo", "tag", "commit_date", "percent_present"])
        for repo in order:
            for i, share in data.get(repo, []):
                tag = tags[repo][i]
                w.writerow([repo, tag, when[(repo, tag)], f"{share:.1f}"])

    try:
        import matplotlib
    except ImportError:
        print(f"wrote {args.out / 'survival.csv'} (matplotlib not installed, no PDF)")
        return
    matplotlib.use("pdf")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 7, "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(3.45, 2.0))
    with open(ROOT / "out" / "instances.csv", newline="") as f:
        n_first = {}
        for r in csv.DictReader(f):
            if r["category"] != "other" and r["presence"][0] == "1":
                n_first[r["repo"]] = n_first.get(r["repo"], 0) + 1
    styles = ["-", "--", "-.", ":"]
    for k, repo in enumerate(r for r in order if r in data):
        xs = [date.fromisoformat(when[(repo, tags[repo][i])]) for i, _ in data[repo]]
        ax.plot(xs, [s for _, s in data[repo]], styles[k % 4], marker="o", markersize=1.8, linewidth=1,
                label=f"{repo} ({n_first[repo]})")
    ax.set_ylabel("First-tag instances present (%)")
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(alpha=0.3, linewidth=0.4)
    ax.legend(fontsize=5.5, ncol=2, frameon=False, loc="lower left")
    fig.tight_layout(pad=0.3)
    fig.savefig(args.out / "survival.pdf")
    print(f"wrote {args.out / 'survival.csv'} and {args.out / 'survival.pdf'}")


if __name__ == "__main__":
    main()

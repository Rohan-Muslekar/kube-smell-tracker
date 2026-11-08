"""Pick each repo's study tags from its minor releases.

Usage:
  python3 -m kst.select_tags CLONE SINCE
      latest patch of 5 minor releases evenly spaced over the window (Milestone 2)
  python3 -m kst.select_tags CLONE SINCE --all --until DATE [--keep TAG ...]
      latest patch of every minor in the window, ignoring tags dated after DATE;
      a --keep tag replaces the latest patch of its minor

SINCE and DATE are YYYY-MM-DD; a minor counts when its x.y.0 is on or after SINCE.
Prints the chosen tags in version order, one per line.
"""
import argparse
import re
import subprocess

SEMVER = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
COUNT = 5


def latest_patch_per_minor(tags):
    best = {}
    for tag in tags:
        m = SEMVER.fullmatch(tag)
        if not m:
            continue
        major, minor, patch = map(int, m.groups())
        if (major, minor) not in best or patch > best[(major, minor)][0]:
            best[(major, minor)] = (patch, tag)
    return {k: tag for k, (_, tag) in sorted(best.items())}


def evenly_spaced(items, count):
    if len(items) <= count:
        return list(items)
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)]


def dense_tags(dates, since, until, keep=()):
    """Latest patch of every minor whose x.y.0 is dated in [since, until], in version order.

    `dates` maps tag -> commit date (YYYY-MM-DD). Tags dated after `until` are ignored, so the
    result does not change when a project publishes new patches. A tag in `keep` is used for its
    minor instead of the latest patch; every kept tag must end up in the result.
    """
    usable = [t for t, d in dates.items() if d <= until]
    minors = latest_patch_per_minor(usable)
    for tag in keep:
        m = SEMVER.fullmatch(tag)
        if m:
            minors[(int(m.group(1)), int(m.group(2)))] = tag
    chosen = []
    for (major, minor), tag in sorted(minors.items()):
        zero = next((t for t in usable if SEMVER.fullmatch(t)
                     and SEMVER.fullmatch(t).groups() == (str(major), str(minor), "0")), None)
        if zero is not None and dates[zero] >= since:
            chosen.append(tag)
    missing = [t for t in keep if t not in chosen]
    if missing:
        raise ValueError(f"kept tags outside the window: {', '.join(missing)}")
    return chosen


def tag_dates(clone):
    """Commit date of every tag (dereferencing annotated tags)."""
    out = _git(clone, "for-each-ref", "refs/tags",
               "--format=%(refname:short) %(*committerdate:short)%(committerdate:short)")
    return dict(line.split() for line in out.splitlines() if len(line.split()) == 2)


def _git(clone, *args):
    return subprocess.run(["git", "-C", clone, *args], capture_output=True, text=True, check=True).stdout


def main(clone, since):
    tags = _git(clone, "tag").split()
    minors = latest_patch_per_minor(tags)
    first = {}
    for tag in tags:
        m = SEMVER.fullmatch(tag)
        if m and m.group(3) == "0":
            first[(int(m.group(1)), int(m.group(2)))] = tag
    recent = [minors[k] for k in minors
              if k in first and _git(clone, "log", "-1", "--format=%cs", first[k]).strip() >= since]
    for tag in evenly_spaced(recent, COUNT):
        print(tag)


def cli(argv=None):
    ap = argparse.ArgumentParser(description="Select a repo's study tags.")
    ap.add_argument("clone")
    ap.add_argument("since")
    ap.add_argument("--all", action="store_true", help="every minor in the window (dense mode)")
    ap.add_argument("--until", help="ignore tags dated after this day (required with --all)")
    ap.add_argument("--keep", nargs="*", default=[], help="tags to keep for their minor")
    args = ap.parse_args(argv)
    if not args.all:
        return main(args.clone, args.since)
    if not args.until:
        ap.error("--all needs --until, so the tag list does not move with new releases")
    for tag in dense_tags(tag_dates(args.clone), args.since, args.until, args.keep):
        print(tag)


if __name__ == "__main__":
    cli()

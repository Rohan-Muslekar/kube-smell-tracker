"""Pick each repo's study tags: the latest patch of 5 minor releases evenly spaced over a window.

Usage: python3 -m kst.select_tags CLONE SINCE   (SINCE = YYYY-MM-DD; a minor counts when its x.y.0 is on or after it)
Prints the chosen tags, oldest first, one per line.
"""
import re
import subprocess
import sys

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


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

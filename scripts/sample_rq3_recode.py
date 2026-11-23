"""Create a blinded, stratified RQ3 recoding sheet from the first coder's CSV.

The first coder's classification is used only for allocating the sample; it is
never written to the output. Run before inspecting the source coding labels.
"""

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

SEED = 5570
N = 20
MIN_PER_CLASS = 2
CLASSES = (
    "real_fix",
    "side_effect_of_fix",
    "analyzer_artifact",
    "new_object",
    "object_deleted",
)
KEY_FIELDS = (
    "repo", "object_kind", "namespace", "object_name", "check",
    "from_tag", "to_tag", "transition",
)
OUTPUT_FIELDS = (*KEY_FIELDS, "commit_url", "classification")


def _key(row):
    return tuple((row.get(field) or "").strip() for field in KEY_FIELDS)


def _allocation(groups, sample_size, minimum):
    """Largest-remainder allocation above a guaranteed per-class minimum."""
    if sample_size < minimum * len(CLASSES):
        raise ValueError("Sample size is too small for the per-class minimum")
    if sum(map(len, groups.values())) < sample_size:
        raise ValueError("Not enough eligible rows for the requested sample")
    if any(len(groups[cl]) < minimum for cl in CLASSES):
        missing = [cl for cl in CLASSES if len(groups[cl]) < minimum]
        raise ValueError(f"Fewer than {minimum} examples for: {', '.join(missing)}")

    allocation = {cl: minimum for cl in CLASSES}
    extras = sample_size - minimum * len(CLASSES)
    available = {cl: len(groups[cl]) - minimum for cl in CLASSES}
    total_available = sum(available.values())
    if extras:
        quotas = {cl: extras * available[cl] / total_available for cl in CLASSES}
        for cl in CLASSES:
            allocation[cl] += int(quotas[cl])
        remaining = sample_size - sum(allocation.values())
        ranked = sorted(CLASSES, key=lambda cl: (-(quotas[cl] % 1), CLASSES.index(cl)))
        for cl in ranked[:remaining]:
            allocation[cl] += 1
    return allocation


def make_sample(source: Path, destination: Path, seed=SEED, size=N):
    with source.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = set((*KEY_FIELDS, "commit_url", "classification"))
        if not reader.fieldnames or required - set(reader.fieldnames):
            raise ValueError(f"Missing source columns: {sorted(required - set(reader.fieldnames or []))}")
        rows = list(reader)

    groups = defaultdict(list)
    seen = set()
    for row in rows:
        label = (row["classification"] or "").strip()
        if label not in CLASSES:
            continue  # e.g. persisting_smell is not one of the five recode classes
        key = _key(row)
        if not all(key[i] for i in (0, 1, 3, 4, 5, 6, 7)):
            raise ValueError(f"Incomplete row identity: {key}")
        if key in seen:
            raise ValueError(f"Duplicate eligible row identity: {key}")
        seen.add(key)
        groups[label].append(row)

    allocation = _allocation(groups, size, MIN_PER_CLASS)
    rng = random.Random(seed)
    selected = []
    for cl in CLASSES:
        # Sorting protects reproducibility if source CSV rows are reordered.
        selected.extend(rng.sample(sorted(groups[cl], key=_key), allocation[cl]))
    rng.shuffle(selected)  # Do not reveal or cluster the source strata.

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in selected:
            writer.writerow({field: (row.get(field) or "") if field != "classification" else ""
                             for field in OUTPUT_FIELDS})
    return len(selected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/rq3_investigations.csv"))
    parser.add_argument("--out", type=Path, default=Path("data/rq3_recode_sheet.csv"))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--size", type=int, default=N)
    args = parser.parse_args(argv)
    count = make_sample(args.input, args.out, args.seed, args.size)
    print(f"Wrote {count} blinded rows to {args.out}; no original labels or notes copied.")


if __name__ == "__main__":
    main()

# Lifecycle tracking validation

Contributor: Yasaminzahra Valitabar.

## Current baseline

First validated on Windows with Python 3.11 and pytest 9.1.1 (74 passed, 2 skipped).
Rerun after the review fixes on Linux with Python 3.14.8 and pytest 9.1.1, from the
repository root, with the same `python3` for every step:

```bash
python3 -m pytest -q -rs
rm -rf /tmp/kst-baseline && python3 -m kst --out /tmp/kst-baseline
diff -r out /tmp/kst-baseline && echo identical
awk -F, 'NR>1 && $6==1' data/versions.csv | wc -l
python3 -c "import csv; s=[r for r in csv.DictReader(open('out/instances.csv')) if r['category']!='other']; rm=sum(int(r['removed']) for r in s); gone=sum(int(r['removed_object_gone']) for r in s); print(len(s), rm, gone, rm-gone)"
```

- `pytest`: 81 passed; the two analyzer-wrapper integration tests in
  `tests/test_analyze.py` skip ("analyzers not built; run ./tools/install.sh").
  Full collection was not run.
- `kst` prints `19346 findings, 1340 instances, 35 versions`, and `diff -r` finds no
  difference between the regenerated files and the committed `out/`.
- The `awk` line prints 35 valid versions. The last command prints `862 147 108 39`:
  862 non-`other` smell instances, 147 removals, 108 of them object deletions and
  39 candidate fixes.
- No production tracking algorithm changes were necessary for the added cases. The
  review fixes added an up-front inventory check to `track()`, which does not change
  any output.
- An independent code/deliverable review reproduced the test result and found no
  blocker in the completed work. Its terminology correction (candidate fixes)
  was applied.

Run the two integration tests in the team's Linux environment after `./tools/install.sh`.

## Pending evidence

Actual denser-tag and rendered-manifest validation is pending those input updates.
The current tests exercise synthetic denser histories and rendered-style file
movement only. Follow `docs/tracking_limitations.md` when new data arrives and
record the input commit, rendering settings, changed counts and manual examples here.

Independent human category ratings have not been collected. No study agreement
coefficient or adjudicated decisions are claimed. Follow `docs/category_validation.md`
to complete that work and preserve the original independent ratings.

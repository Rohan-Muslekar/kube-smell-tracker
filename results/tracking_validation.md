# Lifecycle tracking validation

Contributor: Yasaminzahra Valitabar.

## Current baseline

Local validation on Windows with Python 3.11 and pytest 9.1.1:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs
python -m kst --out C:\Users\yasam\AppData\Local\Temp\opencode\lifecycle-tracking-results
```

- 74 tests passed; two analyzer-wrapper integration tests were skipped because
  the pinned analyzer binaries were not installed. Full collection was not run.
- All regenerated baseline files matched the committed `out/` byte for byte.
- 35 valid versions; 862 non-`other` smell instances.
- 147 removals, including 108 object deletions and 39 candidate fixes.
- No production tracking algorithm changes were necessary for the added cases.
- An independent code/deliverable review reproduced the test result and found no
  blocker in the completed work. Its terminology correction (candidate fixes)
  was applied.

The isolated `.venv/` is retained locally for rerunning tests and ignored by Git.
Temporary generated baseline outputs are outside the repository. Run the two
integration tests in the team's Linux environment after `./tools/install.sh`.

## Pending evidence

Actual denser-tag and rendered-manifest validation is pending those input updates.
The current tests exercise synthetic denser histories and rendered-style file
movement only. Follow `docs/tracking_limitations.md` when new data arrives and
record the input commit, rendering settings, changed counts and manual examples here.

Independent human category ratings have not been collected. No study agreement
coefficient or adjudicated decisions are claimed. Follow `docs/category_validation.md`
to complete that work and preserve the original independent ratings.

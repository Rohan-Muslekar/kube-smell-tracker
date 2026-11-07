# Rename detection result note

PR: https://github.com/Rohan-Muslekar/kube-smell-tracker/pull/12

Scope: Milestone 2 baseline on master `fc84c26`, not the pending dense/rendered run.

Commands:

```bash
python -m pytest -q -rs
python -m kst.rename_report
python -m kst --out <temporary-output-directory>
```

Results: 90 tests passed, two analyzer integration tests skipped (binaries not
installed). The baseline has 35 valid tags and zero invalid tags. The heuristic
finds 21 candidate object-pair transitions, flagging 18 distinct instance rows.
All matches use only kube-linter's `sorted-keys` check (`other`); zero non-`other`
smell rows are flagged. These are not 21 confirmed renames.

Example: Tekton `pipeline`, v0.52.1 to v0.63.0, ConfigMap
`tekton-pipelines/config-leader-election` to
`tekton-pipelines/config-leader-election-controller`. Both have only `sorted-keys`.
Several other new ConfigMaps share that signature, so the match is ambiguous and
needs commit/YAML investigation with Bayan.

All existing instance columns are unchanged; every other output file matches the
baseline byte for byte. Only `probable_rename` is added. No generated `raw/`, `out/`
or `data/versions.csv` changes are included in this code contribution. Consequently
the existing CI output comparison requires integration regeneration of instances.csv.

Contribution: added inventory-backed probable-rename detection without merging
histories; tested positive/negative cases, exact check sets, ambiguity, absent
inventories and a 46-tag history. Added a reproducible candidate/invalid-tag report
and documented the heuristic's limitations.

Pending: rerun these commands after integration, inspect the dense instances output,
and replace baseline counts with dense-data counts and manually checked examples
before the numbers freeze.

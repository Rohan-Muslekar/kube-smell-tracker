# Lifecycle tracking review

Task owner: Yasaminzahra Valitabar.

## Review and verification

`kst/track.py` identifies instances by `(repo, tool, kind, namespace, name, check)`.
It ignores findings from tags outside the supplied valid-tag list, collapses
duplicate instance reports within each tag, and follows the supplied tag order.
File moves do not create new identities. Initial presence is baseline, not an
introduction. A return after a prior presence is a reappearance.

The existing transition logic passed the added regression tests; no production
tracking change was needed. `tests/test_track.py` now additionally covers every
identity field, repeated removals/reappearances, duplicate reports across tags,
rendered-style file moves, supplied tag ordering, missing inventory, empty inputs,
and a synthetic denser history exposing transitions hidden by sparse sampling.

On the committed baseline, regenerated analysis files matched `out/` byte for byte:
862 non-`other` instances, 147 removals and 108 object-deletion removals. The other
39 removals are candidate fixes, not automatically verified fixes. The existing
manual review identified nine analyzer artifacts, leaving the report's 30 fixes.
The full analysis also contains `other` instances; its 1,340 total must not be
mistaken for the 862 smell instances.

## Remaining limitations

- Sampled endpoints hide changes between tags. Zero observed reappearances does
  not establish that no reappearances occurred between releases.
- The caller must supply unique, chronologically ordered valid tags. The tracker
  does not sort or validate that sequence. Invalid tags are skipped, so a transition
  may span a gap rather than adjacent releases.
- Renames, namespace changes and kind changes split identities. Conversely,
  deletion and recreation under the same identity between samples is invisible.
  API group and cluster identity are absent from the key; multi-cluster or
  same-kind resources in different API groups may collide.
- Duplicate reports collapse at object/check level, losing container-level detail.
- A removal with the object still present is only a candidate fix: analyzer
  coverage, changed check behavior, filtering and parsing failures can mimic fixes.
- Object-deletion classification depends on complete, consistent inventories.
  Missing required inventory keys raise an error, but an incorrectly empty
  inventory can still produce a false deletion classification.
- The inventory reader does not fully parse YAML or expand `kind: List` objects.
  The current collection uses unrendered Helm/kustomize inputs as described in
  the repository README. Patch fragments can distort identity and removals.
- Categories are taken from findings, with the last category winning if an
  instance is inconsistently mapped. Use one frozen mapping per run.
- Instances remain tool-specific; cross-tool warnings are not deduplicated by
  tracking. Reappearance of an object is not counted as a first introduction.

## Validation when denser tags and rendered manifests arrive

Status: pending teammate data updates. Synthetic regression coverage is complete;
it is not evidence that future rendered data or new real tags have been validated.

1. Record the input commit, tag order, rendering tool versions and rendering
   options. Keep the current baseline outputs for comparison.
2. Confirm every new valid tag has both analyzer outputs and an object inventory
   from the same rendered manifests. Ensure skipped/crashed analyses are excluded.
3. Run `python -m pytest -q -rs` and `python -m kst --out out_dense_rendered`.
4. Inspect unmapped checks, inventory coverage, duplicate identities and changed
   names/namespaces introduced by rendering. Verify no unexpected identity merges.
5. Compare old sampled endpoints with matching new endpoints. Classify differences
   due to rendering separately from additional transitions revealed by denser tags.
6. Manually inspect representative introductions, persistence, removals and any
   reappearances in YAML and analyzer outputs. Check both object-deleted removals
   and candidate fixes; record analyzer artifacts separately.
7. Record input revisions, commands, counts, sampled evidence and unresolved
   differences in `results/tracking_validation.md` before declaring validation done.

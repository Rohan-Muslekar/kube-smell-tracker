# Rendering check: flux2 rendered vs. unrendered

Fallback for the strongest validity threat while the full renderer (`kst/render.py`,
`RENDER=1`) is pending. flux2 is the project where linting unrendered kustomize files matters
most: its `manifests/` tree is kustomize bases, patches and remote resources.

Ran this to get the data (2026-11-08, kubectl v1.36.2 with kustomize v5.8.1, kube-linter v0.8.3,
kube-score v1.20.0, network on, because flux2 pulls the controller Deployments from GitHub
release assets):

```bash
git clone -q work/flux2 /tmp/flux2-render          # a clone collect.sh is not using
python3 scripts/render_check.py flux2 --clone /tmp/flux2-render --out /tmp/render-flux2
# writes /tmp/render-flux2/{raw,data,out}/ and comparison.json; the unrendered side is
# git show milestone-2-data:out/instances.csv (the Milestone 2 run on the same five tags)
```

How it renders: every kustomization under `manifests/` that no other kustomization lists is
rendered with `kubectl kustomize` (15 at the first tag, 4 at v2.9.6). Plain YAML in a
kustomization's directory, or referenced by one, is not linted on its own. No render failed and
all five tags are valid. Everything after rendering (inventory, both analyzers, validation,
tracking) is the normal pipeline.

Same five tags (v0.36.0, v0.40.2, v2.2.3, v2.5.1, v2.9.6), smell instances excluding `other`:

| | Unrendered (M2) | Rendered |
|---|---|---|
| Instances | 97 | 162 |
| security / resource / image / hygiene | 38 / 36 / 12 / 11 | 49 / 86 / 27 / 0 |
| Present at first tag | 95 | 153 |
| Still present at last tag | 11 (11.6%) | 37 (24.2%) |
| Introduced (with a new object) | 2 (2) | 9 (9) |
| Removed | 84 | 116 |
| of which the object was deleted | 84 | 116 |
| Reappeared | 0 | 0 |

What changes:
- Unrendered, 84 of the 97 instances sit on two patch bases (`credentials-sync`,
  `credentials-sync-eventhub`). The six controller Deployments are not in the repository at all
  (they are remote resources), so they were never analyzed. Rendered, they are, and 33 of their
  smells persist at all five tags.
- All 11 hygiene instances disappear (`dangling-networkpolicy`, `networkpolicy-targets-pod`,
  selector mismatches). They came from linting fragments before kustomize adds the common labels,
  so they were false positives.

What does not change:
- Every flux2 removal is still an object deletion. Rendered, all 116 happen at v2.5.1 to v2.9.6,
  when flux2 deleted `manifests/integrations` (12 objects: the credentials-sync CronJobs,
  Deployments and RoleBindings).
- Study-wide, swapping flux2's unrendered results for the rendered ones moves the deletion share
  of removals from 108/147 (73.5%) to 140/179 (78.2%).

Caveat for the report: without flux2 the deletion share is 24/63 (38%). "Removals are mostly
deletions" holds for flux2 and Knative serving, not for every project; elsewhere removals are
mostly fixes.

# Rendering check: kustomize rendered vs. unrendered

Fallback for the strongest validity threat while the full renderer (`kst/render.py`,
`RENDER=1`) is pending. Only two studied projects ship kustomizations: flux2 (382 of the 388
kustomization files skipped by `collect.sh`) and microservices-demo (6, one top-level
`kubernetes-manifests/kustomization.yaml` per tag). Both are rendered here at every tag, so this
covers every kustomization in the study.

Ran this to get the data (2026-11-08, kubectl v1.36.2 with kustomize v5.8.1, kube-linter v0.8.3,
kube-score v1.20.0, network on, because flux2 pulls the controller Deployments from GitHub
release assets):

```bash
git clone -q work/flux2 /tmp/flux2-render                       # clones collect.sh is not using
git clone -q work/microservices-demo /tmp/msd-render
python3 scripts/render_check.py flux2 --clone /tmp/flux2-render --out /tmp/rc-flux2 \
    --field tags --baseline-ref master
python3 scripts/render_check.py microservices-demo --clone /tmp/msd-render --out /tmp/rc-msd \
    --field tags --baseline-ref master
# each writes {raw,data,out}/ and comparison.json; the unrendered side is master's
# out/instances.csv (the 123-tag run)
```

`results/render_check/<repo>/` keeps each `comparison.json` and the repo's rows of the rendered
`out/instances.csv`.

How it renders: every kustomization that no other kustomization lists is rendered with
`kubectl kustomize` (flux2: 15 at the first tag, 4 at v2.9.6; microservices-demo: 1). Plain YAML
in a kustomization's directory, or referenced by one, is not linted on its own. No render failed
and all 22 tags are valid. Everything after rendering (inventory, both analyzers, validation,
tracking) is the normal pipeline.

## Results (all tags, smell instances excluding `other`)

| | flux2 stored | flux2 rendered | microservices-demo stored | microservices-demo rendered |
|---|---|---|---|---|
| Tags | 16 | 16 | 6 | 6 |
| Instances | 97 | 162 | 182 | 166 |
| Present at first tag | 95 | 153 | 181 | 166 |
| Still present at last tag | 11 (11.6%) | 37 (24.2%) | 161 (89.0%) | 147 (88.6%) |
| Introduced (with a new object) | 2 (2) | 9 (9) | 1 (0) | 0 (0) |
| Removed (object deleted) | 84 (84) | 116 (116) | 20 (0) | 19 (0) |
| Reappeared | 0 | 0 | 0 | 0 |

The 16 flux2 tags give exactly the numbers of the five Milestone 2 tags: nothing changes between
sampled tags. microservices-demo's kustomization comments out `loadgenerator.yaml` ("during
development, the loadgenerator module inside skaffold.yaml will be used"), so rendering drops that
one Deployment and its 16 instances; nothing else differs.

Study-wide, replacing both projects with their rendered results (123 tags, smells only):

| | Stored (master) | Rendered |
|---|---|---|
| Instances | 862 | 911 |
| First-tag instances still present at the last tag | 676/821 (82.3%) | 688/864 (79.6%) |
| Removals that are object deletions | 106/147 (72.1%) | 138/178 (77.5%) |
| Real fixes (excluding the kube-score probe artifact) | 32 | 31 |
| Reappeared | 0 | 0 |

## flux2 details (Milestone 2 tags, unchanged on all 16)

Five Milestone 2 tags (v0.36.0, v0.40.2, v2.2.3, v2.5.1, v2.9.6), unrendered side from git tag `milestone-2-data`:

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
- On the five Milestone 2 tags, swapping flux2's unrendered results for the rendered ones moves
  the study-wide deletion share of removals from 108/147 (73.5%) to 140/179 (78.2%).

Caveat for the report: on the 123-tag data without flux2 the deletion share is 22/63 (34.9%). "Removals are mostly
deletions" holds for flux2 and Knative serving, not for every project; elsewhere removals are
mostly fixes.

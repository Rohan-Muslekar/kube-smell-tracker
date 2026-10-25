# RQ3: Investigation of Configuration Smell Transitions

## Objective

RQ3 investigates why Kubernetes configuration smells disappear or appear between sampled releases. We distinguish genuine configuration fixes, newly introduced smells, object deletions, and analyzer artifacts.

The investigation uses the transition outputs and the 20-instance manual spot-check from Milestone 2, together with GitHub release comparisons and commit history.

`data/rq3_investigations.csv` holds the same 20 instances as `data/spot_check.csv`, with the commit and evidence behind each one.

## Case Study 1: Genuine Security Fix — kube-state-metrics

**Project:** kube-prometheus  
**Object:** Deployment/monitoring/kube-state-metrics  
**Versions:** v0.12.0 → v0.14.0  
**Check:** container-security-context-user-group-id  
**Classification:** Real fix

The earlier configuration lacked an explicit `runAsGroup` setting for the main kube-state-metrics container.

Commit `387731a`, authored on May 14, 2024, introduced `runAsGroup: 65534` in both the Jsonnet source and the generated Deployment manifest.

Evidence: https://github.com/prometheus-operator/kube-prometheus/commit/387731a

**Finding:** This is a genuine fix because the configuration was changed while the Kubernetes object remained present. The disappearing analyzer warning corresponds to a concrete security configuration improvement.

## Case Study 2: Analyzer Artifact — recommendationservice

**Project:** microservices-demo  
**Object:** Deployment/recommendationservice  
**Versions:** v0.7.0 → v0.9.0  
**Check:** pod-probes-identical  
**Classification:** Analyzer artifact

The earlier configuration used identical exec-based health probes. In the later release, the probes switched to gRPC while retaining equivalent configurations.

The kube-score warning disappeared because the analyzer did not compare these gRPC probes in the same way.

Commit `157ef70`, authored on June 13, 2023 (PR 1837, "Remove use of gRPC health probe binary"), made the switch.

Evidence: https://github.com/GoogleCloudPlatform/microservices-demo/commit/157ef70

**Finding:** The disappearance of a warning does not necessarily indicate that its underlying configuration smell was corrected.

The manual investigation identifies this transition as an analyzer artifact rather than a genuine fix.

## Case Study 3: Object Deletion — flux2 Credential Integrations

**Project:** flux2  
**Versions:** v2.5.1 → v2.9.6  
**Objects:** credentials-sync and credentials-sync-eventhub  
**Classification:** Object deletion

The Milestone 2 analysis found that the credential integration manifests disappeared when the integrations directory was removed.

These files included unrendered Kustomize patch fragments. Their disappearance caused associated analyzer findings to disappear as well.

Commit `9cad95d` ("Remove credentials sync manifests", PR 5347, merged June 4, 2025) deleted them. v2.7.0 is the first tag that contains it.

Evidence: https://github.com/fluxcd/flux2/pull/5347

**Finding:** Object deletion must be distinguished from a genuine configuration fix. The disappearance of the entire object does not demonstrate remediation of the underlying smell.

## Case Study 4: Smells Introduced by Fixes — argo-cd Redis

**Project:** argo-cd  
**Objects:** RoleBinding/argocd-redis, StatefulSet/argocd-application-controller, Deployment/argocd-redis  
**Versions:** v2.5.22 → v2.9.22  
**Checks:** access-to-secrets, read-secret-from-env-var, pod-networkpolicy  
**Classification:** Side effect of a fix

All three introductions come from fixes backported to the 2.9 release branch, not from careless changes:

- Commit `53570cbd1` (2024-05-21) is the backport of the fix for advisory GHSA-9766-5277-j5hr, which enables Redis authentication by default. It passes `REDIS_PASSWORD` to the application controller through `secretKeyRef` and lets the `argocd-redis` Role read secrets. kube-linter flags both.
- Commit `2e7fbb042` (2024-05-23, PR 18382) removes the egress rules from the `argocd-redis` NetworkPolicy. kube-score then finds no egress policy for the pod.

Evidence: https://github.com/argoproj/argo-cd/security/advisories/GHSA-9766-5277-j5hr, https://github.com/argoproj/argo-cd/pull/18382

**Finding:** An introduced smell is not always a regression. Here a security fix added the secret access that the analyzers report.

## Baseline Quantitative Results

Across 35 sampled versions from seven projects, the baseline identified 862 smell instances, counted separately by analyzer.

Of the 821 instances present at the first sampled versions, 676 (82.3%) persisted through the final sampled versions.

Among 147 recorded removals:

- 108 resulted from object deletions.
- 39 occurred while their objects remained.
- 9 of those 39 were identified as analyzer artifacts.
- 30 therefore remained classified as genuine fixes at the analyzer-instance level.
- These corresponded to 24 distinct fixes when overlapping reports were consolidated by object, category, and transition.

The analysis also identified 41 introductions, including 16 associated with newly introduced objects. No reappearances were observed across the sampled releases.

These numbers come from `python3 scripts/summary.py`, run from the repository root. Each commit above can be checked against the sampled tags in a clone, for example:

```
git -C work/kube-prometheus merge-base --is-ancestor 387731a v0.14.0
git -C work/flux2 tag --contains 9cad95d | sort -V | head -1
git -C work/argo-cd show 53570cbd1 -- manifests/install.yaml
```

## Limitations and Remaining Investigation

The initial manual spot-check included 20 instances. Nineteen matched their assigned transition explanations, while one apparent fix was identified as an analyzer artifact.

The investigation remains incomplete in three areas:

1. Commits are traced for the 20 spot-check instances only, not for every transition.
2. Some examples require further inspection of the original configuration changes and analyzer behavior.
3. Quantitative results must be regenerated after denser tag sampling, rendered manifests, or category-mapping updates are incorporated.

The baseline results should not be presented as final updated RQ3 results until these steps are completed.

## Preliminary Conclusion

Configuration smell transitions cannot be explained using analyzer output alone. A disappearing warning may represent a genuine fix, deletion of a Kubernetes object, or a limitation of the analyzer.

Commit-level investigation and manual configuration comparison provide necessary evidence for distinguishing these outcomes.

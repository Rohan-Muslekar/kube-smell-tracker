# RQ3: Investigation of Configuration Smell Transitions

## Objective

RQ3 investigates why Kubernetes configuration smells disappear or appear between sampled releases. We distinguish genuine configuration fixes, newly introduced smells, object deletions, and analyzer artifacts.

The investigation uses the transition outputs and the 20-instance manual spot-check from Milestone 2, together with GitHub release comparisons and commit history.

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

Evidence: https://github.com/GoogleCloudPlatform/microservices-demo/compare/v0.7.0...v0.9.0

**Finding:** The disappearance of a warning does not necessarily indicate that its underlying configuration smell was corrected.

The manual investigation identifies this transition as an analyzer artifact rather than a genuine fix. The exact introducing commit remains to be documented.

## Case Study 3: Object Deletion — flux2 Credential Integrations

**Project:** flux2  
**Versions:** v2.5.1 → v2.9.6  
**Objects:** credentials-sync and credentials-sync-eventhub  
**Classification:** Object deletion

The Milestone 2 analysis found that the credential integration manifests disappeared when the integrations directory was removed.

These files included unrendered Kustomize patch fragments. Their disappearance caused associated analyzer findings to disappear as well.

Evidence: https://github.com/fluxcd/flux2/compare/v2.5.1...v2.9.6

**Finding:** Object deletion must be distinguished from a genuine configuration fix. The disappearance of the entire object does not demonstrate remediation of the underlying smell.

The exact deletion commit remains to be traced.

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

## Limitations and Remaining Investigation

The initial manual spot-check included 20 instances. Nineteen matched their assigned transition explanations, while one apparent fix was identified as an analyzer artifact.

The investigation remains incomplete in three areas:

1. Exact introducing commits have not been verified for every transition.
2. Some examples require further inspection of the original configuration changes and analyzer behavior.
3. Quantitative results must be regenerated after denser tag sampling, rendered manifests, or category-mapping updates are incorporated.

The baseline results should not be presented as final updated RQ3 results until these steps are completed.

## Preliminary Conclusion

Configuration smell transitions cannot be explained using analyzer output alone. A disappearing warning may represent a genuine fix, deletion of a Kubernetes object, or a limitation of the analyzer.

Commit-level investigation and manual configuration comparison provide necessary evidence for distinguishing these outcomes.

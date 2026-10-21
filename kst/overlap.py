"""Compare kube-linter and kube-score on the same object and category, before any de-duplication."""
from collections import defaultdict

TOOLS = ("kube-linter", "kube-score")


def overlap(findings, kinds=None):
    """One row per (repo, kind, namespace, name, category) flagged by either tool at any tag.

    A pair counts once, not once per tag, so long-lived objects do not dominate the totals.

    `kinds` limits the comparison to object kinds both tools analyse; kube-score never
    scores RBAC objects, for example, so those would always look "kube-linter only".
    """
    tools = defaultdict(set)
    for f in findings:
        if f.category == "other" or (kinds is not None and f.kind not in kinds):
            continue
        tools[(f.repo, f.kind, f.namespace, f.name, f.category)].add(f.tool)
    return [{"repo": k[0], "kind": k[1], "namespace": k[2], "name": k[3], "category": k[4],
             "in_linter": TOOLS[0] in t, "in_score": TOOLS[1] in t}
            for k, t in sorted(tools.items())]


def overlap_summary(rows):
    counts = defaultdict(lambda: {"linter_only": 0, "score_only": 0, "both": 0})
    for r in rows:
        bucket = "both" if r["in_linter"] and r["in_score"] else "linter_only" if r["in_linter"] else "score_only"
        counts[r["category"]][bucket] += 1
    return [{"category": c, **n} for c, n in sorted(counts.items())]

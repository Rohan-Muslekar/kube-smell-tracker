"""Follow each smell instance across a repo's release tags and label every version-to-version step."""
from collections import defaultdict

LABELS = ("introduced", "persisted", "removed", "reappeared")


def classify(presence):
    """Label each consecutive (previous, current) pair of a presence history."""
    labels, seen = [], presence[:1] == [True]
    for prev, cur in zip(presence, presence[1:]):
        if prev and cur:
            labels.append("persisted")
        elif prev:
            labels.append("removed")
        elif cur:
            labels.append("reappeared" if seen else "introduced")
        else:
            labels.append("absent")
        seen = seen or cur
    return labels


def instance_key(f):
    """Identity of a smell instance across versions; the file is left out so moves keep identity."""
    return (f.repo, f.tool, f.kind, f.namespace, f.name, f.check)


def track(findings, versions, objects=None):
    """One row per instance. `versions` maps repo -> valid tags, oldest first; other tags are ignored.

    `objects` maps (repo, tag) -> set of (kind, namespace, name) defined at that tag. With it,
    `removed_object_gone` counts removals where the whole object was deleted (not a fix), and
    `introduced_new_object` counts introductions that came with a newly added object.
    """
    present = defaultdict(set)
    category = {}
    for f in findings:
        if f.version not in versions.get(f.repo, ()):
            continue
        key = instance_key(f)
        present[key].add(f.version)
        category[key] = f.category

    rows = []
    for key in sorted(present):
        repo, tool, kind, namespace, name, check = key
        history = [v in present[key] for v in versions[repo]]
        labels = classify(history)
        row = {"repo": repo, "tool": tool, "check": check, "category": category[key], "kind": kind,
               "namespace": namespace, "name": name,
               "presence": "".join("1" if p else "0" for p in history), "at_baseline": int(history[0])}
        row.update({label: labels.count(label) for label in LABELS})
        if objects is not None:
            obj, tags = (kind, namespace, name), versions[repo]
            steps = list(zip(tags, tags[1:], labels))
            row["removed_object_gone"] = sum(1 for _, cur, label in steps
                                             if label == "removed" and obj not in objects[(repo, cur)])
            row["introduced_new_object"] = sum(1 for prev, _, label in steps
                                               if label == "introduced" and obj not in objects[(repo, prev)])
        rows.append(row)
    return rows

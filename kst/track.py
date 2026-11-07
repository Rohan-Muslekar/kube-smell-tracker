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


def probable_renames(findings, versions, objects):
    """Candidate object pairs per step, with matching sets of (tool, check).

    Inventories establish disappearance/appearance independently of analyzer coverage.
    Many-to-many matches remain candidates, never an asserted identity merge.
    """
    if objects is None:
        return []
    checks = defaultdict(lambda: defaultdict(set))
    for f in findings:
        if f.version in versions.get(f.repo, ()):
            checks[(f.repo, f.version)][(f.kind, f.namespace, f.name)].add((f.tool, f.check))
    candidates = []
    for repo, tags in versions.items():
        for prev, cur in zip(tags, tags[1:]):
            before, after = objects[(repo, prev)], objects[(repo, cur)]
            added = defaultdict(list)
            for obj in sorted(after - before):
                signature = frozenset(checks[(repo, cur)][obj])
                if signature:
                    added[(obj[0], signature)].append(obj)
            for old in sorted(before - after):
                signature = frozenset(checks[(repo, prev)][old])
                for new in added.get((old[0], signature), ()):
                    if old[2] != new[2]:
                        candidates.append({"repo": repo, "from_tag": prev, "to_tag": cur,
                                           "old": old, "new": new, "checks": sorted(signature)})
    return candidates


def track(findings, versions, objects=None):
    """One row per instance. `versions` maps repo -> valid tags, oldest first; other tags are ignored.

    `objects` maps (repo, tag) -> set of (kind, namespace, name) defined at that tag. With it,
    `removed_object_gone` counts removals where the whole object was deleted (not a fix), and
    `introduced_new_object` counts introductions that came with a newly added object.
    """
    findings = list(findings)
    if objects is not None:
        # Check every tag up front: a lookup only happens at a removal or introduction, so a
        # missing inventory elsewhere would otherwise pass unnoticed.
        missing = [(repo, tag) for repo, tags in versions.items() for tag in tags if (repo, tag) not in objects]
        if missing:
            raise KeyError(f"No object inventory for {missing}")
    present = defaultdict(set)
    category = {}
    for f in findings:
        if f.version not in versions.get(f.repo, ()):
            continue
        key = instance_key(f)
        present[key].add(f.version)
        category[key] = f.category

    flagged = set()
    for candidate in probable_renames(findings, versions, objects):
        for kind, namespace, name in (candidate["old"], candidate["new"]):
            for tool, check in candidate["checks"]:
                flagged.add((candidate["repo"], tool, kind, namespace, name, check))

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
        row["probable_rename"] = int(key in flagged)
        rows.append(row)
    return rows

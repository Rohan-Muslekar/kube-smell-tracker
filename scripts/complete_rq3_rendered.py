"""Prepare evidence-backed, AI-assisted *draft* traces of 21 rendered RQ3 transitions.

Default (safe): write results/rq3_rendered_traces_draft.csv only.
--apply: requires actual rendered out/instances.csv and a local flux2 Git clone;
         checks tag-specific presence changes and Git ancestry, then appends only
         verified *draft* rows to data/rq3_investigations.csv. The rows remain
         AI-assisted pending a human's verification, NOT independent recoding.
"""
import argparse
import csv
import io
import os
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = {
    "roles": "65055c273f7c62ed843e2421a6354c365ca0b2cb",
    "watcher": "0a87ed5a425d86ea909b3720fda196037d0c79ad",
    "deletion": "9cad95dda538d4751ac82725da66dc7a6b645fcf",
}
TRACED_FIELDS = ("repo", "object_kind", "namespace", "object_name", "check",
                 "from_tag", "to_tag", "transition", "classification", "commit_url",
                 "configuration_change", "evidence_url", "verification_status", "notes")
DRAFT_FIELDS = ("repo", "object_kind", "namespace", "object_name", "check", "from_tag", "to_tag",
                "todo_transition", "resulting_transition", "classification", "n_smells",
                "commit_url", "configuration_change", "evidence_url", "review_status")


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def identify(todo):
    name, kind, transition = todo["object_name"], todo["object_kind"], todo["transition"]
    if todo.get("repo") != "flux2":
        raise ValueError(f"Unexpected repo: {todo.get('repo')}")
    if transition == "introduced_new_object" and kind == "ClusterRole" and name in ("flux-edit", "flux-view"):
        return (SHA["roles"], "introduced", "new_object",
                "Flux PR #3566 adds the aggregated RBAC role through manifests/rbac and kustomization",
                "https://github.com/fluxcd/flux2/pull/3566")
    if transition == "introduced_new_object" and kind == "Deployment" and name == "source-watcher":
        return (SHA["watcher"], "introduced", "new_object",
                "Adds source-watcher to rendered Flux manifests via manifests/bases/source-watcher/kustomization.yaml",
                "https://github.com/fluxcd/flux2/commit/" + SHA["watcher"])
    if transition == "removed_object_deleted" and (name.endswith("credentials-sync") or name == "jwt-credentials-sync-eventhub"):
        if kind not in ("CronJob", "Deployment", "RoleBinding"):
            raise ValueError(f"Unexpected object type for deletion: {kind}")
        return (SHA["deletion"], "object_deleted", "object_deleted",
                "Remove credentials sync manifests (Flux PR #5347)",
                "https://github.com/fluxcd/flux2/pull/5347")
    raise ValueError(f"Unrecognized rendered transition: {kind} {name} {transition}")


def build_draft(todo_rows):
    if len(todo_rows) != 21:
        raise ValueError(f"Expected 21 rendered transitions, found {len(todo_rows)}")
    rows, seen = [], set()
    for t in todo_rows:
        key = tuple(t.get(f, "") for f in ("repo", "object_kind", "namespace", "object_name", "check", "from_tag", "to_tag"))
        if key in seen:
            raise ValueError(f"Duplicate rendered item: {key}")
        seen.add(key)
        sha, transition, cls, change, url = identify(t)
        rows.append({**{k: t.get(k, "") for k in DRAFT_FIELDS},
                     "todo_transition": t["transition"], "resulting_transition": transition,
                     "classification": cls,
                     "commit_url": "https://github.com/fluxcd/flux2/commit/" + sha,
                     "configuration_change": change, "evidence_url": url,
                     "review_status": "AI-assisted draft; requires human sign-off and rendered-data validation"})
    return rows


def write_csv(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def indexed_presence(instance_rows):
    by_object = defaultdict(list)
    for r in instance_rows:
        k = (r["repo"], r["kind"], r["namespace"], r["name"])
        by_object[k].append(r)
    return by_object


def validated_study_transition(row, by_object, tags):
    repo = row["repo"]
    tag_list = tags.get(repo) or []
    first, second = row["from_tag"], row["to_tag"]
    if first not in tag_list or second not in tag_list or tag_list.index(second) != tag_list.index(first) + 1:
        raise ValueError(f"Invalid consecutive study tags: {repo} {first} -> {second}")
    i, j = tag_list.index(first), tag_list.index(second)
    key = (row["repo"], row["object_kind"], row["namespace"], row["object_name"])
    candidates = []
    for r in by_object.get(key, []):
        presence = r["presence"]
        want = ("0", "1") if row["resulting_transition"] == "introduced" else ("1", "0")
        if len(presence) > j and (presence[i], presence[j]) == want:
            if row["check"] == "(all smells on the object)" or r["check"] == row["check"]:
                candidates.append(r["check"])
    if not candidates:
        raise ValueError(f"Rendered data does not validate transition for {key} {first}->{second}. "
                         "Run the integration with RENDER=1 before --apply.")
    return sorted(candidates)[0]


def git_ancestor(clone, older, newer):
    return subprocess.run(["git", "-C", str(clone), "merge-base", "--is-ancestor", older, newer],
                          capture_output=True).returncode == 0


def prepare_additions(draft_rows, instance_rows, versions_rows, original_rows, clone, check_git=True):
    tags = defaultdict(list)
    for r in versions_rows:
        if r["valid"] == "1":
            tags[r["repo"]].append(r["tag"])
    by_obj = indexed_presence(instance_rows)
    exists = {(r["repo"], r["object_kind"], r["namespace"], r["object_name"], r["check"],
               r["from_tag"], r["to_tag"], r["transition"]) for r in original_rows}
    planned = []
    for row in draft_rows:
        check = validated_study_transition(row, by_obj, tags)
        sha = row["commit_url"].rsplit("/", 1)[-1]
        if check_git and (not git_ancestor(clone, sha, row["to_tag"]) or git_ancestor(clone, sha, row["from_tag"])):
            raise ValueError(f"Commit {sha[:10]} not proven in study tag range {row['from_tag']}..{row['to_tag']}")
        new_row = {"repo": row["repo"], "object_kind": row["object_kind"], "namespace": row["namespace"],
                   "object_name": row["object_name"], "check": check, "from_tag": row["from_tag"],
                   "to_tag": row["to_tag"], "transition": row["resulting_transition"],
                   "classification": row["classification"], "commit_url": row["commit_url"],
                   "configuration_change": row["configuration_change"], "evidence_url": row["evidence_url"],
                   "verification_status": "ai_assisted_pending_review",
                   "notes": f"Rendered transition, {row['n_smells']} smell(s); needs independent human sign-off"}
        k = tuple(new_row[f] for f in ("repo", "object_kind", "namespace", "object_name", "check",
                                      "from_tag", "to_tag", "transition"))
        if k not in exists:
            planned.append(new_row)
            exists.add(k)
    return planned


def apply(root, draft, clone):
    raw_fields, original = load_csv(root / "data/rq3_investigations.csv")
    _, versions = load_csv(root / "data/versions.csv")
    _, instances = load_csv(root / "out/instances.csv")
    if set(TRACED_FIELDS) - set(raw_fields or []):
        raise ValueError("Unexpected investigations.csv schema")
    new = prepare_additions(draft, instances, versions, original, clone)
    if not new:
        print("All rendered rows already represented; nothing to append")
        return 0
    backup = root / "results/rq3_investigations_before_rendered.csv"
    if backup.exists():
        raise FileExistsError(f"Backup already exists; refusing to overwrite: {backup}")
    write_csv(backup, raw_fields, original)
    path = root / "data/rq3_investigations.csv"
    # Write and replace atomically, *after* validating every row and SHA.
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as fd:
        temp = Path(fd.name)
        writer = csv.DictWriter(fd, fieldnames=raw_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(original + new)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    print(f"Appended {len(new)} evidence-backed AI-assisted draft rows; needs human sign-off")
    print(f"Original dataset backup: {backup}")
    return len(new)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Only after rendered data is generated and reviewed")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        _, todo = load_csv(args.root / "data/rq3_rendered_todo.csv")
        draft = build_draft(todo)
        draft_path = args.root / "results/rq3_rendered_traces_draft.csv"
        if args.apply:
            apply(args.root, draft, args.root / "work/flux2")
        else:
            write_csv(draft_path, DRAFT_FIELDS, draft)
            print(f"Wrote {len(draft)} rendered evidence draft rows: {draft_path}")
            print("Commits: roles 65055c2; watcher 0a87ed5; deletions 9cad95d")
            print("No independent human coding has been performed")
    except (OSError, KeyError, ValueError, IndexError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

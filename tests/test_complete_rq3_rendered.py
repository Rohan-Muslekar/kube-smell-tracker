"""Offline tests of RQ3 rendered evidence and safe merge preparation."""
import csv
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/complete_rq3_rendered.py"
spec = importlib.util.spec_from_file_location("complete_rq3_rendered", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def todo(object_name, kind, transition, check="wildcard-in-rules", old="v1", new="v2", n="1"):
    return {"repo": "flux2", "object_kind": kind, "namespace": "flux-system",
            "object_name": object_name, "check": check,
            "from_tag": old, "to_tag": new, "transition": transition, "n_smells": n}


def all_rows():
    rows = [todo("flux-edit", "ClusterRole", "introduced_new_object"),
            todo("flux-view", "ClusterRole", "introduced_new_object")]
    checks = ["minimum-three-replicas", "no-rolling-update-strategy", "container-ephemeral-storage-request-and-limit",
              "container-image-pull-policy", "container-security-context-user-group-id", "deployment-replicas", "deployment-strategy"]
    rows += [todo("source-watcher", "Deployment", "introduced_new_object", check=c) for c in checks]
    for kind in ("CronJob", "Deployment", "RoleBinding"):
        for name in ("acr-credentials-sync", "ecr-credentials-sync", "gcr-credentials-sync", "jwt-credentials-sync-eventhub"):
            rows.append(todo(name, kind, "removed_object_deleted", check="(all smells on the object)", n="14"))
    return rows


def test_21_with_correct_commit_and_classes():
    rows = m.build_draft(all_rows())
    assert len(rows) == 21
    assert all(row["commit_url"].endswith(m.SHA["roles"]) for row in rows[:2])
    assert all(row["commit_url"].endswith(m.SHA["watcher"]) for row in rows[2:9])
    assert all(row["commit_url"].endswith(m.SHA["deletion"]) for row in rows[9:])
    assert [r["classification"] for r in rows].count("object_deleted") == 12


def test_unknown_rows_fail():
    rows = all_rows()
    rows[0]["object_name"] = "unfamiliar"
    with pytest.raises(ValueError, match="Unrecognized"):
        m.build_draft(rows)


def test_wrong_size_fail():
    with pytest.raises(ValueError, match="Expected 21"):
        m.build_draft(all_rows()[:20])


def test_presence_validation_and_no_rendered_data_error():
    sample = m.build_draft(all_rows())[2]
    tags = {"flux2": ["v1", "v2"]}
    match = {("flux2", "Deployment", "flux-system", "source-watcher"):
             [{"repo": "flux2", "kind": "Deployment", "namespace": "flux-system",
               "name": "source-watcher", "check": sample["check"], "presence": "01"}]}
    assert m.validated_study_transition(sample, match, tags) == sample["check"]
    match.clear()
    with pytest.raises(ValueError, match="RENDER=1"):
        m.validated_study_transition(sample, match, tags)


def test_no_change_on_failed_validation(tmp_path):
    repo = tmp_path
    (repo/"data").mkdir()
    (repo/"out").mkdir()
    source = repo/"data/rq3_investigations.csv"
    m.write_csv(source, list(m.TRACED_FIELDS), [])
    m.write_csv(repo/"data/versions.csv", ["repo", "tag", "valid"],
                [{"repo": "flux2", "tag": "v1", "valid": "1"},
                 {"repo": "flux2", "tag": "v2", "valid": "1"}])
    m.write_csv(repo/"out/instances.csv", ["repo", "kind", "namespace", "name", "check", "presence"], [])
    original = source.read_bytes()
    with pytest.raises(ValueError, match="RENDER=1"):
        m.apply(repo, m.build_draft(all_rows()), repo/"work/flux2")
    assert source.read_bytes() == original
    assert not (repo/"results/rq3_investigations_before_rendered.csv").exists()

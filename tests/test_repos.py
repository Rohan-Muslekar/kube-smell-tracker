import json

import pytest

from kst.repos import load_repos


def _repo(name, tags=("v1", "v2", "v3")):
    return {"name": name, "url": f"https://example.com/{name}.git",
            "manifest_paths": ["deploy"], "tags": list(tags), "reason": "test"}


def _write(tmp_path, included, excluded=()):
    p = tmp_path / "repos.json"
    p.write_text(json.dumps({"included": included, "excluded": list(excluded)}))
    return str(p)


def test_load_repos_valid(tmp_path):
    path = _write(tmp_path, [_repo(f"r{i}") for i in range(5)])
    repos = load_repos(path)
    assert [r["name"] for r in repos] == ["r0", "r1", "r2", "r3", "r4"]


def test_rejects_fewer_than_3_tags(tmp_path):
    path = _write(tmp_path, [_repo(f"r{i}") for i in range(4)] + [_repo("short", tags=("v1", "v2"))])
    with pytest.raises(ValueError, match="short"):
        load_repos(path)


def test_rejects_fewer_than_5_included(tmp_path):
    path = _write(tmp_path, [_repo(f"r{i}") for i in range(4)])
    with pytest.raises(ValueError, match="5"):
        load_repos(path)

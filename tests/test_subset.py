import csv
import json

from kst.subset import make_subset

HEADER = "repo,tag,commit_sha,commit_date,n_yaml_files,valid,note\n"


def _data(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "repos.json").write_text(json.dumps({"included": [
        {"name": "a", "tags": ["v1", "v2", "v3"], "tags_milestone2": ["v1", "v3"]},
        {"name": "b", "tags": ["v5", "v6"], "tags_milestone2": ["v6"]},
    ]}))
    (data / "versions.csv").write_text(HEADER + "a,v1,s,d,1,1,\na,v2,s,d,1,1,\na,v3,s,d,1,0,crash\n"
                                       "b,v5,s,d,1,1,\nb,v6,s,d,1,1,\n")
    (data / "check_categories.csv").write_text("tool,check,category,rationale\n")
    return data


def test_subset_keeps_only_listed_tags_in_order(tmp_path):
    out = tmp_path / "sub"
    make_subset(_data(tmp_path), "tags_milestone2", out)
    with open(out / "versions.csv", newline="") as f:
        rows = [(r["repo"], r["tag"], r["valid"]) for r in csv.DictReader(f)]
    assert rows == [("a", "v1", "1"), ("a", "v3", "0"), ("b", "v6", "1")]


def test_subset_copies_the_other_data_files(tmp_path):
    out = tmp_path / "sub"
    make_subset(_data(tmp_path), "tags_milestone2", out)
    assert (out / "check_categories.csv").read_text() == "tool,check,category,rationale\n"
    assert (out / "repos.json").exists()

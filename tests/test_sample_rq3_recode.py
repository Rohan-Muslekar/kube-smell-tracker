"""Tests for the blind RQ3 sampling script."""

import csv
import importlib.util
from collections import Counter
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sample_rq3_recode.py"
spec = importlib.util.spec_from_file_location("sample_rq3_recode", SCRIPT)
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)


def fixture(tmp_path, counts=(33, 23, 9, 4, 5)):
    path = tmp_path / "original.csv"
    fields = (*sampler.KEY_FIELDS, "classification", "commit_url", "notes", "configuration_change")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for cl, total in zip(sampler.CLASSES, counts):
            for index in range(total):
                writer.writerow(dict(repo="sample", object_kind="Deployment", namespace="",
                                     object_name=f"{cl}-{index}", check="check", from_tag="v1",
                                     to_tag="v2", transition="introduced", classification=cl,
                                     commit_url=f"https://example.org/{cl}/{index}",
                                     notes="PRIVATE FIRST CODER NOTES", configuration_change="SECRET"))
        writer.writerow(dict(repo="sample", object_kind="Deployment", namespace="",
                             object_name="excluded-persisting", check="check", from_tag="v1",
                             to_tag="v2", transition="persisted", classification="persisting_smell"))
    return path


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_sample_is_blinded_stratified_reproducible_and_20_rows(tmp_path):
    source = fixture(tmp_path)
    output1 = tmp_path / "first.csv"
    output2 = tmp_path / "second.csv"
    assert sampler.make_sample(source, output1) == 20
    assert sampler.make_sample(source, output2) == 20
    assert output1.read_bytes() == output2.read_bytes()
    rows = read_csv(output1)
    assert len(rows) == 20
    assert len({tuple(row[field] for field in sampler.KEY_FIELDS) for row in rows}) == 20
    assert all(row["classification"] == "" for row in rows)
    assert all("PRIVATE" not in str(row) and "SECRET" not in str(row) for row in rows)
    assert all("notes" not in row and "configuration_change" not in row for row in rows)
    assert not any(row["object_name"] == "excluded-persisting" for row in rows)
    labels = {row["object_name"].rsplit("-", 1)[0] for row in rows}
    counts = Counter(row["object_name"].rsplit("-", 1)[0] for row in rows)
    assert labels == set(sampler.CLASSES)
    assert all(counts[cl] >= 2 for cl in sampler.CLASSES)


def test_does_not_overwrite_existing_sheet(tmp_path):
    source = fixture(tmp_path)
    dest = tmp_path / "sheet.csv"
    dest.write_text("do not replace me\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        sampler.make_sample(source, dest)
    assert dest.read_text() == "do not replace me\n"


def test_fails_when_class_too_small(tmp_path):
    source = fixture(tmp_path, counts=(33, 23, 9, 1, 5))
    with pytest.raises(ValueError, match="new_object"):
        sampler.make_sample(source, tmp_path / "sheet.csv")
    assert not (tmp_path / "sheet.csv").exists()


def test_fails_with_duplicate_identities(tmp_path):
    source = fixture(tmp_path)
    with source.open("a", encoding="utf-8") as stream:
        stream.write("sample,Deployment,,real_fix-0,check,v1,v2,introduced,real_fix,https://x,,\n")
    with pytest.raises(ValueError, match="Duplicate"):
        sampler.make_sample(source, tmp_path / "sheet.csv")

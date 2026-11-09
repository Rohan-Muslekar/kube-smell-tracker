import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "minor_dates", Path(__file__).parent.parent / "scripts" / "minor_dates.py")
minor_dates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(minor_dates)


def test_each_sampled_tag_gets_its_minors_first_release_date():
    versions = [{"repo": "a", "tag": "v0.9.0"}, {"repo": "a", "tag": "v0.10.7"}]
    dates = {"a": {"v0.9.0": "2023-12-18", "v0.10.0": "2024-04-23", "v0.10.7": "2026-09-18"}}
    assert minor_dates.rows(versions, dates) == [
        {"repo": "a", "tag": "v0.9.0", "minor_first_tag": "v0.9.0", "minor_first_date": "2023-12-18"},
        {"repo": "a", "tag": "v0.10.7", "minor_first_tag": "v0.10.0", "minor_first_date": "2024-04-23"},
    ]


def test_missing_first_release_is_an_error():
    with pytest.raises(ValueError, match="v0.10.0"):
        minor_dates.rows([{"repo": "a", "tag": "v0.10.7"}], {"a": {"v0.10.7": "2026-09-18"}})

import os
import subprocess

import pytest

from kst.select_tags import dense_tags, tag_dates, evenly_spaced, latest_patch_per_minor


def test_latest_patch_per_minor_ignores_prereleases():
    tags = ["v1.0.0", "v1.0.3", "v1.1.0", "v1.1.0-rc.1", "v1.2.1", "v1.2.10", "1.3.0", "stable-2.0"]
    assert latest_patch_per_minor(tags) == {(1, 0): "v1.0.3", (1, 1): "v1.1.0", (1, 2): "v1.2.10", (1, 3): "1.3.0"}


def test_evenly_spaced_keeps_both_ends():
    assert evenly_spaced(list(range(9)), 5) == [0, 2, 4, 6, 8]


def test_evenly_spaced_short_list_returned_whole():
    assert evenly_spaced([1, 2, 3], 5) == [1, 2, 3]


# Dense mode: every minor in the window, pinned to a cut-off date and to tags already in use.
DATES = {
    "v1.0.0": "2022-01-10", "v1.0.4": "2022-03-01",                         # minor before the window
    "v1.1.0": "2022-11-01", "v1.1.2": "2022-12-01",
    "v1.2.0": "2023-05-01", "v1.2.3": "2023-06-01", "v1.2.4": "2026-11-01",  # v1.2.4 after cut-off
    "v1.3.0": "2024-02-01", "v1.3.1": "2024-03-01", "v1.3.5": "2024-09-01",
    "v1.4.0": "2026-11-02",                                                 # minor after cut-off
}


def test_dense_takes_latest_patch_of_every_minor_in_window():
    assert dense_tags(DATES, since="2022-10-22", until="2026-10-22") == ["v1.1.2", "v1.2.3", "v1.3.5"]


def test_dense_ignores_patches_released_after_cutoff():
    assert "v1.2.4" not in dense_tags(DATES, since="2022-10-22", until="2026-10-22")


def test_dense_keeps_pinned_tag_for_its_minor():
    tags = dense_tags(DATES, since="2022-10-22", until="2026-10-22", keep=["v1.3.1"])
    assert tags == ["v1.1.2", "v1.2.3", "v1.3.1"]


def test_dense_orders_by_version_not_release_date():
    # Same order as the five-tag mode: a backported patch of an older minor still comes first.
    dates = {"v2.0.0": "2023-01-01", "v1.9.0": "2022-12-01", "v1.9.1": "2023-03-01"}
    assert dense_tags(dates, since="2022-10-22", until="2026-10-22") == ["v1.9.1", "v2.0.0"]


def test_dense_includes_every_kept_tag():
    # A kept tag outside the computed set would silently drop a Milestone 2 version.
    with pytest.raises(ValueError, match="v1.0.4"):
        dense_tags(DATES, since="2022-10-22", until="2026-10-22", keep=["v1.0.4"])


def test_tag_dates_reads_lightweight_and_annotated_tags(tmp_path):
    env = {**os.environ, "GIT_COMMITTER_DATE": "2024-05-06T12:00:00", "GIT_AUTHOR_DATE": "2024-05-06T12:00:00",
           "GIT_CONFIG_GLOBAL": os.devnull}

    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, env=env)

    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "c")
    git("tag", "v1.0.0")
    git("-c", "user.name=t", "-c", "user.email=t@t", "tag", "-a", "v1.0.1", "-m", "annotated")
    assert tag_dates(str(tmp_path)) == {"v1.0.0": "2024-05-06", "v1.0.1": "2024-05-06"}


def test_minor_zero_names_the_first_release_of_the_tags_minor():
    from kst.select_tags import minor_zero
    assert minor_zero("v0.10.7") == "v0.10.0"
    assert minor_zero("1.16.7") == "1.16.0"
    assert minor_zero("v2.7.0") == "v2.7.0"

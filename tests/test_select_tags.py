from kst.select_tags import evenly_spaced, latest_patch_per_minor


def test_latest_patch_per_minor_ignores_prereleases():
    tags = ["v1.0.0", "v1.0.3", "v1.1.0", "v1.1.0-rc.1", "v1.2.1", "v1.2.10", "1.3.0", "stable-2.0"]
    assert latest_patch_per_minor(tags) == {(1, 0): "v1.0.3", (1, 1): "v1.1.0", (1, 2): "v1.2.10", (1, 3): "1.3.0"}


def test_evenly_spaced_keeps_both_ends():
    assert evenly_spaced(list(range(9)), 5) == [0, 2, 4, 6, 8]


def test_evenly_spaced_short_list_returned_whole():
    assert evenly_spaced([1, 2, 3], 5) == [1, 2, 3]

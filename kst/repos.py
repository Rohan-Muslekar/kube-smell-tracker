"""Load and validate the study's repository selection (data/repos.json)."""
import json

MIN_REPOS = 5
MIN_TAGS = 3


def load_repos(path):
    """Return the included repos in file order; tags are listed oldest to newest."""
    with open(path) as f:
        included = json.load(f)["included"]
    for repo in included:
        if len(repo["tags"]) < MIN_TAGS:
            raise ValueError(f"{repo['name']}: {len(repo['tags'])} tags, need at least {MIN_TAGS}")
    if len(included) < MIN_REPOS:
        raise ValueError(f"{len(included)} repos included, need at least {MIN_REPOS}")
    return included

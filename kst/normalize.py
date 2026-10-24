"""Turn raw kube-linter and kube-score JSON into one Finding per (object, check) report."""
import csv
import re
from dataclasses import dataclass, replace

from kst.inventory import object_namespace


@dataclass(frozen=True)
class Finding:
    repo: str
    version: str
    tool: str
    check: str
    category: str
    kind: str
    namespace: str
    name: str
    file: str


def _relative(path, repo):
    """Strip the local clone prefix (…/work/<repo>/) so files are relative to the repo root."""
    return re.sub(rf"^.*/work/{re.escape(repo)}/", "", path)


def parse_kube_linter(data, repo, version):
    findings = []
    for rep in data.get("Reports") or []:
        obj = rep["Object"]["K8sObject"]
        findings.append(Finding(
            repo=repo, version=version, tool="kube-linter", check=rep["Check"], category="",
            kind=obj["GroupVersionKind"]["Kind"],
            namespace=object_namespace(obj["GroupVersionKind"]["Kind"], obj.get("Namespace")),
            name=obj["Name"], file=_relative(rep["Object"]["Metadata"]["FilePath"], repo)))
    return findings


# kube-score grades seen in our raw output: 10 = ok, 5 = warning, 1 = critical,
# and 0 only on skipped checks. A finding is a non-skipped check graded below 10.
OK_GRADE = 10


def parse_kube_score(data, repo, version):
    findings = []
    for obj in data or []:
        meta = obj.get("object_meta") or {}
        for check in obj.get("checks") or []:
            if check["skipped"] or check["grade"] >= OK_GRADE:
                continue
            findings.append(Finding(
                repo=repo, version=version, tool="kube-score", check=check["check"]["id"], category="",
                kind=obj["type_meta"]["kind"],
                namespace=object_namespace(obj["type_meta"]["kind"], meta.get("namespace")),
                name=meta.get("name") or "", file=_relative(obj.get("file_name") or "", repo)))
    return findings


def load_categories(path):
    with open(path, newline="") as f:
        return {(row["tool"], row["check"]): row["category"] for row in csv.DictReader(f)}


def categorize(findings, cats):
    """Set each finding's category; checks missing from the mapping become "other" and are reported."""
    mapped, unmapped = [], set()
    for f in findings:
        category = cats.get((f.tool, f.check))
        if category is None:
            unmapped.add((f.tool, f.check))
            category = "other"
        mapped.append(replace(f, category=category))
    return mapped, unmapped

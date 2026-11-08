"""Rendering check: lint one repo's kustomize output instead of its unrendered files.

Fallback for the strongest validity threat (flux2's kustomize bases and patches are linted as if
they were complete objects). For each tag it renders every top-level kustomization with
`kubectl kustomize`, keeps the plain manifests that no kustomization uses, and runs the same
inventory, analyzers and validation as scripts/collect.sh. The result is a separate raw/ and data/
under --out, so `python3 -m kst` can track it, and a comparison with the unrendered run.

Usage (from the repo root, with the analyzers in tools/bin and kubectl on PATH):
    python3 scripts/render_check.py flux2 --clone CLONE --out DIR [--field tags_milestone2]
              [--baseline-ref milestone-2-data]

CLONE is a clone of the project that this script may check out (not work/<repo> while
collect.sh is running). Remote resources in a kustomization (flux2 pulls the controller
Deployments from GitHub release assets) need network access.
"""
import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KUSTOMIZATION = ("kustomization.yaml", "kustomization.yml", "Kustomization")
LIST_ITEM = re.compile(r"^\s*-\s+([^\s#:][^\s#]*)\s*(#.*)?$")
PATH_KEY = re.compile(r"^\s*-?\s*path:\s*([^\s#]+)")


def local_refs(kfile):
    """Local files and directories a kustomization refers to (resources, bases, patches, ...).

    Line-based, like kst/inventory.py: any list item or `path:` value that resolves to an
    existing path next to the kustomization counts. Remote URLs never resolve.
    """
    refs = set()
    for line in kfile.read_text(errors="replace").splitlines():
        m = LIST_ITEM.match(line) or PATH_KEY.match(line)
        if not m:
            continue
        target = (kfile.parent / m.group(1).strip("'\"")).resolve()
        if target.exists():
            refs.add(target)
    return refs


def plan(clone, manifest_paths):
    """Return (top-level kustomization dirs, plain files they use) under the manifest paths."""
    kdirs = sorted({p.parent.resolve() for mp in manifest_paths
                    for name in KUSTOMIZATION for p in (clone / mp).rglob(name)})
    referenced, used = set(), set()
    for d in kdirs:
        kfile = next(d / n for n in KUSTOMIZATION if (d / n).exists())
        for ref in local_refs(kfile):
            if ref.is_dir():
                referenced.add(ref)
            else:
                used.add(ref)
        # Plain YAML next to a kustomization belongs to it, even when only a generator uses it.
        used.update(p.resolve() for p in d.iterdir() if p.suffix in (".yaml", ".yml"))
    top = [d for d in kdirs if d not in referenced]
    return top, used


def render(clone, top, dest, log):
    """Render each top-level kustomization to one file under dest; return the written files."""
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for d in top:
        rel = d.relative_to(clone.resolve())
        out = dest / (str(rel).replace("/", "__") + ".yaml")
        result = subprocess.run(["kubectl", "kustomize", str(d)], capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            reason = (result.stderr.strip().splitlines() or ["empty output"])[-1]
            log.append((str(rel), f"render failed: {reason}"))
            continue
        out.write_text(result.stdout)
        written.append(out)
    return written


def collect_tag(repo, tag, clone, manifest_paths, out):
    subprocess.run(["git", "-C", str(clone), "checkout", "-q", "--force", tag], check=True)
    sha = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    date = subprocess.run(["git", "-C", str(clone), "log", "-1", "--format=%cs", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    top, used = plan(clone, manifest_paths)
    log = []
    rendered = render(clone, top, out / "work" / "rendered" / f"{repo}__{tag}", log)

    # Plain manifests no kustomization uses go through the usual filter, as in collect.sh.
    plain = sorted(str(p.relative_to(clone)) for mp in manifest_paths for p in (clone / mp).rglob("*")
                   if p.is_file() and p.suffix in (".yaml", ".yml") and p.resolve() not in used)
    kept = []
    if plain:
        res = subprocess.run([sys.executable, "-P", "-m", "kst.manifests", *plain], cwd=clone,
                             capture_output=True, text=True, env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})
        kept = res.stdout.split()
    files = [str(p) for p in rendered] + kept

    raw = out / "raw"
    for sub in ("kube-linter", "kube-score", "objects"):
        (raw / sub).mkdir(parents=True, exist_ok=True)
    lint_out, score_out = raw / "kube-linter" / f"{repo}__{tag}.json", raw / "kube-score" / f"{repo}__{tag}.json"
    env = {"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}
    inv = subprocess.run([sys.executable, "-P", "-m", "kst.inventory", *files], cwd=clone,
                         capture_output=True, text=True, check=True, env=env)
    (raw / "objects" / f"{repo}__{tag}.tsv").write_text(inv.stdout)
    err = out / "err" / f"{repo}__{tag}"
    err.parent.mkdir(exist_ok=True)
    subprocess.run([str(ROOT / "scripts" / "analyze.sh"), str(lint_out), str(score_out), str(err), *files],
                   cwd=clone, capture_output=True, text=True, check=True)
    for path in (lint_out, score_out):
        path.write_text(path.read_text().replace(f"{clone.resolve()}/", ""))
    valid = all(subprocess.run([sys.executable, "-P", "-m", "kst.validate", str(p)], env=env,
                               capture_output=True).returncode == 0 for p in (lint_out, score_out))
    n_objects = len(inv.stdout.splitlines())
    return dict(repo=repo, tag=tag, commit_sha=sha, commit_date=date, n_yaml_files=len(files),
                valid=int(valid), note=""), dict(tag=tag, top=len(top), rendered=len(rendered),
                                                 plain=len(kept), objects=n_objects, failed=log)


def summarize(instances_csv, repo):
    rows = [r for r in csv.DictReader(instances_csv) if r["repo"] == repo and r["category"] != "other"]
    n = lambda col: sum(int(r[col]) for r in rows)
    first = [r for r in rows if r["presence"][0] == "1"]
    removed, gone = n("removed"), n("removed_object_gone")
    return {
        "instances": len(rows),
        "by_category": dict(sorted(Counter(r["category"] for r in rows).items())),
        "at_first_tag": len(first),
        "survive_to_last": sum(r["presence"][-1] == "1" for r in first),
        "introduced": n("introduced"),
        "introduced_new_object": n("introduced_new_object"),
        "removed": removed,
        "removed_object_gone": gone,
        "removed_object_kept": removed - gone,
        "reappeared": n("reappeared"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo")
    ap.add_argument("--clone", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--field", default="tags_milestone2", help="tag list in data/repos.json")
    ap.add_argument("--baseline-ref", default="milestone-2-data",
                    help="git ref whose out/instances.csv is the unrendered comparison")
    args = ap.parse_args(argv)

    config = json.loads((ROOT / "data" / "repos.json").read_text())
    entry = next(r for r in config["included"] if r["name"] == args.repo)
    tags = entry[args.field]
    clone = args.clone.resolve()
    if args.out.exists():
        shutil.rmtree(args.out)
    shutil.copytree(ROOT / "data", args.out / "data")

    versions, details = [], []
    for tag in tags:
        row, info = collect_tag(args.repo, tag, clone, entry["manifest_paths"], args.out)
        versions.append(row)
        details.append(info)
        print(f"{args.repo}@{tag}: {info['top']} top-level kustomizations, {info['rendered']} rendered, "
              f"{info['plain']} plain files, {info['objects']} objects, valid={row['valid']}", file=sys.stderr)
        for path, reason in info["failed"]:
            print(f"  {path}: {reason}", file=sys.stderr)
    with open(args.out / "data" / "versions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(versions[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(versions)

    subprocess.run([sys.executable, "-m", "kst", "--raw", str(args.out / "raw"), "--data",
                    str(args.out / "data"), "--out", str(args.out / "out")], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)

    baseline = subprocess.run(["git", "-C", str(ROOT), "show", f"{args.baseline_ref}:out/instances.csv"],
                              capture_output=True, text=True, check=True).stdout
    with open(args.out / "out" / "instances.csv", newline="") as f:
        rendered = summarize(f, args.repo)
    report = {"repo": args.repo, "tags": tags, "per_tag": details,
              "unrendered": summarize(io.StringIO(baseline), args.repo), "rendered": rendered}
    (args.out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

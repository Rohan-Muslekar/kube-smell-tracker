#!/usr/bin/env python3
"""Generate every number, table and the figure in the Milestone 3 report from the committed outputs.

Usage: python3 scripts/report_numbers.py --out DIR [--render-rev 1e314b0]
Writes DIR/numbers.tex (one \\newcommand per number in the prose), DIR/tables/*.tex and DIR/survival.pdf
(via scripts/survival.py). Reads out/, data/ and results/category_validation_*; the rendering check
(scripts/render_check.py, PR #15) is read from results/render_check/ at --render-rev with `git show`,
so that commit must be fetched (git fetch origin pull/15/head). The fix-commit dates come from the clones
under work/.
"""
import argparse
import csv
import io
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ART = Path(__file__).resolve().parent.parent
CATS = ("security", "resource", "image", "hygiene")
CAT_NAME = {"security": "Security \\& privilege", "resource": "Resource \\& reliability",
            "image": "Image \\& supply chain", "hygiene": "Hygiene"}
TOOL_NAME = {"kube-linter": "KL", "kube-score": "KS"}
# kube-score stops comparing probes once they use grpc, so these removals are not fixes (spot-check).
ARTIFACT_CHECKS = {("kube-score", "pod-probes-identical")}


def rows(path):
    with open(ART / path, newline="") as f:
        return list(csv.DictReader(f))


def test_count():
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ART,
                         capture_output=True, text=True, check=True).stdout
    return int(re.search(r"(\d+) tests? collected", out).group(1))


def pct(a, b):
    return f"{100 * a / b:.1f}\\%"


def chi_square(units):
    """Chi-square test of independence between category and survival for (category, survived) units.
    df = 3, so the p-value has a closed form (checked against scipy.stats.chi2_contingency without
    correction). Returns (statistic, p, Cramer's V, n)."""
    table = []
    for cat in CATS:
        f = [u for u in units if u[0] == cat]
        s = sum(1 for u in f if u[1])
        table.append((s, len(f) - s))
    n = sum(a + b for a, b in table)
    col = [sum(r[0] for r in table), sum(r[1] for r in table)]
    x = sum((o - (r[0] + r[1]) * c / n) ** 2 / ((r[0] + r[1]) * c / n)
            for r in table for o, c in zip(r, col))
    p = math.erfc(math.sqrt(x / 2)) + math.sqrt(2 * x / math.pi) * math.exp(-x / 2)
    return x, p, math.sqrt(x / n), n


def git_show(rev, path):
    return subprocess.run(["git", "-C", str(ART), "show", f"{rev}:{path}"], capture_output=True,
                          text=True, check=True).stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--render-rev", default="1e314b0")
    args = ap.parse_args(argv)
    OUT = args.out
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    repos = json.loads((ART / "data/repos.json").read_text())
    versions = rows("data/versions.csv")
    instances = rows("out/instances.csv")
    smell = [r for r in instances if r["category"] != "other"]
    findings = rows("out/findings.csv")
    spot = rows("data/spot_check.csv")
    total = lambda k, rs=smell: sum(int(r[k]) for r in rs)

    baseline = total("at_baseline")
    survivors = sum(1 for r in smell if r["presence"][0] == "1" and r["presence"][-1] == "1")
    always = sum(1 for r in smell if set(r["presence"]) == {"1"})
    removed, gone = total("removed"), total("removed_object_gone")
    introduced, new_obj = total("introduced"), total("introduced_new_object")
    fixes_by_repo, artifact_fixes, fix_steps = Counter(), 0, set()
    for r in smell:
        kept = int(r["removed"]) - int(r["removed_object_gone"])
        if (r["tool"], r["check"]) in ARTIFACT_CHECKS:
            artifact_fixes += kept
            continue
        fixes_by_repo[r["repo"]] += kept
        if kept:
            # One fix seen by both tools on the same object, category and step counts once here.
            p = r["presence"]
            fix_steps.update((r["repo"], r["kind"], r["namespace"], r["name"], r["category"], i)
                             for i in range(1, len(p)) if p[i - 1] == "1" and p[i] == "0")
    merged = {(r["repo"], r["kind"], r["namespace"], r["name"], r["category"]) for r in smell}
    per_tool = {t: [r for r in smell if r["tool"] == t] for t in TOOL_NAME}
    base_tool = {t: [r for r in rs if r["presence"][0] == "1"] for t, rs in per_tool.items()}
    surv_tool = {t: sum(1 for r in rs if r["presence"][-1] == "1") for t, rs in base_tool.items()}
    unloaded = defaultdict(set)
    for line in open(ART / "raw/load_failures.tsv"):
        repo, tag, file = line.rstrip("\n").split("\t")
        unloaded[repo].add(file)
    flux_gone = sum(int(r["removed_object_gone"]) for r in smell if r["repo"] == "flux2")
    checks = {(f["tool"], f["check"]) for f in findings}
    cats = rows("data/check_categories.csv")
    confirmed = sum(1 for s in spot if s["confirmed"] == "yes")

    numbers = {
        "nRepos": len(repos["included"]),
        "nExcluded": len(repos["excluded"]),
        "nVersions": len(versions),
        "nValid": sum(1 for v in versions if v["valid"] == "1"),
        "nReports": sum(int(f["dup_count"]) for f in findings),
        "nFindingRows": len(findings),
        "nChecks": len(checks),
        "nMappedChecks": len(cats),
        "nOtherChecks": sum(1 for c in cats if c["category"] == "other"),
        "nInstancesAll": len(instances),
        "nInstances": len(smell),
        "nInstancesKL": len(per_tool["kube-linter"]),
        "nInstancesKS": len(per_tool["kube-score"]),
        "nMerged": len(merged),
        "pSurvivorsKL": pct(surv_tool["kube-linter"], len(base_tool["kube-linter"])),
        "pSurvivorsKS": pct(surv_tool["kube-score"], len(base_tool["kube-score"])),
        "nBaseline": baseline,
        "nSurvivors": survivors,
        "pSurvivors": pct(survivors, baseline),
        "nAlways": always,
        "pAlways": pct(always, len(smell)),
        "nPersisted": total("persisted"),
        "nRemoved": removed,
        "nRemovedGone": gone,
        "pRemovedGone": pct(gone, removed),
        "nFixes": removed - gone,
        "nArtifactFixes": artifact_fixes,
        "nRealFixes": removed - gone - artifact_fixes,
        "nRealFixesMerged": len(fix_steps),
        "nFixRepos": sum(1 for n in fixes_by_repo.values() if n > 0),
        "nFluxGone": flux_gone,
        "nIntroduced": introduced,
        "nIntroducedNew": new_obj,
        "nReappeared": total("reappeared"),
        "nSpot": len(spot),
        "nSpotConfirmed": confirmed,
        "nSkipped": sum(1 for _ in open(ART / "raw/skipped_files.txt")),
        "nUnloadedFiles": sum(len(f) for f in unloaded.values()),
        "nUnloadedRepos": len(unloaded),
        "nTests": test_count(),
    }
    overlap = rows("out/overlap_summary.csv")
    both = sum(int(o["both"]) for o in overlap)
    flagged = sum(int(o["both"]) + int(o["linter_only"]) + int(o["score_only"]) for o in overlap)
    numbers.update(nOverlapBoth=both, nOverlapAll=flagged, pOverlapBoth=pct(both, flagged))
    ov = {o["category"]: o for o in overlap}
    pairs = lambda o: int(o["both"]) + int(o["linter_only"]) + int(o["score_only"])
    numbers.update(nOvHygKL=int(ov["hygiene"]["linter_only"]), nOvHygAll=pairs(ov["hygiene"]),
                   nOvImgKS=int(ov["image"]["score_only"]), nOvImgAll=pairs(ov["image"]))
    rest = [o for o in overlap if o["category"] != "hygiene"]
    both_nh = sum(int(o["both"]) for o in rest)
    flagged_nh = sum(int(o["both"]) + int(o["linter_only"]) + int(o["score_only"]) for o in rest)
    numbers.update(nOverlapBothNoHyg=both_nh, nOverlapAllNoHyg=flagged_nh, pOverlapBothNoHyg=pct(both_nh, flagged_nh))

    for cat in CATS:
        numbers[f"nCat{cat.capitalize()}"] = sum(1 for r in smell if r["category"] == cat)
        numbers[f"pCat{cat.capitalize()}"] = pct(numbers[f"nCat{cat.capitalize()}"], len(smell))
    skipped = Counter(line.rstrip("\n").split("\t")[-1] for line in open(ART / "raw/skipped_files.txt"))
    numbers["nSkippedKustomization"] = skipped.get("kustomization", 0)
    numbers["nSkippedKustomizationFlux"] = sum(1 for line in open(ART / "raw/skipped_files.txt")
                                               if line.startswith("flux2\t") and line.rstrip("\n").endswith("\tkustomization"))

    # Probable renames (track.probable_renames): flagged instances, and how many are real smells.
    if "probable_rename" in instances[0]:
        numbers["nRenameFlagged"] = sum(1 for r in instances if r["probable_rename"] == "1")
        numbers["nRenameFlaggedSmell"] = sum(1 for r in smell if r["probable_rename"] == "1")
    rename = json.loads(subprocess.run([sys.executable, "-m", "kst.rename_report"], cwd=ART,
                                       capture_output=True, text=True, check=True).stdout)
    numbers["nRenameCandidates"] = rename["candidate_object_pair_transitions"]

    # Per-system deletion share: the headline is driven by a few systems.
    by_repo = defaultdict(lambda: [0, 0])
    for r in smell:
        by_repo[r["repo"]][0] += int(r["removed"])
        by_repo[r["repo"]][1] += int(r["removed_object_gone"])
    rest_rem = sum(v[0] for k, v in by_repo.items() if k != "flux2")
    rest_gone = sum(v[1] for k, v in by_repo.items() if k != "flux2")
    numbers.update(nRemovedNoFlux=rest_rem, nRemovedGoneNoFlux=rest_gone, pRemovedGoneNoFlux=pct(rest_gone, rest_rem))
    numbers["nFixReposOnlyFix"] = sum(1 for k, v in by_repo.items() if v[0] and v[1] == 0)

    # RQ3: traced transitions (data/rq3_investigations.csv), smells only.
    other = {c["check"] for c in cats if c["category"] == "other"}
    rq3 = [r for r in rows("data/rq3_investigations.csv") if r["check"] not in other]
    rq3_count = Counter((r["transition"], r["classification"]) for r in rq3)
    intro_existing = total("introduced") - total("introduced_new_object")
    numbers.update(nRQThree=len(rq3), nRQThreeOther=len(rows("data/rq3_investigations.csv")) - len(rq3),
                   nTracedRealFix=rq3_count[("fixed", "real_fix")],
                   nTracedArtifact=rq3_count[("fixed", "analyzer_artifact")],
                   nTracedSideEffect=rq3_count[("introduced", "side_effect_of_fix")],
                   nTracedNewObject=rq3_count[("introduced", "new_object")],
                   nTracedDeleted=rq3_count[("object_deleted", "object_deleted")],
                   nTracedPersisting=rq3_count[("persisted", "persisting_smell")],
                   nIntroExisting=intro_existing)
    real = [r for r in rq3 if r["classification"] == "real_fix"]
    commits = Counter(r["commit_url"].rstrip("/").split("/")[-1][:7] for r in real)
    numbers.update(nRealFixCommits=len(commits), nTopCommitFixes=commits.most_common(1)[0][1],
                   nRealFixTracedRepos=len({r["repo"] for r in real}))
    # Table: the commits behind the real fixes, per system (what changed is read from the diffs).
    change = {"microservices-demo": "a ServiceAccount per service",
              "pipeline": "read-only root filesystem",
              "serving": "probes on the controller and domain-mapping; host anti-affinity",
              "argo-cd": "read-only root filesystem on Redis",
              "kube-prometheus": "\\texttt{runAsGroup}, \\texttt{runAsNonRoot}, no RBAC wildcards, one component each"}
    per_repo = defaultdict(Counter)
    for r in real:
        per_repo[r["repo"]][r["commit_url"].rstrip("/").split("/")[-1][:7]] += 1
    lines = [f"{repo} & {len(c)} & {sum(c.values())} & {change[repo]} \\\\"
             for repo, c in sorted(per_repo.items(), key=lambda kv: -sum(kv[1].values()))]
    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "tables/fixcommits.tex").write_text("\n".join(lines) + "\n")
    top4 = commits.most_common(4)
    numbers.update(nTopFourCommitFixes=sum(n for _, n in top4),
                   nKpFixCommits=len(per_repo.get("kube-prometheus", {})))
    intro_rows = [r for r in rq3 if r["transition"] == "introduced"]
    # Commits behind the introductions on objects that already existed (not new-object introductions).
    existing = {(r["repo"], r["name"], r["check"]) for r in smell
                if int(r["introduced"]) > int(r["introduced_new_object"])}
    numbers["nIntroCommits"] = len({r["commit_url"] for r in intro_rows
                                    if (r["repo"], r["object_name"], r["check"]) in existing})
    numbers["nIntroTraced"] = sum(1 for r in intro_rows if (r["repo"], r["object_name"], r["check"]) in existing)
    numbers["nTracedNewObjectAll"] = rq3_count[("introduced", "new_object")]
    # Traced introductions on objects that did not exist before (the rest are among nIntroTraced).
    numbers["nIntroNewTraced"] = len(intro_rows) - numbers["nIntroTraced"]
    rq3_lines = [
        ("Fix (object kept)", "Real fix", rq3_count[("fixed", "real_fix")]),
        ("", "Analyzer artifact", rq3_count[("fixed", "analyzer_artifact")]),
        ("Introduction", "Side effect of another fix", rq3_count[("introduced", "side_effect_of_fix")]),
        ("", "New object or new Service", rq3_count[("introduced", "new_object")]),
        ("Removal", "Object deleted", rq3_count[("object_deleted", "object_deleted")]),
        ("Persisted", "Unchanged smell", rq3_count[("persisted", "persisting_smell")]),
    ]
    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "tables/rq3.tex").write_text("".join(f"{a} & {b} & {n} \\\\\n" for a, b, n in rq3_lines))

    # Rendering check (scripts/render_check.py, PR #15): flux2 and microservices-demo, the only
    # projects with kustomizations, rendered at every tag. render-check/<repo>/ holds the
    # comparison.json and the repo's rows of the rendered out/instances.csv.
    rc = {repo: json.loads(git_show(args.render_rev, f"results/render_check/{repo}/comparison.json"))
          for repo in ("flux2", "microservices-demo")}
    rendered_rows = [r for repo in rc for r in csv.DictReader(io.StringIO(git_show(args.render_rev, f"results/render_check/{repo}/instances.csv")))
                     if r["category"] != "other"]
    mixed = [r for r in smell if r["repo"] not in rc] + rendered_rows

    def life(rs):
        first = [r for r in rs if r["presence"][0] == "1"]
        surv = sum(1 for r in first if r["presence"][-1] == "1")
        rem, gone_ = sum(int(r["removed"]) for r in rs), sum(int(r["removed_object_gone"]) for r in rs)
        art = sum(int(r["removed"]) - int(r["removed_object_gone"]) for r in rs if (r["tool"], r["check"]) in ARTIFACT_CHECKS)
        return dict(inst=len(rs), first=len(first), surv=surv, ps=pct(surv, len(first)), rem=rem, gone=gone_,
                    pg=pct(gone_, rem), fix=rem - gone_ - art, reapp=sum(int(r["reappeared"]) for r in rs),
                    intro=sum(int(r["introduced"]) for r in rs), intro_new=sum(int(r["introduced_new_object"]) for r in rs))
    st, rd = life(smell), life(mixed)
    fu, fr = rc["flux2"]["unrendered"], rc["flux2"]["rendered"]
    mu, mr = rc["microservices-demo"]["unrendered"], rc["microservices-demo"]["rendered"]
    numbers.update(nRcInstU=fu["instances"], nRcInstR=fr["instances"], nRcRemR=fr["removed"],
                   nRcHygU=fu["by_category"].get("hygiene", 0), nRcTop=rc["flux2"]["per_tag"][0]["top"],
                   nRcTags=len(rc["flux2"]["tags"]) + len(rc["microservices-demo"]["tags"]),
                   nRcMsdDrop=mu["instances"] - mr["instances"],
                   pRcSurvAll=rd["ps"], pRcGoneAll=rd["pg"], nRcFixAll=rd["fix"], nRcReappAll=rd["reapp"])
    # Object-level view under rendering: deleted objects and object-category pairs, deleted vs fixed,
    # and how many rendered real fixes come from the four commits with the most stored fixes.
    def object_level(rs):
        gone_o, gone_p, fix_p, fix_keys = set(), set(), set(), []
        for r in rs:
            obj = (r["repo"], r["kind"], r["namespace"], r["name"])
            for i in range(1, len(r["presence"])):
                if r["presence"][i - 1:i + 1] == "10":
                    if int(r["removed_object_gone"]):
                        gone_o.add(obj)
                        gone_p.add((*obj, r["category"]))
                    elif (r["tool"], r["check"]) not in ARTIFACT_CHECKS:
                        fix_p.add((*obj, r["category"]))
                        fix_keys.append((*obj, r["check"]))
        return gone_o, gone_p, fix_p, fix_keys
    sha_of = {(r["repo"], r["object_kind"], r["namespace"], r["object_name"], r["check"]):
              r["commit_url"].rstrip("/").split("/")[-1][:7] for r in real}
    top4_shas = {sha for sha, _ in top4}
    go_r, gp_r, fp_r, fk_r = object_level(mixed)
    assert all(k in sha_of for k in fk_r), [k for k in fk_r if k not in sha_of]
    numbers.update(nRcGoneObjects=len(go_r), nRcGonePairs=len(gp_r), nRcFixPairs=len(fp_r),
                   nRcTopFour=sum(1 for k in fk_r if sha_of[k] in top4_shas),
                   nRcIntroAll=rd["intro"], nRcIntroNewAll=rd["intro_new"])
    cols = [life([r for r in smell if r["repo"] == "flux2"]), life([r for r in rendered_rows if r["repo"] == "flux2"]),
            life([r for r in smell if r["repo"] == "microservices-demo"]),
            life([r for r in rendered_rows if r["repo"] == "microservices-demo"]), st, rd]
    rc_rows = [("Smell instances", *[c["inst"] for c in cols]),
               ("Surv. to last tag", *[c["ps"] for c in cols]),
               ("Removed", *[c["rem"] for c in cols]),
               ("Deleted share", *[c["pg"] if c["rem"] else "--" for c in cols]),
               ("Real fixes", *[c["fix"] for c in cols]),
               ("Reappeared", *[c["reapp"] for c in cols])]
    (OUT / "tables/render.tex").write_text("".join(" & ".join(str(x) for x in row) + " \\\\\n" for row in rc_rows))

    # The figure comes from the artifact's own script, so the report and the repo show the same plot.
    subprocess.run([sys.executable, str(ART / "scripts/survival.py"), "--out", str(OUT / "figure")],
                   cwd=ART, check=True, stdout=subprocess.DEVNULL)
    (OUT / "survival.pdf").write_bytes((OUT / "figure/survival.pdf").read_bytes())

    with open(OUT / "numbers.tex", "w") as f:
        f.write("% Generated by scripts/report_numbers.py from the artifact outputs. Do not edit.\n")
        for k, v in numbers.items():
            v = f"{v:,}".replace(",", "{,}") if isinstance(v, int) else v
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

    (OUT / "tables").mkdir(exist_ok=True)

    # Table: systems with per-system results
    # Years: the x.y.0 release of each tag's minor (data/minor_dates.csv), as in Fig. 1 and the ages.
    year = {(m["repo"], m["tag"]): m["minor_first_date"][:4] for m in rows("data/minor_dates.csv")}
    lines = []
    for r in repos["included"]:
        name = r["name"]
        t0, t1 = r["tags"][0], r["tags"][-1]
        path = r["manifest_paths"][0].replace("_", "\\_")
        rs = [x for x in smell if x["repo"] == name]
        first = [x for x in rs if x["presence"][0] == "1"]
        surv = sum(1 for x in first if x["presence"][-1] == "1")
        rem, gone_r = sum(int(x["removed"]) for x in rs), sum(int(x["removed_object_gone"]) for x in rs)
        intro, new_r = sum(int(x["introduced"]) for x in rs), sum(int(x["introduced_new_object"]) for x in rs)
        lines.append(f"{name} & \\texttt{{{path}}} & {len(r['tags'])} & {t0}--{t1} "
                     f"({year[(name, t0)]}--{year[(name, t1)]}) & {len(rs)} & "
                     f"{pct(surv, len(first)) if first else '--'} & {rem} ({gone_r}) & {intro} ({new_r}) \\\\")
    (OUT / "tables/systems.tex").write_text("\n".join(lines) + "\n")

    # Table: transitions by tool and category
    summary = {(r["tool"], r["category"]): r for r in rows("out/transitions_summary.csv")}
    n_inst = Counter((r["tool"], r["category"]) for r in smell)
    lines = []
    for cat in CATS:
        for tool in ("kube-linter", "kube-score"):
            s = summary.get((tool, cat))
            if not s:
                continue
            lines.append(f"{CAT_NAME[cat]} & {TOOL_NAME[tool]} & {n_inst[(tool, cat)]} & {s['at_baseline']} & "
                         f"{s['persisted']} & {s['introduced']} ({s['introduced_new_object']}) & "
                         f"{s['removed']} ({s['removed_object_gone']}) & {s['reappeared']} \\\\")
    lines.append("\\midrule")
    lines.append(f"\\textbf{{Total}} & & {len(smell)} & {baseline} & {total('persisted')} & "
                 f"{introduced} ({new_obj}) & {removed} ({gone}) & {total('reappeared')} \\\\")
    (OUT / "tables/transitions.tex").write_text("\n".join(lines) + "\n")

    # Table: survival, removals and introductions per category (RQ2), both tools together.
    lines = []
    for cat in CATS:
        rs = [r for r in smell if r["category"] == cat]
        first = [r for r in rs if r["presence"][0] == "1"]
        surv = sum(1 for r in first if r["presence"][-1] == "1")
        rem, gone_c = sum(int(r["removed"]) for r in rs), sum(int(r["removed_object_gone"]) for r in rs)
        art = sum(int(r["removed"]) - int(r["removed_object_gone"]) for r in rs
                  if (r["tool"], r["check"]) in ARTIFACT_CHECKS)
        lines.append(f"{CAT_NAME[cat]} & {len(first)} & {pct(surv, len(first))} & {rem} ({gone_c}) & "
                     f"{rem - gone_c - art} & {sum(int(r['introduced']) for r in rs)} "
                     f"({sum(int(r['introduced_new_object']) for r in rs)}) \\\\")
        numbers[f"pSurv{cat.capitalize()}"] = pct(surv, len(first))
        numbers[f"nRealFix{cat.capitalize()}"] = rem - gone_c - art
    (OUT / "tables/categories.tex").write_text("\n".join(lines) + "\n")

    # Chi-square test of independence: category x (survived to the last tag or not), first-tag
    # instances. df = 3, so the p-value has a closed form (no scipy needed; checked against
    # scipy.stats.chi2_contingency without correction). Three units: instances, instances outside
    # flux2, and merged (system, kind, namespace, name, category) pairs, which removes the dependence
    # between several instances on one object.
    fmt_p = lambda p: "$p<0.001$" if p < 0.001 else f"$p={p:.2f}$"
    first_units = lambda rs: [(r["category"], r["presence"][-1] == "1") for r in rs if r["presence"][0] == "1"]
    pairs_first = {}
    for r in smell:
        if r["presence"][0] == "1":
            k = (r["repo"], r["kind"], r["namespace"], r["name"], r["category"])
            pairs_first[k] = pairs_first.get(k, False) or r["presence"][-1] == "1"
    # A pair can also count as surviving only when all its first-tag instances survive.
    pairs_all = {}
    for r in smell:
        if r["presence"][0] == "1":
            k = (r["repo"], r["kind"], r["namespace"], r["name"], r["category"])
            pairs_all[k] = pairs_all.get(k, True) and r["presence"][-1] == "1"
    for tag, units in (("", first_units(smell)),
                       ("NoFlux", first_units([r for r in smell if r["repo"] != "flux2"])),
                       ("Obj", [(k[4], s) for k, s in pairs_first.items()]),
                       ("ObjAll", [(k[4], s) for k, s in pairs_all.items()])):
        x, p, v, n = chi_square(units)
        numbers.update({f"xCat{tag}": f"{x:.1f}", f"pCat{tag}Test": fmt_p(p),
                        f"vCat{tag}": f"{v:.2f}", f"nCat{tag}Units": n})

    # Table: the most frequent checks (RQ1), with the systems they occur in and their survival.
    top = Counter((r["tool"], r["check"], r["category"]) for r in smell).most_common(8)
    lines = []
    for (tool, check, cat), n in top:
        rs = [r for r in smell if (r["tool"], r["check"]) == (tool, check)]
        first = [r for r in rs if r["presence"][0] == "1"]
        surv = sum(1 for r in first if r["presence"][-1] == "1")
        lines.append(f"\\texttt{{{check.replace('-', '-\\allowbreak{}') if len(check) > 34 else check}}} & {TOOL_NAME[tool]} & {n} & "
                     f"{len({r['repo'] for r in rs})} & {pct(surv, len(first))} \\\\")
    (OUT / "tables/topchecks.tex").write_text("\n".join(lines) + "\n")
    numbers["nTopEightShare"] = pct(sum(n for _, n in top), len(smell))
    by_check = Counter(r["check"] for r in smell)
    numbers.update(nImgPull=by_check["container-image-pull-policy"],
                   nImgOwn=sum(1 for r in smell if r["category"] == "image") - by_check["container-image-pull-policy"],
                   nHygNs=by_check["use-namespace"])

    # Smell age: years from the first release where an instance is present to the release where it
    # is removed (real fixes vs deletions), and the age of the instances still present at the last tag.
    # A study tag is the latest patch of its minor and can be dated years after the minor shipped,
    # so each tag is dated by its minor's x.y.0 (data/minor_dates.csv, scripts/minor_dates.py).
    minor_date = {(m["repo"], m["tag"]): date.fromisoformat(m["minor_first_date"]) for m in rows("data/minor_dates.csv")}
    when = defaultdict(list)
    for v in versions:
        if v["valid"] == "1":
            when[v["repo"]].append(minor_date[(v["repo"], v["tag"])])
    tag_list = defaultdict(list)
    for v in versions:
        if v["valid"] == "1":
            tag_list[v["repo"]].append(v["tag"])
    ages = defaultdict(list)
    fix_events = []          # (repo, kind, namespace, name, check, category, step) of every real fix
    gone_objects, fix_objects, gone_pairs = set(), set(), set()
    for r in smell:
        p, d = r["presence"], when[r["repo"]]
        first = p.index("1")
        obj = (r["repo"], r["kind"], r["namespace"], r["name"])
        for i in range(1, len(p)):
            if p[i - 1] == "1" and p[i] == "0":
                if int(r["removed_object_gone"]):
                    kind = "gone"
                    gone_objects.add(obj)
                    gone_pairs.add((*obj, r["category"]))
                elif (r["tool"], r["check"]) in ARTIFACT_CHECKS:
                    kind = "artifact"
                else:
                    kind = "fix"
                    fix_objects.add(obj)
                    fix_events.append((*obj, r["check"], r["category"], i, first == 0))
                ages[kind].append((d[i] - d[first]).days / 365.25)
        if p[-1] == "1":
            ages["alive"].append((d[-1] - d[first]).days / 365.25)
    yrs = lambda xs: f"{statistics.median(xs):.1f}"
    numbers.update(yFixMedian=yrs(ages["fix"]), yFixMin=f"{min(ages['fix']):.1f}", yFixMax=f"{max(ages['fix']):.1f}",
                   yGoneMedian=yrs(ages["gone"]), yAliveMedian=yrs(ages["alive"]), nAlive=len(ages["alive"]),
                   nFixWithinYear=sum(1 for a in ages["fix"] if a <= 1),
                   nFixAtBaseline=sum(1 for e in fix_events if e[-1]),
                   nGoneObjects=len(gone_objects), nFixObjects=len(fix_objects),
                   nGonePairs=len(gone_pairs), nFixPairs=len({(*e[:4], e[5]) for e in fix_events}))
    # Fixes made before a system's last tag are the only ones a later tag could show coming back.
    last = {repo: len(t) - 1 for repo, t in tag_list.items()}
    early = [e for e in fix_events if e[6] < last[e[0]]]
    numbers.update(nFixBeforeLast=len(early), nFixBeforeLastRepos=len({e[0] for e in early}))
    # Cross-check of the fix age: date each real fix by its traced commit (git, clones under work/)
    # instead of by the release that first lacks the smell.
    rq3_all = rows("data/rq3_investigations.csv")
    commit_of = {(r["repo"], r["object_kind"], r["namespace"], r["object_name"], r["check"]): r["commit_url"]
                 for r in rq3_all if r["classification"] == "real_fix"}
    commit_age = []
    for repo, kind, ns, name, check, _cat, i, _base in fix_events:
        sha = commit_of[(repo, kind, ns, name, check)].rstrip("/").split("/")[-1]
        day = subprocess.run(["git", "-C", str(ART / "work" / repo), "log", "-1", "--format=%cs", sha],
                             capture_output=True, text=True, check=True).stdout.strip()
        first = next(r for r in smell if (r["repo"], r["kind"], r["namespace"], r["name"], r["check"]) ==
                     (repo, kind, ns, name, check))["presence"].index("1")
        commit_age.append((date.fromisoformat(day) - when[repo][first]).days / 365.25)
    numbers.update(yFixCommitMedian=yrs(commit_age))
    # Fixes per traced commit: how many commits remove a single smell.
    per_commit = Counter(commit_of[e[:5]].rstrip("/").split("/")[-1][:7] for e in fix_events)
    numbers.update(nSingleFixCommits=sum(1 for n in per_commit.values() if n == 1))
    # One commit gives a third of the fixes, so also give the fix age with one value per commit
    # (the median age of the fixes it makes).
    by_commit = defaultdict(list)
    for e, age in zip(fix_events, ages["fix"]):
        by_commit[commit_of[e[:5]].rstrip("/").split("/")[-1][:7]].append(age)
    numbers.update(yFixPerCommitMedian=yrs([statistics.median(a) for a in by_commit.values()]))
    # Context for the headline numbers: excluded `other` instances, files kube-linter cannot load,
    # survival without istio (229 of the first-tag instances, all surviving) and per system,
    # removals that a later tag could show coming back, and how security and image smells are lost.
    other = [r for r in instances if r["category"] == "other"]
    other_first = [r for r in other if r["presence"][0] == "1"]
    no_istio = [r for r in smell if r["presence"][0] == "1" and r["repo"] != "istio"]
    per_sys = defaultdict(list)
    for r in smell:
        if r["presence"][0] == "1":
            per_sys[r["repo"]].append(r["presence"][-1] == "1")
    lost = lambda cat: [r for r in smell if r["category"] == cat and r["presence"][0] == "1" and r["presence"][-1] == "0"]
    sec_lost, img_lost = lost("security"), lost("image")
    with open(ART / "raw/load_failures.tsv", newline="") as f:
        load_fail = {tuple(line[:1] + line[2:3]) for line in csv.reader(f, delimiter="\t")}
    numbers.update(nOther=len(other), nAllInst=len(instances), pOther=pct(len(other), len(instances)),
                   pOtherSurv=pct(sum(1 for r in other_first if r["presence"][-1] == "1"), len(other_first)),
                   nLoadFailFiles=len(load_fail), nBaselineIstio=len(per_sys["istio"]),
                   pSurvNoIstio=pct(sum(1 for r in no_istio if r["presence"][-1] == "1"), len(no_istio)),
                   pSurvMedianSys=f"{statistics.median(100 * sum(v) / len(v) for v in per_sys.values()):.1f}\\%",
                   nRemovedLater=sum(1 for r in smell for i in range(1, len(r["presence"]) - 1)
                                     if r["presence"][i - 1:i + 1] == "10"),
                   nSecLost=len(sec_lost), nSecLostGone=sum(1 for r in sec_lost if int(r["removed_object_gone"])),
                   nSecLostFix=sum(1 for r in sec_lost if not int(r["removed_object_gone"])),
                   nImgLost=len(img_lost))
    assert all(int(r["removed_object_gone"]) for r in img_lost)
    # The stored and rendered flux2 removals all happen at one tag.
    flux_steps = {tag_list["flux2"][i] for r in smell if r["repo"] == "flux2"
                  for i in range(1, len(r["presence"])) if r["presence"][i - 1:i + 1] == "10"}
    assert len(flux_steps) == 1, flux_steps
    numbers.update(tFluxRemoval=flux_steps.pop())
    # Category check: blind LLM rater vs the map (results/category_validation_*, from kst.category_validation calculate),
    # and the main results with the rater's categories for the checks where it differs.
    # Rater 1 (Ankit's returned sheet, AI-assisted per its rater field) is handled the same way.
    def with_sheet(sheet):
        cats = {(r["tool"], r["check"]): r["category"].strip().lower()
                for r in rows(sheet)}
        alt = [dict(r, category=cats[(r["tool"], r["check"])]) for r in instances]
        alt = [r for r in alt if r["category"] != "other"]
        first = [r for r in alt if r["presence"][0] == "1"]
        rem = sum(int(r["removed"]) for r in alt)
        gone = sum(int(r["removed_object_gone"]) for r in alt)
        return (len(alt), f"{100 * sum(r['presence'][-1] == '1' for r in first) / len(first):.1f}",
                f"{100 * gone / rem:.1f}", sum(int(r["reappeared"]) for r in alt),
                pct(sum(1 for r in alt if r["category"] == "resource"), len(alt)))
    agree = json.loads((ART / "results/category_validation_llm/category_agreement.json").read_text())
    r1 = json.loads((ART / "results/category_validation_rater1/category_agreement.json").read_text())
    r1_llm = json.loads((ART / "results/category_validation_rater1_vs_llm/category_agreement.json").read_text())
    numbers.update(nLlmAgree=agree["agreements"], nLlmChecks=agree["checks"],
                   kLlm=f"{agree['cohens_kappa']:.2f}", nLlmDiffer=agree["disagreements"],
                   nROneAgree=r1["agreements"], kROne=f"{r1['cohens_kappa']:.2f}", nROneDiffer=r1["disagreements"],
                   nROneLlmAgree=r1_llm["agreements"], kROneLlm=f"{r1_llm['cohens_kappa']:.2f}")
    numbers.update(zip(("nAltInst", "pAltSurv", "pAltGone", "nAltReapp", "pAltResource"), with_sheet("data/category_validation/llm_rater.csv")))
    numbers.update(zip(("nROneInst", "pROneSurv", "pROneGone", "nROneReapp", "pROneResource"), with_sheet("data/category_validation/category_rater_1.csv")))
    with open(OUT / "numbers.tex", "a") as f:
        for k in ("nLlmAgree", "nLlmChecks", "kLlm", "nLlmDiffer", "nAltInst", "pAltSurv", "pAltGone", "nAltReapp",
                  "nROneAgree", "kROne", "nROneDiffer", "nROneLlmAgree", "kROneLlm",
                  "nROneInst", "pROneSurv", "pROneGone", "nROneReapp", "pAltResource", "pROneResource",
                  "nFixAtBaseline", "nGoneObjects", "nFixObjects", "nFixBeforeLast", "nFixBeforeLastRepos",
                  "yFixCommitMedian", "nSingleFixCommits", "yFixPerCommitMedian", "nOther", "nAllInst", "pOther",
                  "pOtherSurv", "nLoadFailFiles", "nBaselineIstio", "pSurvNoIstio", "pSurvMedianSys", "nRemovedLater", "nSecLost",
                  "nSecLostGone", "nSecLostFix", "nImgLost", "tFluxRemoval", "nGonePairs", "nFixPairs"):
            f.write(f"\\newcommand{{\\{k}}}{{{numbers[k]}}}\n")
        for k in ("xCat", "pCatTest", "vCat", "nCatUnits", "xCatNoFlux", "pCatNoFluxTest", "vCatNoFlux",
                  "nCatNoFluxUnits", "xCatObj", "pCatObjTest", "vCatObj", "nCatObjUnits", "xCatObjAll", "pCatObjAllTest", "vCatObjAll", "pSurvSecurity", "pSurvResource", "pSurvImage", "pSurvHygiene", "nRealFixSecurity",
                  "nRealFixResource", "nRealFixImage", "nRealFixHygiene", "nTopEightShare", "yFixMedian",
                  "yFixMin", "yFixMax", "yGoneMedian", "yAliveMedian", "nAlive", "nFixWithinYear",
                  "nImgPull", "nImgOwn", "nHygNs"):
            f.write(f"\\newcommand{{\\{k}}}{{{numbers[k]}}}\n")

    # Table: overlap
    lines = [f"{CAT_NAME[o['category']]} & {o['linter_only']} & {o['score_only']} & {o['both']} \\\\"
             for o in sorted(overlap, key=lambda o: CATS.index(o["category"]))]
    (OUT / "tables/overlap.tex").write_text("\n".join(lines) + "\n")

    # Table: spot-check
    by = defaultdict(Counter)
    for s in spot:
        by[s["stratum"]][s["cause"]] += 1
    lines = [f"{stratum} & " + "; ".join(f"{cause} ({n})" for cause, n in causes.most_common()) + " \\\\"
             for stratum, causes in by.items()]
    (OUT / "tables/spotcheck.tex").write_text("\n".join(lines) + "\n")

    print(f"wrote numbers.tex ({len(numbers)} values) and tables/ from {ART}")


if __name__ == "__main__":
    main()

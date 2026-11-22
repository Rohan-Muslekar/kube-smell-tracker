# Milestone 4: commands behind every number

Run from the repository root. `milestone-3-data` is the stored-manifest data used up to
Milestone 3; `master` holds the rendered data from the Nov 23 integration run.

## E1: rendered integration run

```bash
./tools/install.sh            # kube-linter v0.8.3, kube-score v1.20.0, kubectl v1.36.2
make all                      # RENDER=1 is the default: collect every tag, then python3 -m kst
python3 scripts/check_rq3.py  # 74 traced transitions: 67 checked on rendered out/, 0 problems;
                              # 7 name stored-only objects (flux2 patch fragments, loadgenerator)
python3 scripts/report_numbers.py --out <dir>          # every number and table, rendered data
python3 scripts/report_numbers.py --headlines-only --out results/rendered/baseline
python3 scripts/report_numbers.py --exclude istio --out results/rendered/without_istio
python3 scripts/report_numbers.py --exclude flux2 --out results/rendered/without_flux2
```

## Stored vs rendered, per system

```bash
git worktree add /tmp/kst-stored milestone-3-data
python3 scripts/compare_render.py --stored /tmp/kst-stored --rendered . \
  --out results/render_comparison.csv
```

## E2: rendered transitions (validation only, writes nothing)

```bash
python3 -c "import sys; sys.path.insert(0, 'scripts'); import complete_rq3_rendered as c
from pathlib import Path
_, todo = c.load_csv(Path('data/rq3_rendered_todo.csv'))
_, orig = c.load_csv(Path('data/rq3_investigations.csv'))
_, vers = c.load_csv(Path('data/versions.csv'))
_, inst = c.load_csv(Path('out/instances.csv'))
print(len(c.prepare_additions(c.build_draft(todo), inst, vers, orig, Path('work/flux2'))), 'rows validate')"
```

## E3: category ratings so far

See `results/category_validation_status.md` (rater 2 against the map and against the LLM sheet).

## E5: survival curves and sensitivity

`python3 -m kst` writes `out/km_by_*.csv` (event: any removal) and `out/km_fix_by_*.csv`
(event: a fix; deletions and the gRPC-probe artifact censored).

## Confounder checks added in Milestone 4

Analyzer ignore annotations at every tag (accepted-defaults alternative):

```bash
python3 - <<'EOF'
import json, subprocess
pat = r'ignore-check\.kube-linter\.io|kube-score/ignore|kube-linter\.io/ignore'
for r in json.load(open('data/repos.json'))['included']:
    n = sum(bool(subprocess.run(['git', '-C', f"work/{r['name']}", 'grep', '-q', '-E', pat, t, '--',
                                 *r['manifest_paths']]).returncode == 0) for t in r['tags'])
    print(r['name'], n, 'of', len(r['tags']), 'tags with ignore annotations')
EOF
```

istio variant files (instances keyed by file as well, so a fix in one variant would show):

```bash
python3 - <<'EOF'
import csv
from collections import defaultdict
tags = [r['tag'] for r in csv.DictReader(open('data/versions.csv'))
        if r['repo'] == 'istio' and r['valid'] == '1']
seen = defaultdict(set)
for r in csv.DictReader(open('out/findings.csv')):
    if r['repo'] == 'istio' and r['category'] != 'other':
        seen[(r['tool'], r['kind'], r['namespace'], r['name'], r['check'], r['file'])].add(r['version'])
p = [''.join('1' if t in v else '0' for t in tags) for v in seen.values()]
print(len(p), 'file-level instances;', sum(x[0] == '1' for x in p), 'at the first tag;',
      sum(x[0] == x[-1] == '1' for x in p), 'survive;', sum(x.count('10') for x in p), 'removals')
EOF
```

## Report macros

The Milestone 4 report's `numbers.tex` is `report_numbers.py --out` at tag `milestone-3-data`
(stored manifests); `rnumbers.tex` is the same command at the integration commit, with every
macro prefixed by `R`:

```bash
python3 scripts/report_numbers.py --out /tmp/rn && sed 's/\\newcommand{\\/\\newcommand{\\R/' /tmp/rn/numbers.tex > rnumbers.tex
```

istio objects that sit in more than one Bookinfo variant file (14 of 33, over all tags):

```bash
python3 - <<'EOF'
import csv, glob
from collections import defaultdict
files = defaultdict(set)
for p in glob.glob('raw/objects/istio__*.tsv'):
    for row in csv.reader(open(p), delimiter='\t'):
        files[tuple(row[:3])].add(row[3])
print(sum(len(f) > 1 for f in files.values()), 'of', len(files), 'objects sit in more than one file')
EOF
```

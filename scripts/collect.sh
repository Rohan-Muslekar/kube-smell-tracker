#!/usr/bin/env bash
# Run kube-linter and kube-score over every included repo at every selected tag.
# Usage: ./scripts/collect.sh [repo-name]   (no argument = all repos in data/repos.json)
#
# Writes raw/kube-linter/<repo>__<tag>.json, raw/kube-score/<repo>__<tag>.json, raw/objects/<repo>__<tag>.tsv,
# data/versions.csv (one row per repo and tag) and raw/skipped_files.txt.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPOS="$ROOT/data/repos.json"
LINTER="$ROOT/tools/bin/kube-linter"
SCORER="$ROOT/tools/bin/kube-score"
WORK="$ROOT/work"
VERSIONS="$ROOT/data/versions.csv"
SKIPPED="$ROOT/raw/skipped_files.txt"
ONLY="${1:-}"

mkdir -p "$WORK" "$ROOT/raw/kube-linter" "$ROOT/raw/kube-score" "$ROOT/raw/objects"
[ -f "$VERSIONS" ] || echo "repo,tag,commit_sha,commit_date,n_yaml_files,valid,note" > "$VERSIONS"
[ -f "$SKIPPED" ] || : > "$SKIPPED"

# Drop earlier rows for the repos being re-collected, so reruns never duplicate rows.
forget() {
  local name="$1" tmp
  tmp="$(mktemp)"
  awk -F, -v r="$name" 'NR == 1 || $1 != r' "$VERSIONS" > "$tmp" && mv "$tmp" "$VERSIONS"
  tmp="$(mktemp)"
  awk -F'\t' -v r="$name" '$1 != r' "$SKIPPED" > "$tmp" && mv "$tmp" "$SKIPPED"
}

# Print the Kubernetes manifests under the given paths, one per line, relative to the clone.
# The filter lives in kst/manifests.py; skipped files go to $SKIPPED with the reason.
# -P keeps the cloned repo (the current directory) off Python's import path.
manifests() {
  local name="$1" tag="$2"; shift 2
  find "$@" -type f \( -name '*.yaml' -o -name '*.yml' \) 2>/dev/null | sort \
    | xargs -r env PYTHONPATH="$ROOT" python3 -P -m kst.manifests \
        2> >(awk -v r="$name" -v t="$tag" '{print r "\t" t "\t" $0}' >> "$SKIPPED")
}

jq -c '.included[]' "$REPOS" | while IFS= read -r repo; do
  name="$(jq -r .name <<<"$repo")"
  [ -n "$ONLY" ] && [ "$ONLY" != "$name" ] && continue
  url="$(jq -r .url <<<"$repo")"
  mapfile -t paths < <(jq -r '.manifest_paths[]' <<<"$repo")
  mapfile -t tags < <(jq -r '.tags[]' <<<"$repo")
  clone="$WORK/$name"

  [ -d "$clone/.git" ] || git clone -q --filter=blob:none --no-checkout "$url" "$clone"
  forget "$name"

  for tag in "${tags[@]}"; do
    git -C "$clone" checkout -q --force "$tag"
    sha="$(git -C "$clone" rev-parse HEAD)"
    date="$(git -C "$clone" log -1 --format=%cs HEAD)"
    lint_out="$ROOT/raw/kube-linter/${name}__${tag}.json"
    score_out="$ROOT/raw/kube-score/${name}__${tag}.json"

    mapfile -t files < <(cd "$clone" && manifests "$name" "$tag" "${paths[@]}")
    if [ "${#files[@]}" -eq 0 ]; then
      echo "$name,$tag,$sha,$date,0,0,no manifests" >> "$VERSIONS"
      echo "$name@$tag: no manifests"
      continue
    fi

    # Object inventory (kind, namespace, name, file) used to tell fixed smells from deleted objects.
    (cd "$clone" && PYTHONPATH="$ROOT" python3 -P -m kst.inventory "${files[@]}") \
      > "$ROOT/raw/objects/${name}__${tag}.tsv"

    # Both tools exit non-zero when they find problems, so the exit code is ignored.
    # A run counts as failed only when stdout is not valid JSON.
    (cd "$clone" && "$LINTER" lint "${files[@]}" --add-all-built-in --format json) \
      > "$lint_out" 2> "$WORK/${name}__${tag}.linter.err" || true
    (cd "$clone" && "$SCORER" score "${files[@]}" --output-format json) \
      > "$score_out" 2> "$WORK/${name}__${tag}.score.err" || true

    # Both tools print absolute paths; keep raw output machine-independent (paths relative to the repo).
    sed -i "s|$clone/||g" "$lint_out" "$score_out"

    valid=1; note=""
    if ! jq empty "$lint_out" 2>/dev/null; then
      valid=0; note="kube-linter: $(head -1 "$WORK/${name}__${tag}.linter.err" | tr ',' ';')"
    elif ! jq empty "$score_out" 2>/dev/null; then
      valid=0; note="kube-score: $(head -1 "$WORK/${name}__${tag}.score.err" | tr ',' ';')"
    fi
    echo "$name,$tag,$sha,$date,${#files[@]},$valid,$note" >> "$VERSIONS"
    echo "$name@$tag: ${#files[@]} files, valid=$valid $note"
  done
done

#!/usr/bin/env bash
# Walk all Git repositories under the AOHP project tree (by finding .git files/dirs on disk) and check:
#   1) Uncommitted changes (unstaged, staged, and untracked)
#   2) Whether the current branch has unpushed commits relative to the configured @{upstream}
#      (skipped when no upstream or tracking branch is set)
# Usage: check_dirty_repos.sh [AOHP_ROOT]
# When no argument is given, defaults to the parent of the script directory (the AOHP repo root).
# Parallelism is controlled by CHECK_DIRTY_JOBS; defaults to the local CPU count (same as nproc).
# Example 1 (default): ./scripts/check_dirty_repos.sh
# Example 2 (custom):   CHECK_DIRTY_JOBS=16 ./scripts/check_dirty_repos.sh /path/to/AOHP

set -euo pipefail

export GIT_OPTIONAL_LOCKS=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AOHP_ROOT="$(cd "${1:-$SCRIPT_DIR/..}" && pwd)"
JOBS="${CHECK_DIRTY_JOBS:-$(nproc)}"
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT
mkdir -p "$WORKDIR/out"

# Collect all Git repo roots (parent of each .git), sorted by relative path for stable output
mapfile -t REPOS < <(
  find "$AOHP_ROOT" -name .git 2>/dev/null \
    | while IFS= read -r g || [[ -n "$g" ]]; do
        [[ -z "$g" ]] && continue
        dirname "$g"
      done \
    | sort -u \
    | while IFS= read -r p || [[ -n "$p" ]]; do
        [[ -z "$p" ]] && continue
        if [[ "$p" == "$AOHP_ROOT" ]]; then
          rel="."
        else
          rel="${p#$AOHP_ROOT/}"
        fi
        printf '%s\t%s\n' "$rel" "$p"
      done | sort -t $'\t' -k1,1 | cut -f2-
)

LIST="$WORKDIR/repos.tsv"
idx=0
for proj_dir in "${REPOS[@]}"; do
  if [[ "$proj_dir" == "$AOHP_ROOT" ]]; then
    rel="."
  else
    rel="${proj_dir#$AOHP_ROOT/}"
  fi
  printf '%s\t%s\t%s\n' "$idx" "$proj_dir" "$rel"
  ((idx++)) || true
done >"$LIST"

check_one() {
  local line="$1"
  local idx proj_dir rel out f ahead
  IFS=$'\t' read -r idx proj_dir rel <<<"$line"
  if ! out="$(git -C "$proj_dir" status --porcelain 2>&1)"; then
    echo "[Git error] ${rel}: ${out}" >>"$WORKDIR/errors"
    return 0
  fi
  if [[ -n "$out" ]]; then
    f=$(printf '%s/out/%05d.dirty' "$WORKDIR" "$idx")
    {
      echo "========== Uncommitted changes: ${rel} =========="
      git -C "$proj_dir" status --short
      echo ""
    } >"$f"
  fi
  # Unpushed commits relative to upstream (requires branch.*.merge / tracking branch)
  if git -C "$proj_dir" rev-parse '@{u}' >/dev/null 2>&1; then
    ahead=$(git -C "$proj_dir" rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)
    if [[ "$ahead" =~ ^[0-9]+$ ]] && (( ahead > 0 )); then
      f=$(printf '%s/out/%05d.unpushed' "$WORKDIR" "$idx")
      {
        echo "========== Unpushed commits: ${rel} (ahead of @{upstream} by ${ahead}) =========="
        git -C "$proj_dir" log --oneline --decorate '@{u}..HEAD'
        echo ""
      } >"$f"
    fi
  fi
  return 0
}
export -f check_one
export WORKDIR AOHP_ROOT

if [[ ${#REPOS[@]} -gt 0 ]]; then
  # Newline must be the sole delimiter: default xargs splits on whitespace, which breaks paths with spaces.
  # shellcheck disable=SC2016
  cat "$LIST" | xargs -d '\n' -P "$JOBS" -L 1 bash -c 'check_one "$1"' _
fi

if [[ -f "$WORKDIR/errors" ]]; then
  cat "$WORKDIR/errors"
fi
for f in "$WORKDIR"/out/*.dirty; do
  [[ -e "$f" ]] || continue
  cat "$f"
done
for f in "$WORKDIR"/out/*.unpushed; do
  [[ -e "$f" ]] || continue
  cat "$f"
done

dirty_count=$(find "$WORKDIR/out" -name '*.dirty' -type f 2>/dev/null | wc -l)
unpushed_count=$(find "$WORKDIR/out" -name '*.unpushed' -type f 2>/dev/null | wc -l)
git_err_count=0
[[ -f "$WORKDIR/errors" ]] && git_err_count=$(wc -l <"$WORKDIR/errors")

echo "--- Summary ---"
echo "AOHP root: ${AOHP_ROOT}"
echo "Git repositories found: ${#REPOS[@]}"
echo "Parallel jobs: ${JOBS}"
echo "Repos with uncommitted changes: ${dirty_count}"
echo "Repos with unpushed commits: ${unpushed_count}"
echo "Git command failures: ${git_err_count}"

if ((dirty_count > 0 || unpushed_count > 0)); then
  exit 1
fi
exit 0

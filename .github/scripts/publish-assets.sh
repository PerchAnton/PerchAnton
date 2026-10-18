#!/usr/bin/env bash
# Updates only known SVGs on a dedicated branch. No force-push or main-branch changes.
set -euo pipefail

: "${READY_DIR:?READY_DIR must contain validated SVG images}"
: "${PUBLISH_DIR:?PUBLISH_DIR must be an unused worktree directory}"
branch="profile-assets"

if [[ -e "$PUBLISH_DIR" ]]; then
  echo "Refusing to overwrite existing worktree directory: $PUBLISH_DIR" >&2
  exit 1
fi

names=(snake-light.svg snake-dark.svg stats-light.svg stats-dark.svg
       languages-light.svg languages-dark.svg streak-light.svg streak-dark.svg)
found=0
for name in "${names[@]}"; do
  [[ ! -L "$READY_DIR/$name" ]] || { echo "Refusing a symlink: $name" >&2; exit 1; }
  if [[ -f "$READY_DIR/$name" ]]; then found=$((found + 1)); fi
done
if [[ "$found" -eq 0 ]]; then
  echo "No validated images to publish." >&2
  exit 1
fi

# A failed remote query is fatal, not interpreted as an empty repository.
remote_ref="$(git ls-remote --heads origin "refs/heads/$branch")"
if [[ -n "$remote_ref" ]]; then
  git fetch --no-tags --depth=1 origin "refs/heads/$branch:refs/remotes/origin/$branch"
  git worktree add --detach "$PUBLISH_DIR" "refs/remotes/origin/$branch"
else
  git worktree add --detach "$PUBLISH_DIR" HEAD
  git -C "$PUBLISH_DIR" switch --orphan "$branch"
fi
cleanup() { git worktree remove --force "$PUBLISH_DIR"; }
trap cleanup EXIT

for name in "${names[@]}"; do
  if [[ -f "$READY_DIR/$name" ]]; then
    cp -- "$READY_DIR/$name" "$PUBLISH_DIR/$name"
    git -C "$PUBLISH_DIR" add -- "$name"
  fi
done

if git -C "$PUBLISH_DIR" diff --cached --quiet; then
  echo "Profile images are already up to date."
  exit 0
fi

git -C "$PUBLISH_DIR" -c user.name='github-actions[bot]' \
  -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit -m 'Refresh profile animation and statistics'
# Refuse non-fast-forward pushes rather than overwriting concurrent changes.
git -C "$PUBLISH_DIR" push origin "HEAD:refs/heads/$branch"

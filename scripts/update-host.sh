#!/usr/bin/env bash
set -euo pipefail

repo="${WCGW_REPO:-$HOME/wcgw}"

fail() {
  printf 'update-wcgw: %s\n' "$*" >&2
  exit 1
}

[[ -d "$repo/.git" ]] || fail "missing git checkout at $repo"

remote="$(git -C "$repo" remote get-url origin)"
case "$remote" in
  git@github.com:brandonp2412/wcgw.git|https://github.com/brandonp2412/wcgw.git)
    ;;
  *)
    fail "origin is not Brandon's WCGW fork: $remote"
    ;;
esac

[[ -z "$(git -C "$repo" status --porcelain)" ]] || fail "checkout is dirty; refusing to upgrade"

uv_bin="$(command -v uv || true)"
[[ -n "$uv_bin" ]] || uv_bin="$HOME/.local/bin/uv"
[[ -x "$uv_bin" ]] || fail "uv is not installed"

git -C "$repo" fetch --prune origin main
git -C "$repo" switch main
git -C "$repo" pull --ff-only origin main
(
  cd "$repo"
  "$uv_bin" sync --frozen --inexact
)

commit="$(git -C "$repo" rev-parse --short HEAD)"

if [[ "${IN_WCGW_ENVIRONMENT:-}" == "1" ]]; then
  printf 'wcgw source updated to %s; restart skipped because this command is running inside WCGW\n' "$commit"
  exit 0
fi

if systemctl --user is-active --quiet glass-wcgw-http.service 2>/dev/null; then
  systemctl --user restart glass-wcgw-http.service glass-tunnel-http.service
  systemctl --user is-active --quiet glass-wcgw-http.service glass-tunnel-http.service
elif systemctl --user is-active --quiet nox-wcgw-http.service 2>/dev/null; then
  systemctl --user restart nox-wcgw-http.service nox-tunnel-http.service
  systemctl --user is-active --quiet nox-wcgw-http.service nox-tunnel-http.service
elif systemctl is-active --quiet openai-mcp-tunnel-pi.service 2>/dev/null; then
  sudo -n systemctl restart openai-mcp-tunnel-pi.service
  sudo -n systemctl is-active --quiet openai-mcp-tunnel-pi.service
else
  fail "could not identify the WCGW service to restart"
fi

printf 'wcgw updated and restarted at %s\n' "$commit"

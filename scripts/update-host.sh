#!/usr/bin/env bash
set -euo pipefail

repo="${WCGW_REPO:-$HOME/wcgw}"

fail() {
  printf 'update-wcgw: %s\n' "$*" >&2
  exit 1
}

[[ -d "$repo/.git" ]] || fail "missing git checkout at $repo"

remote="$(git -C "$repo" remote get-url origin)"
normalized_remote="${remote/https:\/\/github.com:443\//https:\/\/github.com\/}"
case "$normalized_remote" in
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

mapfile -t user_units < <(
  systemctl --user list-units --type=service --state=active --no-legend --plain 2>/dev/null |
    awk '$1 ~ /^[[:alnum:]_.@-]+-wcgw-http[.]service$/ { print $1 }'
)

if (( ${#user_units[@]} == 1 )); then
  service="${user_units[0]}"
  tunnel="${service%-wcgw-http.service}-tunnel-http.service"
  systemctl --user restart "$service" "$tunnel"
  systemctl --user is-active --quiet "$service" "$tunnel"
else
  mapfile -t system_units < <(
    systemctl list-units --type=service --state=active --no-legend --plain 2>/dev/null |
      awk '$1 ~ /^openai-mcp-tunnel-[[:alnum:]_-]+[.]service$/ { print $1 }'
  )
  (( ${#system_units[@]} == 1 )) || fail "could not identify one WCGW service to restart"
  sudo -n systemctl restart "${system_units[0]}"
  sudo -n systemctl is-active --quiet "${system_units[0]}"
fi

printf 'wcgw updated and restarted at %s\n' "$commit"

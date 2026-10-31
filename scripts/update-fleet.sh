#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'update-wcgw-fleet: %s\n' "$*" >&2
  exit 1
}

if [[ "${IN_WCGW_ENVIRONMENT:-}" == "1" ]]; then
  fail "run this from a host shell, not from inside the WCGW connector"
fi

if [[ -n "${WCGW_FLEET_HOSTS:-}" ]]; then
  read -r -a hosts <<< "$WCGW_FLEET_HOSTS"
else
  config="${WCGW_FLEET_CONFIG:-$HOME/.config/wcgw/fleet-hosts}"
  [[ -r "$config" ]] || fail "set WCGW_FLEET_HOSTS or create a private fleet-hosts file"
  mapfile -t hosts < <(awk 'NF && $1 !~ /^#/ { print $1 }' "$config")
fi

(( ${#hosts[@]} > 0 )) || fail "no fleet hosts configured"
for host in "${hosts[@]}"; do
  [[ "$host" =~ ^[[:alnum:]][[:alnum:]_.-]*$ ]] || fail "invalid fleet host alias"
  printf '\n== %s ==\n' "$host"
  ssh -o BatchMode=yes "$host" '$HOME/.local/bin/update-wcgw'
done

printf '\n== local ==\n'
"$HOME/.local/bin/update-wcgw"

local_commit="$(git -C "$HOME/wcgw" rev-parse HEAD)"
for host in "${hosts[@]}"; do
  remote_commit="$(ssh -o BatchMode=yes "$host" 'git -C "$HOME/wcgw" rev-parse HEAD')"
  [[ "$local_commit" == "$remote_commit" ]] || fail "local and $host differ: $local_commit != $remote_commit"
done

printf '\nAll WCGW hosts are on %s\n' "${local_commit:0:7}"

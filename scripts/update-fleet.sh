#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'update-wcgw-fleet: %s\n' "$*" >&2
  exit 1
}

if [[ "${IN_WCGW_ENVIRONMENT:-}" == "1" ]]; then
  fail "run this from a normal Glass shell, not from inside the Glass WCGW connector"
fi

for host in nox pi; do
  printf '\n== %s ==\n' "$host"
  ssh -o BatchMode=yes "$host" '$HOME/.local/bin/update-wcgw'
done

printf '\n== glass ==\n'
"$HOME/.local/bin/update-wcgw"

local_commit="$(git -C "$HOME/wcgw" rev-parse HEAD)"
nox_commit="$(ssh -o BatchMode=yes nox 'git -C "$HOME/wcgw" rev-parse HEAD')"
pi_commit="$(ssh -o BatchMode=yes pi 'git -C "$HOME/wcgw" rev-parse HEAD')"

[[ "$local_commit" == "$nox_commit" ]] || fail "Glass and Nox differ: $local_commit != $nox_commit"
[[ "$local_commit" == "$pi_commit" ]] || fail "Glass and Pi differ: $local_commit != $pi_commit"

printf '\nAll WCGW hosts are on %s\n' "${local_commit:0:7}"

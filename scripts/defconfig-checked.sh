#!/bin/bash
# Kconfig can report dependency errors while make still exits successfully.
set -eo pipefail
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
make defconfig 2>&1 | tee "$log"
if grep -Eq 'recursive dependency detected|:error:' "$log"; then
  echo '::error::Kconfig reported errors despite a successful make exit; refusing this build.'
  exit 1
fi

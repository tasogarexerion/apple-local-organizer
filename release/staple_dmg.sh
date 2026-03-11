#!/bin/zsh
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <artifact-path>" >&2
  exit 1
fi

ARTIFACT_PATH="$1"
xcrun stapler staple "$ARTIFACT_PATH"

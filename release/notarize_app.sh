#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${APPLE_LOCAL_AI_RELEASE_BUILD_DIR:-$ROOT_DIR/release/build}"
ARTIFACT_PATH="${APPLE_LOCAL_AI_NOTARIZE_PATH:-}"
PROFILE="${NOTARY_PROFILE:-}"
TEAM_ID_VALUE="${TEAM_ID:-}"
MANIFEST_PATH="${BUILD_DIR}/notary-manifest.json"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact)
      ARTIFACT_PATH="$2"
      shift
      ;;
    --profile)
      PROFILE="$2"
      shift
      ;;
    --team-id)
      TEAM_ID_VALUE="$2"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    *)
      if [[ -z "$ARTIFACT_PATH" ]]; then
        ARTIFACT_PATH="$1"
      elif [[ -z "$PROFILE" ]]; then
        PROFILE="$1"
      elif [[ -z "$TEAM_ID_VALUE" ]]; then
        TEAM_ID_VALUE="$1"
      else
        echo "Unknown option: $1" >&2
        exit 1
      fi
      ;;
  esac
  shift
done

if [[ -z "$ARTIFACT_PATH" || -z "$PROFILE" || -z "$TEAM_ID_VALUE" ]]; then
  echo "Usage: $0 [--artifact <path>] [--profile <keychain-profile>] [--team-id <team-id>] [--dry-run]" >&2
  echo "Or set APPLE_LOCAL_AI_NOTARIZE_PATH, NOTARY_PROFILE, and TEAM_ID." >&2
  exit 1
fi

if [[ ! -e "$ARTIFACT_PATH" ]]; then
  echo "Artifact not found: $ARTIFACT_PATH" >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"

if (( DRY_RUN )); then
  ARTIFACT_PATH_ENV="$ARTIFACT_PATH" \
  PROFILE_ENV="$PROFILE" \
  TEAM_ID_ENV="$TEAM_ID_VALUE" \
  MANIFEST_PATH_ENV="$MANIFEST_PATH" \
  python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "artifact_path": os.environ["ARTIFACT_PATH_ENV"],
    "profile": os.environ["PROFILE_ENV"],
    "team_id": os.environ["TEAM_ID_ENV"],
    "status": "dry-run",
}
Path(os.environ["MANIFEST_PATH_ENV"]).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY
  echo "Dry run complete. Manifest: $MANIFEST_PATH"
  exit 0
fi

RESULT="$(
  xcrun notarytool submit "$ARTIFACT_PATH" \
    --keychain-profile "$PROFILE" \
    --team-id "$TEAM_ID_VALUE" \
    --wait \
    --output-format json
)"

RESULT_ENV="$RESULT" \
MANIFEST_PATH_ENV="$MANIFEST_PATH" \
python3 - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(os.environ["RESULT_ENV"])
Path(os.environ["MANIFEST_PATH_ENV"]).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY

echo "$RESULT"

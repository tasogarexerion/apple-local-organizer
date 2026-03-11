#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${VENV_PYTHON:-$ROOT_DIR/.venv-fm312/bin/python}"
MODEL_NAME="${MODEL:-mlx-community/Llama-3.2-3B-Instruct-4bit}"
MAX_TOKENS="${MAX_TOKENS:-192}"
TEMPERATURE="${TEMP:-0.7}"
PROMPT="${1:-Apple Silicon で動くローカル LLM の動作確認です。3行で短く自己紹介してください。}"

exec "$PYTHON_BIN" -m mlx_lm generate \
  --model "$MODEL_NAME" \
  --prompt "$PROMPT" \
  --max-tokens "$MAX_TOKENS" \
  --temp "$TEMPERATURE"

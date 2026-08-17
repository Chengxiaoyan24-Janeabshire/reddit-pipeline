#!/usr/bin/env bash
# One-shot setup for the Reddit pipeline runtime.
# Run this from the project root: bash scripts/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "reddit pipeline setup"
echo "project dir: $PROJECT_DIR"
echo

echo "[1/3] creating venv (.venv) ..."
python3 -m venv .venv

echo "[2/3] installing python deps ..."
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

echo "[3/3] installing chromium for optional blog fetch ..."
if [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
  echo "  system Chrome found; skipping Playwright Chromium download"
else
  ./.venv/bin/playwright install chromium
fi

echo
echo "done."
echo "smoke test:"
echo "  python3 -m unittest tests.test_rules"
echo "  python3 scripts/append_pack_to_feishu.py --validate-only --weekly < samples/weekly_pack.example.json"

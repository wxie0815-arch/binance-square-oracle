#!/usr/bin/env bash

set -euo pipefail

echo "== Binance Square Oracle local prototype installer =="

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3.8+ is required for local prototype mode."
  echo "If you are using OpenClaw, prefer installing and running the root SKILL.md instead."
  exit 1
fi

echo "Using Python: $PYTHON_BIN"

if command -v pip3 >/dev/null 2>&1; then
  PIP_BIN="pip3"
elif command -v pip >/dev/null 2>&1; then
  PIP_BIN="pip"
else
  echo "pip was not found. Please install pip first."
  exit 1
fi

echo "Installing Python dependencies..."
$PIP_BIN install -r requirements.txt

echo "Running import smoke test..."
$PYTHON_BIN - <<'PY'
import collect
import config
import oracle
import publish

print("config.VERSION =", config.VERSION)
print("styles =", oracle.list_available_styles())
print("routes =", sorted(collect.get_available_routes().keys()))
print("publish helper ready =", callable(publish.publish_to_square))
PY

echo
echo "Local prototype mode is ready."
echo "For local generation, set OPENAI_API_KEY and optionally OPENAI_BASE_URL / OPENAI_MODEL."
echo "For OpenClaw competition usage, install the repository as a skill and use SKILL.md."

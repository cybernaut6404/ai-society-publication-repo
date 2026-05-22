#!/bin/bash
# Wrapper for the publication-repo daemon. Sources secrets.env so
# PUBLICATION_KEY_<polity_id> tokens are visible to the FastAPI auth gate.
set -e

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [ -f "$HOME/.ai-society/secrets.env" ]; then
  set -a; source "$HOME/.ai-society/secrets.env"; set +a
fi

cd "/Users/richardweakley/ai-workspace/publication-repo"

UVICORN=".venv/bin/uvicorn"
if [ ! -x "$UVICORN" ]; then
  echo "ERROR: $UVICORN not found. Run: .venv/bin/pip install fastapi uvicorn pydantic" >&2
  exit 1
fi

exec "$UVICORN" backend.server:app --host 127.0.0.1 --port 9100

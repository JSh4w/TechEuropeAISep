#!/usr/bin/env bash
# One-time dev setup. Works on macOS (Homebrew) and Linux. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

have() { command -v "$1" >/dev/null 2>&1; }

# 1. uv (Python + dependencies)
if ! have uv; then
  echo "==> Installing uv"
  if have brew; then brew install uv; else curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; fi
fi

# 2. Temporal CLI (includes the local dev server)
if ! have temporal && [ ! -x "$HOME/.temporalio/bin/temporal" ]; then
  echo "==> Installing Temporal CLI"
  if have brew; then brew install temporal; else curl -sSf https://temporal.download/cli.sh | sh; fi
fi
if ! have temporal && [ -x "$HOME/.temporalio/bin/temporal" ]; then
  echo "    Add Temporal to your PATH:  export PATH=\"\$PATH:\$HOME/.temporalio/bin\""
fi

# 3. Python deps (uv downloads the right Python version if needed)
echo "==> Installing Python dependencies"
uv sync

# 4. Secrets file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env — fill in the keys (ask Josh)"
fi

# 5. Modal login (opens a browser; skipped if already logged in)
if ! uv run modal profile current >/dev/null 2>&1; then
  echo "==> Logging in to Modal"
  uv run modal setup
fi

echo
echo "Done. Next:"
echo "  temporal server start-dev      # in its own terminal (UI at http://localhost:8233)"
echo "  uv run python scripts/check_env.py"

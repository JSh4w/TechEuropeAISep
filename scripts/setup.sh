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

# 3. Node.js for the web UI (Next.js 16 needs Node >= 20.9)
node_major() { node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0; }
if ! have node || [ "$(node_major)" -lt 20 ]; then
  echo "==> Installing Node.js"
  if have brew; then
    brew install node
  else
    echo "    Install Node.js 20+ (https://nodejs.org, or your package manager), then re-run this script." >&2
    exit 1
  fi
fi

# 4. Python deps (uv downloads the right Python version if needed)
echo "==> Installing Python dependencies"
uv sync

# 5. Secrets file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env — fill in the keys (ask Josh)"
fi

# 6. Modal login (opens a browser; skipped if already logged in)
if ! uv run python -c "import sys, modal.config as c; sys.exit(not c.config.get('token_id'))"; then
  echo "==> Logging in to Modal"
  uv run modal setup
fi

# 7. Web UI dependencies (exact versions from package-lock.json)
echo "==> Installing web dependencies"
(cd sandbox/map_session/web && npm ci --no-audit --no-fund)

echo
echo "Done. Next:"
echo "  uv run python scripts/check_env.py   # check keys and logins"
echo "  ./scripts/dev.sh                     # start Temporal + worker + web UI (Ctrl+C stops all)"

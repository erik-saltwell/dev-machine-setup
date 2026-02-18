#!/usr/bin/env bash
set -euo pipefail

# dev_machine_setup.sh
# - Installs uv if missing
# - Installs pyinfra as a uv tool
# - Runs pyinfra using inventory.py + deploy.py against @local

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$REPO_ROOT"

echo "==> Repo root: $REPO_ROOT"

# 1) Install uv if missing
if ! command -v uv >/dev/null 2>&1; then
  echo "==> Installing uv..."
  # Official installer (Linux/macOS)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Ensure ~/.local/bin is on PATH for this script invocation
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "==> uv already installed: $(uv --version)"
fi

# 2) Install pyinfra as a uv tool (idempotent)
if ! command -v pyinfra >/dev/null 2>&1; then
  echo "==> Installing pyinfra with uv tool install..."
  uv tool install pyinfra
else
  echo "==> pyinfra already available: $(pyinfra --version)"
fi

# 3) Run pyinfra deploy against local machine
if [[ ! -f "inventory.py" ]]; then
  echo "ERROR: inventory.py not found in $REPO_ROOT" >&2
  exit 1
fi
if [[ ! -f "deploy.py" ]]; then
  echo "ERROR: deploy.py not found in $REPO_ROOT" >&2
  exit 1
fi

echo "==> Running pyinfra deploy (@local)..."
pyinfra inventory.py deploy.py --limit @local

echo "==> Done."

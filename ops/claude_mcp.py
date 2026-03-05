# ops/claude_mcp.py
from __future__ import annotations

import json
import shlex
from io import StringIO
from pathlib import Path
from typing import Any

from pyinfra import host
from pyinfra.operations import files, server

from .util import as_primary_user_kwargs, primary_home

# For CLI config writes, we don't need a sudo "login shell".
USER = as_primary_user_kwargs(use_sudo_login=False)

DEFAULT_SCOPE = "user"


def _claude_bin() -> Path:
    # Match your claude_code.py convention.
    return primary_home() / ".local" / "bin" / "claude"


def _local_bin_dir() -> Path:
    return primary_home() / ".local" / "bin"


def _npx_wrapper_path() -> Path:
    # Wrapper that loads NVM then execs npx; handy for Node-based MCP servers.
    return _local_bin_dir() / "claude-mcp-npx"


def _ensure_npx_wrapper() -> None:
    files.directory(
        name="Ensure ~/.local/bin exists (for Claude MCP wrapper)",
        path=str(_local_bin_dir()),
        present=True,
        **USER,
    )

    wrapper = """#!/usr/bin/env bash
set -euo pipefail

export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi

exec npx "$@"
"""

    files.put(
        name="Install Claude MCP npx wrapper (loads NVM then execs npx)",
        src=StringIO(wrapper),
        dest=str(_npx_wrapper_path()),
        mode="755",
        **USER,
    )


def _servers_from_inventory() -> list[dict[str, Any]]:
    """
    Required inventory format:

    claude_mcp_servers = [
      {
        "name": "playwright",
        "scope": "user",  # optional; defaults to "user"
        "config": {
          "type": "stdio",
          "command": "~/.local/bin/claude-mcp-npx",
          "args": ["-y", "@playwright/mcp@latest"],
          "env": {},
        },
      },
      ...
    ]
    """
    servers = host.data.claude_mcp_servers  # hard-fail if missing
    if not isinstance(servers, list) or not servers:
        raise ValueError("host.data.claude_mcp_servers must be a non-empty list")
    return servers


def _expand_tilde(s: str) -> str:
    # Expand only leading "~/" (leave "~user" etc. alone unless you want that too)
    if s.startswith("~/"):
        return str(primary_home() / s[2:])
    return s


def _expand_tildes_any(obj: Any) -> Any:
    """
    Recursively expand "~/" in any string anywhere in the config:
    - command
    - args elements
    - env values
    - nested dict/list structures
    """
    if isinstance(obj, str):
        return _expand_tilde(obj)
    if isinstance(obj, list):
        return [_expand_tildes_any(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _expand_tildes_any(v) for k, v in obj.items()}
    return obj


def _normalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a server config before JSON-encoding.

    - Expand "~/" everywhere (command, args, env values, etc.)
    """
    # Make a shallow copy first, then recurse
    return _expand_tildes_any(dict(cfg))


def _json_arg(obj: dict[str, Any]) -> str:
    # Compact JSON, shell-quoted as a single argument.
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    return shlex.quote(raw)


def install_claude_mcp_servers(*, install_npx_wrapper: bool = True) -> None:
    """
    Configure MCP servers for Claude Code from inventory.

    Reconcile behavior:
      - Always remove (ignore errors) then add-json each run, so inventory is source of truth.
    """
    if install_npx_wrapper:
        _ensure_npx_wrapper()

    claude = _claude_bin()

    # Fail fast if Claude Code CLI isn't installed where expected.
    server.shell(
        name="Verify Claude Code CLI exists",
        commands=f'test -x "{claude}"',
        **USER,
    )

    for item in _servers_from_inventory():
        name = str(item["name"])
        scope = str(item.get("scope", DEFAULT_SCOPE))
        cfg = _normalize_config(dict(item["config"]))
        cfg_json = _json_arg(cfg)

        # Reconcile-to-inventory: remove then add-json every run.
        server.shell(
            name=f"Reconcile Claude MCP server: {name} (scope={scope})",
            commands=(
                f'"{claude}" mcp remove --scope {shlex.quote(scope)} {shlex.quote(name)} >/dev/null 2>&1 || true; '
                f'"{claude}" mcp add-json --scope {shlex.quote(scope)} {shlex.quote(name)} {cfg_json}'
            ),
            **USER,
        )


def uninstall_claude_mcp_servers(*, remove_wrapper: bool = False) -> None:
    """
    Remove MCP servers listed in inventory (best-effort).
    """
    claude = _claude_bin()

    # If Claude isn't present, just skip quietly.
    server.shell(
        name="Verify Claude Code CLI exists (best-effort)",
        commands=f'test -x "{claude}" || exit 0',
        **USER,
    )

    for item in _servers_from_inventory():
        name = str(item["name"])
        scope = str(item.get("scope", DEFAULT_SCOPE))

        server.shell(
            name=f"Remove Claude MCP server: {name} (scope={scope})",
            commands=(
                f'"{claude}" mcp remove --scope {shlex.quote(scope)} {shlex.quote(name)} >/dev/null 2>&1 || true'
            ),
            **USER,
        )

    if remove_wrapper:
        files.file(
            name="Remove Claude MCP npx wrapper",
            path=str(_npx_wrapper_path()),
            present=False,
            **USER,
        )
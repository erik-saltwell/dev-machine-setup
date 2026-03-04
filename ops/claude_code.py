# ops/claude_code.py
from __future__ import annotations

from pyinfra.operations import files, server

from .util import as_primary_user_kwargs, primary_home

USER = as_primary_user_kwargs()

CLAUDE_BIN = primary_home() / ".local" / "bin" / "claude"
CLAUDE_DATA_DIR = primary_home() / ".local" / "share" / "claude"
CLAUDE_CONFIG_DIR = primary_home() / ".claude"
CLAUDE_CONFIG_JSON = primary_home() / ".claude.json"
INSTALL_URL = "https://claude.ai/install.sh"


def install_claude_code() -> None:
    """
    Installs Claude Code CLI for the primary user using the official installer.
    User-level install to ~/.local/bin/claude.
    Idempotent: skips if the binary already exists.
    """
    files.directory(
        name="Ensure ~/.local/bin exists",
        path=str(primary_home() / ".local" / "bin"),
        present=True,
        **USER,
    )

    server.shell(
        name="Install Claude Code CLI",
        commands=f'test -f "{CLAUDE_BIN}" || curl -fsSL "{INSTALL_URL}" | bash',
        **USER,
    )


def uninstall_claude_code(*, remove_config: bool = False) -> None:
    """
    Removes the Claude Code CLI binary and data directory.
    Optionally removes configuration files (~/.claude, ~/.claude.json).
    """
    files.file(
        name="Remove Claude Code binary",
        path=str(CLAUDE_BIN),
        present=False,
        **USER,
    )

    files.directory(
        name="Remove Claude Code data directory",
        path=str(CLAUDE_DATA_DIR),
        present=False,
        **USER,
    )

    if remove_config:
        files.directory(
            name="Remove Claude Code config directory",
            path=str(CLAUDE_CONFIG_DIR),
            present=False,
            **USER,
        )
        files.file(
            name="Remove Claude Code config json",
            path=str(CLAUDE_CONFIG_JSON),
            present=False,
            **USER,
        )
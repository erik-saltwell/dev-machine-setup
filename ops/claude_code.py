# ops/claude_code.py
from __future__ import annotations

from pyinfra import host
from pyinfra.operations import server

CLAUDE_BIN = "~/.local/bin/claude"
CLAUDE_DATA_DIR = "~/.local/share/claude"
CLAUDE_CONFIG_DIR = "~/.claude"
CLAUDE_CONFIG_JSON = "~/.claude.json"
INSTALL_URL = "https://claude.ai/install.sh"


def install_claude_code() -> None:
    """
    Installs Claude Code CLI for host.data.user using the official native installer.
    Installs to ~/.local/bin/claude (user-level, not system-wide).
    Idempotent: skips if the binary already exists.
    """
    server.shell(
        name="Install Claude Code CLI",
        commands=f"test -f {CLAUDE_BIN} || curl -fsSL {INSTALL_URL} | bash",
        _sudo=True,
        _sudo_user=host.data.user,
    )


def uninstall_claude_code(*, remove_config: bool = False) -> None:
    """
    Removes the Claude Code CLI binary and version files.
    Optionally removes configuration files (~/.claude, ~/.claude.json).
    """
    server.shell(
        name="Remove Claude Code binary",
        commands=f"rm -f {CLAUDE_BIN}",
        _sudo=True,
        _sudo_user=host.data.user,
    )

    server.shell(
        name="Remove Claude Code data directory",
        commands=f"rm -rf {CLAUDE_DATA_DIR}",
        _sudo=True,
        _sudo_user=host.data.user,
    )

    if remove_config:
        server.shell(
            name="Remove Claude Code configuration files",
            commands=f"rm -rf {CLAUDE_CONFIG_DIR} && rm -f {CLAUDE_CONFIG_JSON}",
            _sudo=True,
            _sudo_user=host.data.user,
        )

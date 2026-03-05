# ops/nodejs.py
from __future__ import annotations

import shlex
from pathlib import Path

from pyinfra import host
from pyinfra.operations import apt, files, server

from .util import as_root_kwargs, as_primary_user_kwargs, primary_home

ROOT = as_root_kwargs()
# Avoid sudo "login shell" here; we explicitly set NVM_DIR and source nvm.sh ourselves.
USER = as_primary_user_kwargs(use_sudo_login=False)

NVM_DIR: Path = primary_home() / ".nvm"
BASHRC: Path = primary_home() / ".bashrc"
ZSHRC: Path = primary_home() / ".zshrc"

NVM_COMMENT = "# NVM (Node Version Manager)"
NVM_DIR_LINE = 'export NVM_DIR="$HOME/.nvm"'
NVM_SOURCE_LINE = '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # Load nvm'


def _bash_lc(script: str) -> str:
    """
    Run a bash login command with strict error handling.
    """
    return "bash -lc " + shlex.quote("set -euo pipefail; " + script)


def _nvm_bash_lc(script: str) -> str:
    """
    Run a bash command that sets NVM_DIR and sources nvm.sh (must exist).
    """
    nvm_dir = str(NVM_DIR)
    return _bash_lc(
        f'export NVM_DIR="{nvm_dir}"; '
        'if [ ! -s "$NVM_DIR/nvm.sh" ]; then '
        '  echo "ERROR: $NVM_DIR/nvm.sh not found (NVM not installed?)" >&2; '
        '  ls -la "$NVM_DIR" || true; '
        "  exit 1; "
        "fi; "
        '. "$NVM_DIR/nvm.sh"; '
        + script
    )


def _ensure_rc_files_exist() -> None:
    files.file(name="Ensure ~/.bashrc exists", path=str(BASHRC), touch=True, **USER)
    files.file(name="Ensure ~/.zshrc exists", path=str(ZSHRC), touch=True, **USER)


def _ensure_nvm_shell_lines() -> None:
    _ensure_rc_files_exist()
    for rc in (BASHRC, ZSHRC):
        files.line(
            name=f"Add NVM comment in {rc.name}",
            path=str(rc),
            line=NVM_COMMENT,
            present=True,
            ensure_newline=True,
            **USER,
        )
        files.line(
            name=f"Set NVM_DIR in {rc.name}",
            path=str(rc),
            line=NVM_DIR_LINE,
            present=True,
            ensure_newline=True,
            **USER,
        )
        files.line(
            name=f"Source nvm.sh in {rc.name}",
            path=str(rc),
            line=NVM_SOURCE_LINE,
            present=True,
            ensure_newline=True,
            **USER,
        )


def install_nodejs() -> None:
    """
    Installs NVM + Node.js for the primary user.

    Inventory knobs (optional):
      - nvm_install_ref: tag/commit for the installer (default: "master")
      - node_version: what to install (default: "lts/*")
    """
    apt.packages(
        name="Ensure deps for NVM install",
        packages=["curl", "ca-certificates"],
        update=True,
        **ROOT,
    )

    _ensure_nvm_shell_lines()

    nvm_install_ref: str = host.data.get("nvm_install_ref", "master")
    nvm_install_url: str = f"https://raw.githubusercontent.com/nvm-sh/nvm/{nvm_install_ref}/install.sh"

    # Install NVM if missing, but do it in a way that fails if curl fails.
    server.shell(
        name="Install NVM",
        commands=_bash_lc(
            f'export NVM_DIR="{str(NVM_DIR)}"; '
            'if [ ! -s "$NVM_DIR/nvm.sh" ]; then '
            '  tmp="$(mktemp)"; '
            f'  curl -fsSL "{nvm_install_url}" -o "$tmp"; '
            '  bash "$tmp"; '
            '  rm -f "$tmp"; '
            "fi; "
            'test -s "$NVM_DIR/nvm.sh"'
        ),
        **USER,
    )

    node_version: str = host.data.get("node_version", "lts/*")

    # Verify NVM actually loaded, then install node.
    server.shell(
        name=f"Install Node.js via NVM ({node_version})",
        commands=_nvm_bash_lc(
            'command -v nvm >/dev/null; '
            f'nvm install "{node_version}"; '
            f'nvm alias default "{node_version}"; '
            "node --version; npm --version"
        ),
        **USER,
    )


def uninstall_nodejs(*, remove_shell_lines: bool = True, remove_npm_cache: bool = False) -> None:
    files.directory(
        name="Remove ~/.nvm",
        path=str(NVM_DIR),
        present=False,
        **USER,
    )

    if remove_npm_cache:
        files.directory(
            name="Remove ~/.npm",
            path=str(primary_home() / ".npm"),
            present=False,
            **USER,
        )

    if remove_shell_lines:
        _ensure_rc_files_exist()
        for rc in (BASHRC, ZSHRC):
            files.line(
                name=f"Remove nvm.sh source line from {rc.name}",
                path=str(rc),
                line=NVM_SOURCE_LINE,
                present=False,
                **USER,
            )
            files.line(
                name=f"Remove NVM_DIR line from {rc.name}",
                path=str(rc),
                line=NVM_DIR_LINE,
                present=False,
                **USER,
            )
            files.line(
                name=f"Remove NVM comment from {rc.name}",
                path=str(rc),
                line=NVM_COMMENT,
                present=False,
                **USER,
            )
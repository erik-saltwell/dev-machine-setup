# ops/util.py
from __future__ import annotations

import getpass
import os
from pathlib import Path

from pyinfra import host
from typing import Any

def primary_user() -> str:
    """
    Return the user account we are configuring the machine for.

    Priority:
      1) inventory "user" (recommended; you already have this set)
      2) SUDO_USER (if the deploy was launched with sudo, this is the original user)
      3) getpass.getuser() (the current process user)
    """
    inv_user = host.data.get("user")
    if inv_user:
        return str(inv_user)

    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        return sudo_user

    return getpass.getuser()


def primary_home(user: str | None = None) -> Path:
    """
    Return the home directory as a Path for the configured user (or a provided user).

    Uses "~user" expansion which respects system user database entries.

    """
    u = user or primary_user()
    return Path(f"~{u}").expanduser()

def as_primary_user_kwargs(
    *,
    user: str | None = None,
    use_sudo_login: bool = True,
) -> dict[str, Any]:
    """
    Return pyinfra global-arg kwargs to run an operation as the configured user.

    Typical use: any operation that writes into ~/.config, ~/.ssh, ~/.zshrc,
    installs nvm into ~/.nvm, clones dotfiles, etc — especially when you might
    run deploy as root.

    Example:
        files.block(..., **as_configured_user_kwargs())
    """
    u = user or primary_user()
    return {
        "_sudo": True,
        "_sudo_user": u,
        "_use_sudo_login": use_sudo_login,
    }

def as_root_kwargs() -> dict[str, object]:
    return {"_sudo": True}
# ops/zsh.py
from __future__ import annotations

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import apt, server

ZSH_PATH = "/usr/bin/zsh"
BASH_PATH = "/usr/bin/bash"

OMZ_DIR = "~/.oh-my-zsh"
OMZ_COMMIT = "45dd7d006ab2650273d9859f7e3224cf757a9db3"
OMZ_INSTALLER_URL = f"https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/{OMZ_COMMIT}/tools/install.sh"


def install_zsh() -> None:
    """
    Installs zsh, sets it as the login shell for host.data.user,
    and installs oh-my-zsh for that same user.
    Hard-fails if host.data.user is missing.
    """
    # 1) Install prerequisites
    apt.packages(
        name="Install zsh + prerequisites",
        packages=["zsh", "git", "curl"],
        update=True,
    )

    # 2) Set default shell for the user
    server.user(
        name="Set default shell to zsh",
        user=host.data.user,
        shell=ZSH_PATH,
    )

    # 3) Install oh-my-zsh (idempotent via directory guard)
    # Run as the target user, not root.
    server.shell(
        name="Install oh-my-zsh",
        commands=(
            f'test -d {OMZ_DIR} || '
            # Avoid auto-launching zsh and avoid chsh prompts; keep existing .zshrc
            f'RUNZSH=no CHSH=no KEEP_ZSHRC=yes '
            f'sh -c "$(curl -fsSL {OMZ_INSTALLER_URL})"'
        ),
        _sudo=True,
        _sudo_user=host.data.user,
    )


def uninstall_zsh(*, revert_to_bash: bool = True, remove_oh_my_zsh: bool = True) -> None:
    """
    Reverts the user's shell to bash (optional), removes oh-my-zsh directory (optional),
    and removes zsh.
    Hard-fails if host.data.user is missing.
    """
    if revert_to_bash:
        server.user(
            name="Revert default shell to bash",
            user=host.data.user,
            shell=BASH_PATH,
        )

    if remove_oh_my_zsh:
        # Remove the oh-my-zsh directory in the user's home.
        server.shell(
            name="Remove oh-my-zsh directory",
            commands=f"rm -rf {OMZ_DIR}",
            _sudo=True,
            _sudo_user=host.data.user,
        )

    apt.packages(
        name="Remove zsh",
        packages=["zsh"],
        present=False,
    )

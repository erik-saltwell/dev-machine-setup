# ops/dotfiles.py
from __future__ import annotations

from pyinfra import host
from pyinfra.operations import server, snap

CHEZMOI_SOURCE_DIR = "$HOME/.local/share/chezmoi"


def install_dotfiles() -> None:
    """
    Install chezmoi and apply dotfiles.

    Requires (hard-fail if missing):
      - host.data.dotfiles_repo_url

    Behavior:
      - Installs chezmoi via snap classic.
      - If not initialized: `chezmoi init --apply <repo>`
      - If initialized and dotfiles_update_every_run is True (default): `chezmoi update`
    """
    repo_url: str = host.data.dotfiles_repo_url  # hard-fail if missing
    update_every_run: bool = getattr(host.data, 'dotfiles_update_every_run', True)
    user: str = host.data.user

    snap.package(
        name="Install chezmoi (snap classic)",
        packages=["chezmoi"],
        classic=True,
    )

    # chezmoi must run as the target user so dotfiles deploy to their $HOME
    # Always init if not already initialized
    server.shell(
        name="Init dotfiles with chezmoi",
        commands=f'test -d "{CHEZMOI_SOURCE_DIR}" || chezmoi init --apply "{repo_url}"',
        _sudo_user=user,
    )

    # Only update on subsequent runs if configured to do so
    if update_every_run:
        server.shell(
            name="Update dotfiles with chezmoi",
            commands=f'test -d "{CHEZMOI_SOURCE_DIR}" && chezmoi update',
            _sudo_user=user,
        )


def uninstall_dotfiles(*, purge_binary: bool = False) -> None:
    """
    Remove chezmoi management state.

    `chezmoi purge --force` removes chezmoi config/state/source, but leaves the
    dotfiles it applied in your home directory intact.

    If purge_binary=True, also removes the chezmoi snap.
    """
    user: str = host.data.user

    server.shell(
        name="Purge chezmoi state",
        commands="chezmoi purge --force",
        _sudo_user=user,
    )

    if purge_binary:
        snap.package(
            name="Remove chezmoi snap",
            packages=["chezmoi"],
            present=False,
            classic=True,
        )

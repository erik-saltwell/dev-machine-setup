# ops/dotfiles.py
from __future__ import annotations

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import server, snap

from .util import as_root_kwargs, as_primary_user_kwargs, primary_home

ROOT = as_root_kwargs()
USER = as_primary_user_kwargs()

# NOTE: must be relative components; do NOT use Path("/.local/...") here
CHEZMOI_SOURCE_DIR = primary_home() / ".local" / "share" / "chezmoi"


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
    update_every_run: bool = host.data.get("dotfiles_update_every_run", True)

    # Snap operation is plural in pyinfra
    snap.packages(
        name="Install chezmoi (snap classic)",
        packages=["chezmoi"],
        classic=True,
        **ROOT,
    )

    # Run as the target user so chezmoi uses that user's $HOME
    server.shell(
        name="Init dotfiles with chezmoi",
        commands=f'test -d "{CHEZMOI_SOURCE_DIR}" || chezmoi init --apply "{repo_url}"',
        **USER,
    )

    if update_every_run:
        server.shell(
            name="Update dotfiles with chezmoi",
            commands=f'test -d "{CHEZMOI_SOURCE_DIR}" && chezmoi update',
            **USER,
        )


def uninstall_dotfiles(*, purge_binary: bool = False) -> None:
    """
    Remove chezmoi management state.

    `chezmoi purge --force` removes chezmoi config/state/source, but leaves the
    dotfiles it applied in your home directory intact.

    If purge_binary=True, also removes the chezmoi snap.
    """
    # Forgiving/idempotent: only attempt purge if chezmoi exists, and never fail the deploy
    if host.get_fact(Which, command="chezmoi"):
        server.shell(
            name="Purge chezmoi state",
            commands="chezmoi purge --force || true",
            **USER,
        )

    if purge_binary:
        snap.packages(
            name="Remove chezmoi snap",
            packages=["chezmoi"],
            present=False,
            classic=True,
            **ROOT,
        )
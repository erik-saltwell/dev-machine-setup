# ops/dotfiles.py
from __future__ import annotations

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import server, snap

from .util import as_root_kwargs, as_primary_user_kwargs, primary_home

ROOT = as_root_kwargs()
USER = as_primary_user_kwargs(use_sudo_login=False)

CHEZMOI_SOURCE_DIR = primary_home() / ".local" / "share" / "chezmoi"


def _chezmoi_cmd(subcommand: str) -> str:
    """
    Build a chezmoi command with safety flags.

    Inventory knobs:
      - dotfiles_debug: bool (default False) -> adds --debug --verbose
      - dotfiles_exclude_scripts: bool (default False) -> adds --exclude=scripts
      - dotfiles_force: bool (default False) -> adds --force
    """
    debug: bool = host.data.get("dotfiles_debug", False)
    exclude_scripts: bool = host.data.get("dotfiles_exclude_scripts", False)
    force: bool = host.data.get("dotfiles_force", False)

    flags: list[str] = ["--no-pager", "--no-tty"]
    if debug:
        flags.extend(["--debug", "--verbose"])
    if exclude_scripts:
        flags.append("--exclude=scripts")
    if force:
        flags.append("--force")

    return f"chezmoi {' '.join(flags)} {subcommand}"


def install_dotfiles() -> None:
    repo_url: str = host.data.dotfiles_repo_url  # hard-fail if missing
    update_every_run: bool = host.data.get("dotfiles_update_every_run", True)

    snap.package(
        name="Install chezmoi (snap classic)",
        packages=["chezmoi"],
        classic=True,
        **ROOT,
    )

    init_cmd = _chezmoi_cmd(f'init --apply "{repo_url}"')
    server.shell(
        name="Init dotfiles with chezmoi",
        commands=f'test -d "{CHEZMOI_SOURCE_DIR}" || {init_cmd}',
        **USER,
    )

    if update_every_run:
        server.shell(
            name="Update dotfiles with chezmoi",
            commands=f'test -d "{CHEZMOI_SOURCE_DIR}" && {_chezmoi_cmd("update")}',
            **USER,
        )


def uninstall_dotfiles(*, purge_binary: bool = False) -> None:
    if host.get_fact(Which, command="chezmoi"):
        server.shell(
            name="Purge chezmoi state",
            commands=f"{_chezmoi_cmd('purge --force')} || true",
            **USER,
        )

    if purge_binary:
        snap.package(
            name="Remove chezmoi snap",
            packages=["chezmoi"],
            present=False,
            classic=True,
            **ROOT,
        )
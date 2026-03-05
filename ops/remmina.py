# ops/remmina.py
from __future__ import annotations

from pathlib import Path

from pyinfra.operations import files

from .util import as_primary_user_kwargs, primary_home

# For pure file operations, a sudo "login shell" doesn't buy us anything and can cause surprises.
USER = as_primary_user_kwargs(use_sudo_login=False)

# Layout:
#   my_pkg/ops/remmina.py
#   my_pkg/files/remmina/*.remmina
_FILES_DIR = Path(__file__).resolve().parents[1] / "files" / "remmina"
_DEST_DIR = primary_home() / ".local" / "share" / "remmina"


def install_remmina() -> None:
    files.directory(
        name="Ensure ~/.local/share/remmina exists",
        path=str(_DEST_DIR),
        present=True,
        **USER,
    )

    for src_path in sorted(_FILES_DIR.glob("*.remmina")):
        dest_path = _DEST_DIR / src_path.name
        files.put(
            name=f"Deploy Remmina connection: {src_path.name}",
            src=str(src_path),
            dest=str(dest_path),
            **USER,
        )


def uninstall_remmina() -> None:
    for src_path in sorted(_FILES_DIR.glob("*.remmina")):
        dest_path = _DEST_DIR / src_path.name
        files.file(
            name=f"Remove Remmina connection: {src_path.name}",
            path=str(dest_path),
            present=False,
            **USER,
        )
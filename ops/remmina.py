import os

from pyinfra import host
from pyinfra.operations import files

_FILES_DIR = os.path.join(os.path.dirname(__file__), "..", "files", "remmina")
_DEST_DIR = "~/.local/share/remmina"


def install_remmina():
    user = host.data.user

    files.directory(
        name="Ensure ~/.local/share/remmina exists",
        path=_DEST_DIR,
        present=True,
        _sudo_user=user,
    )

    for filename in os.listdir(_FILES_DIR):
        if filename.endswith(".remmina"):
            files.put(
                name=f"Deploy Remmina connection: {filename}",
                src=os.path.join(_FILES_DIR, filename),
                dest=f"{_DEST_DIR}/{filename}",
                _sudo_user=user,
            )


def uninstall_remmina():
    user = host.data.user

    for filename in os.listdir(_FILES_DIR):
        if filename.endswith(".remmina"):
            files.file(
                name=f"Remove Remmina connection: {filename}",
                path=f"{_DEST_DIR}/{filename}",
                present=False,
                _sudo_user=user,
            )

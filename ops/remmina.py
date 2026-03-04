import os

from pyinfra import host
from pyinfra.operations import files


from .util import as_root_kwargs, as_primary_user_kwargs, primary_home
ROOT = as_root_kwargs()
USER = as_primary_user_kwargs()

_FILES_DIR = os.path.join(os.path.dirname(__file__), "..", "files", "remmina")
_DEST_DIR = primary_home()  / ".local/share/remmina"


def install_remmina():

    files.directory(
        name="Ensure ~/.local/share/remmina exists",
        path=_DEST_DIR,
        present=True,
        **USER
    )

    for filename in os.listdir(_FILES_DIR):
        if filename.endswith(".remmina"):
            files.put(
                name=f"Deploy Remmina connection: {filename}",
                src=os.path.join(_FILES_DIR, filename),
                dest=f"{_DEST_DIR}/{filename}",
                **USER
            )


def uninstall_remmina():

    for filename in os.listdir(_FILES_DIR):
        if filename.endswith(".remmina"):
            files.file(
                name=f"Remove Remmina connection: {filename}",
                path=f"{_DEST_DIR}/{filename}",
                present=False,
                **USER
            )

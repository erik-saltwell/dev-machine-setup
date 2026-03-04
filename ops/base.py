# ops/base.py
from pyinfra import host
from pyinfra.operations import apt, snap
from .util import as_root_kwargs, as_primary_user_kwargs
ROOT = as_root_kwargs()
USER = as_primary_user_kwargs()

def install_base() -> None:
    apt.packages(
        name="Install base apt packages",
        packages=host.data.apt_packages,
        **ROOT
    )

    snap.package(
        name="Install classic snaps",
        packages=host.data.snaps_classic,
        classic=True,
        **ROOT
    )

    snap.package(
        name="Install modern snaps",
        packages=host.data.snaps_modern,
        classic=False,
        **ROOT
    )


def uninstall_base() -> None:
    apt.packages(
        name="Remove base apt packages",
        packages=host.data.apt_packages,
        present=False,
        **ROOT
    )

    snap.package(
        name="Remove classic snaps",
        packages=host.data.snaps_classic,
        classic=True,
        present=False,
        **ROOT
    )

    snap.package(
        name="Remove modern snaps",
        packages=host.data.snaps_modern,
        classic=False,
        present=False,
        **ROOT
    )

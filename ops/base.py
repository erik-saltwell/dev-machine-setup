# ops/base.py
from pyinfra import host
from pyinfra.operations import apt, snap

def install_base() -> None:
    apt.packages(
        name="Install base apt packages",
        packages=host.data.apt_packages,
    )

    snap.package(
        name="Install classic snaps",
        packages=host.data.snaps_classic,
        classic=True,
    )

    snap.package(
        name="Install modern snaps",
        packages=host.data.snaps_modern,
        classic=False,
    )


def uninstall_base() -> None:
    apt.packages(
        name="Remove base apt packages",
        packages=host.data.apt_packages,
        present=False,
    )

    snap.package(
        name="Remove classic snaps",
        packages=host.data.snaps_classic,
        classic=True,
        present=False,
    )

    snap.package(
        name="Remove modern snaps",
        packages=host.data.snaps_modern,
        classic=False,
        present=False,
    )

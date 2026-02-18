# ops/pre_install.py
from io import StringIO

from pyinfra import host
from pyinfra.operations import apt, files, server

SNAP_SUDOERS = "/etc/sudoers.d/snap-secure-path"
SNAP_SUDOERS_CONTENT = (
    'Defaults secure_path="/usr/local/sbin:/usr/local/bin:'
    '/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"\n'
)


def preinstall_setup() -> None:
    apt.update(name="apt update")
    apt.upgrade(name="apt upgrade")
    apt.packages(
        name="Install snapd",
        packages=["snapd"],
    )
    files.put(
        name="Add /snap/bin to sudo secure_path",
        src=StringIO(SNAP_SUDOERS_CONTENT),
        dest=SNAP_SUDOERS,
        mode="0440",
        _sudo=True,
    )
    server.shell(
        name="snap refresh",
        commands="test -x /snap/bin/snap && /snap/bin/snap refresh || true",
        _sudo=True,
    )

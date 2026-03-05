# ops/pre_install.py
from io import StringIO

from pyinfra import host
from pyinfra.operations import apt, files, server

from .util import as_root_kwargs, as_primary_user_kwargs, primary_home
ROOT = as_root_kwargs()
USER = as_primary_user_kwargs()

SNAP_SUDOERS = "/etc/sudoers.d/snap-secure-path"
SNAP_SUDOERS_CONTENT = (
    'Defaults secure_path="/usr/local/sbin:/usr/local/bin:'
    '/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"\n'
)


def preinstall_setup() -> None:
    apt.update(name="apt update", **ROOT)
    apt.upgrade(name="apt upgrade", **ROOT)
    apt.packages(
        name="Install snapd",
        packages=["snapd"],
        **ROOT
    )
    files.put(
        name="Add /snap/bin to sudo secure_path",
        src=StringIO(SNAP_SUDOERS_CONTENT),
        dest=SNAP_SUDOERS,
        mode="0440",
        **ROOT
    )
    server.shell(
        name="snap refresh",
        commands="test -x /snap/bin/snap && /snap/bin/snap refresh || true",
        **ROOT
    )

from pyinfra.operations import server

from .util import as_root_kwargs

ROOT = as_root_kwargs()

def do_autoremove()->None:
    server.shell(
            name="apt autoremove",
            commands="apt-get autoremove -y",
            **ROOT,
        )
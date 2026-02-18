from io import StringIO

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import apt, files, server

GH_KEYRING = "/etc/apt/keyrings/githubcli-archive-keyring.gpg"
GH_LIST = "/etc/apt/sources.list.d/github-cli.list"
GH_REPO_LINE = (
    f"deb [arch=amd64 signed-by={GH_KEYRING}] "
    "https://cli.github.com/packages stable main\n"
)


def install_gh() -> None:
    files.directory(
        name="Ensure /etc/apt/keyrings/ exists",
        path="/etc/apt/keyrings",
        mode="755",
        _sudo=True,
    )

    server.shell(
        name="Install GitHub CLI apt keyring",
        commands=(
            f"test -f {GH_KEYRING} || "
            f"curl -fsSL -o {GH_KEYRING} "
            "https://cli.github.com/packages/githubcli-archive-keyring.gpg"
        ),
        _sudo=True,
    )

    files.put(
        name="Add GitHub CLI apt repo",
        src=StringIO(GH_REPO_LINE),
        dest=GH_LIST,
        _sudo=True,
    )

    if host.get_fact(Which, command="gh"):
        return

    apt.update(name="apt update after adding GitHub CLI repo")

    apt.packages(
        name="Install GitHub CLI",
        packages=["gh"],
    )


def uninstall_gh(*, purge: bool = True) -> None:
    if purge:
        server.shell(
            name="Purge GitHub CLI",
            commands="apt-get purge -y gh || true",
            _sudo=True,
        )
    else:
        apt.packages(
            name="Remove GitHub CLI",
            packages=["gh"],
            present=False,
        )

    files.file(
        name="Remove GitHub CLI apt source list",
        path=GH_LIST,
        present=False,
        _sudo=True,
    )

    files.file(
        name="Remove GitHub CLI keyring",
        path=GH_KEYRING,
        present=False,
        _sudo=True,
    )

    apt.update(name="apt update after removing GitHub CLI repo")

    server.shell(
        name="apt autoremove",
        commands="apt-get autoremove -y",
        _sudo=True,
    )

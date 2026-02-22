from io import StringIO

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import apt, files, server

VSCODE_KEYRING = "/usr/share/keyrings/microsoft.gpg"
VSCODE_SOURCES = "/etc/apt/sources.list.d/vscode.sources"
VSCODE_SOURCES_CONTENT = (
    "Types: deb\n"
    "URIs: https://packages.microsoft.com/repos/code\n"
    "Suites: stable\n"
    "Components: main\n"
    "Architectures: amd64,arm64,armhf\n"
    f"Signed-By: {VSCODE_KEYRING}\n"
)


def install_vscode() -> None:
    server.shell(
        name="Install Microsoft apt keyring",
        commands=(
            f"test -f {VSCODE_KEYRING} || "
            f"curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | "
            f"gpg --dearmor -o {VSCODE_KEYRING}"
        ),
        _sudo=True,
    )

    files.put(
        name="Add VS Code apt repo",
        src=StringIO(VSCODE_SOURCES_CONTENT),
        dest=VSCODE_SOURCES,
        _sudo=True,
    )

    apt.packages(
        name="Install apt-transport-https",
        packages=["apt-transport-https"],
        _sudo=True,
    )

    if host.get_fact(Which, command="code"):
        return

    apt.update(name="apt update after adding VS Code repo")

    apt.packages(
        name="Install VS Code",
        packages=["code"],
    )


def uninstall_vscode() -> None:
    server.shell(
        name="Purge VS Code",
        commands="apt-get purge -y code || true",
        _sudo=True,
    )

    files.file(
        name="Remove VS Code apt sources file",
        path=VSCODE_SOURCES,
        present=False,
        _sudo=True,
    )

    files.file(
        name="Remove Microsoft apt keyring",
        path=VSCODE_KEYRING,
        present=False,
        _sudo=True,
    )

    apt.update(name="apt update after removing VS Code repo")

from io import StringIO

from pyinfra import host
from pyinfra.facts.deb import DebPackages
from pyinfra.operations import apt, files, server

from .util import as_root_kwargs

ROOT = as_root_kwargs()

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
    # Only skip if the DEB package is installed (avoids skipping when snap 'code' exists)
    installed = host.get_fact(DebPackages)
    if "code" in installed:
        return

    # Install keyring with safe permissions (mode 644)
    server.shell(
        name="Install Microsoft apt keyring",
        commands=(
            f"test -f {VSCODE_KEYRING} || "
            "wget -qO- https://packages.microsoft.com/keys/microsoft.asc | "
            "gpg --dearmor > /tmp/microsoft.gpg && "
            f"install -D -o root -g root -m 644 /tmp/microsoft.gpg {VSCODE_KEYRING} && "
            "rm -f /tmp/microsoft.gpg; "
            f"chmod 0644 {VSCODE_KEYRING}"
        ),
        **ROOT,
    )

    files.put(
        name="Add VS Code apt repo (deb822 .sources)",
        src=StringIO(VSCODE_SOURCES_CONTENT),
        dest=VSCODE_SOURCES,
        mode="644",
        **ROOT,
    )

    apt.update(name="apt update after adding VS Code repo", **ROOT)

    apt.packages(
        name="Install VS Code",
        packages=["code"],
        **ROOT,
    )


def uninstall_vscode() -> None:
    server.shell(
        name="Purge VS Code",
        commands="apt-get purge -y code || true",
        **ROOT,
    )

    files.file(
        name="Remove VS Code apt sources file",
        path=VSCODE_SOURCES,
        present=False,
        **ROOT,
    )

    files.file(
        name="Remove Microsoft apt keyring",
        path=VSCODE_KEYRING,
        present=False,
        **ROOT,
    )

    apt.update(name="apt update after removing VS Code repo", **ROOT)
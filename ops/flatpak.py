from pyinfra import host
from pyinfra.operations import apt, server


def install_flatpak() -> None:
    apt.packages(
        name="Install flatpak",
        packages=["flatpak"],
    )

    server.shell(
        name="Add Flathub remote",
        commands=["flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo"],
    )

    for app in host.data.flatpak_apps:
        server.shell(
            name=f"Install flatpak app: {app}",
            commands=[f"flatpak install -y flathub {app}"],
        )


def uninstall_flatpak() -> None:
    for app in host.data.flatpak_apps:
        server.shell(
            name=f"Remove flatpak app: {app}",
            commands=[f"flatpak uninstall -y {app}"],
        )

    server.shell(
        name="Remove Flathub remote",
        commands=["flatpak remote-delete --if-exists flathub"],
    )

    apt.packages(
        name="Remove flatpak",
        packages=["flatpak"],
        present=False,
    )

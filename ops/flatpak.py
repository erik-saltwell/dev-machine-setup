from pyinfra import host
from pyinfra.operations import apt, server

from .util import as_root_kwargs

ROOT = as_root_kwargs()


def _flatpak_apps() -> list[str]:
    # Forgiving default if inventory doesn't define this key
    return list(host.data.get("flatpak_apps", []))


def install_flatpak() -> None:
    apt.packages(
        name="Install flatpak",
        packages=["flatpak"],
        **ROOT,
    )

    server.shell(
        name="Add Flathub remote (system)",
        commands=[
            "flatpak remote-add --system --if-not-exists "
            "flathub https://dl.flathub.org/repo/flathub.flatpakrepo"
        ],
        **ROOT,
    )

    for app_id in _flatpak_apps():
        server.shell(
            name=f"Install flatpak app (system): {app_id}",
            commands=[f"flatpak install --system -y --noninteractive flathub {app_id}"],
            **ROOT,
        )


def uninstall_flatpak() -> None:
    for app_id in _flatpak_apps():
        server.shell(
            name=f"Remove flatpak app (system): {app_id}",
            commands=[
                "sh -lc "
                + repr(
                    f"if flatpak info --system {app_id} >/dev/null 2>&1; then "
                    f"flatpak uninstall --system -y --noninteractive {app_id}; "
                    "fi"
                )
            ],
            **ROOT,
        )

    server.shell(
        name="Remove Flathub remote (system)",
        commands=["flatpak remote-delete --system --if-exists flathub"],
        **ROOT,
    )

    apt.packages(
        name="Remove flatpak",
        packages=["flatpak"],
        present=False,
        **ROOT,
    )
from io import StringIO

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import apt, files, server

CHROME_KEYRING = "/usr/share/keyrings/google-chrome.gpg"
CHROME_LIST = "/etc/apt/sources.list.d/google-chrome.list"
CHROME_SOURCE_LINE = (
    f"deb [arch=amd64 signed-by={CHROME_KEYRING}] "
    "http://dl.google.com/linux/chrome/deb/ stable main\n"
)

def install_chrome() -> None:
    # Always ensure repo + keyring are configured (idempotent)
    server.shell(
        name="Install Google Chrome apt keyring",
        commands=(
            f"test -f {CHROME_KEYRING} || "
            f"curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | "
            f"gpg --dearmor -o {CHROME_KEYRING}"
        ),
        _sudo=True,
    )

    files.put(
        name="Add Google Chrome apt repo",
        src=StringIO(CHROME_SOURCE_LINE),
        dest=CHROME_LIST,
        _sudo=True,
    )

    # Only install if not already present
    chrome_path = host.get_fact(Which, command="google-chrome")
    if chrome_path:
        return

    apt.update(name="apt update after adding Chrome repo")

    apt.packages(
        name="Install Google Chrome",
        packages=["google-chrome-stable"],
    )


def uninstall_chrome(*, purge: bool = True, remove_user_profile: bool = False) -> None:
    # 1) Remove (and optionally purge) the package
    if purge:
        server.shell(
            name="Purge Google Chrome",
            commands="apt-get purge -y google-chrome-stable || true",
            _sudo=True,
        )
    else:
        apt.packages(
            name="Remove Google Chrome",
            packages=["google-chrome-stable"],
            present=False,
        )

    # 2) Remove repo + keyring files
    files.file(
        name="Remove Chrome apt source list",
        path=CHROME_LIST,
        present=False,
        _sudo=True,
    )

    files.file(
        name="Remove Chrome keyring",
        path=CHROME_KEYRING,
        present=False,
        _sudo=True,
    )

    # 3) Refresh apt indexes after removing repo
    apt.update(name="apt update after removing Chrome repo")

    # 4) Optional cleanup of orphaned packages
    server.shell(
        name="apt autoremove",
        commands="apt-get autoremove -y",
        _sudo=True,
    )

    # 5) Optional: remove per-user browser profile (DANGEROUS: deletes bookmarks, etc.)
    if remove_user_profile:
        server.shell(
            name="Remove user Chrome profile",
            commands="rm -rf ~/.config/google-chrome ~/.cache/google-chrome",
            _sudo=True,
            _sudo_user=host.data.user,
        )

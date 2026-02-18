# ops/one_password.py
from __future__ import annotations

from io import StringIO

from pyinfra import host
from pyinfra.facts.server import Which
from pyinfra.operations import apt, files, server

KEY_FINGERPRINT_SUFFIX = "AC2D62742012EA22"

ARCHIVE_KEYRING = "/usr/share/keyrings/1password-archive-keyring.gpg"
APT_LIST = "/etc/apt/sources.list.d/1password.list"

DEBSIG_POLICY_DIR = f"/etc/debsig/policies/{KEY_FINGERPRINT_SUFFIX}"
DEBSIG_POLICY_FILE = f"{DEBSIG_POLICY_DIR}/1password.pol"

DEBSIG_KEYRING_DIR = f"/usr/share/debsig/keyrings/{KEY_FINGERPRINT_SUFFIX}"
DEBSIG_KEYRING_FILE = f"{DEBSIG_KEYRING_DIR}/debsig.gpg"

REPO_LINE = (
    f"deb [arch=amd64 signed-by={ARCHIVE_KEYRING}] "
    "https://downloads.1password.com/linux/debian/amd64 stable main\n"
)

ASC_URL = "https://downloads.1password.com/linux/keys/1password.asc"
POL_URL = "https://downloads.1password.com/linux/debian/debsig/1password.pol"

# What we add to shells (simple + portable)
SSH_AUTH_SOCK_LINE = 'export SSH_AUTH_SOCK="$HOME/.1password/agent.sock"'
SSH_AUTH_SOCK_COMMENT = "# 1Password SSH agent"
BASHRC = "~/.bashrc"
ZSHRC = "~/.zshrc"
AGENT_DIR = "~/.1password"


def _ensure_repo_and_keys() -> None:
    """
    Ensure the 1Password apt repo + keyring + debsig policy is configured.
    Safe to run even if already set up.
    """
    apt.packages(
        name="Ensure deps for 1Password repo setup",
        packages=["curl", "gpg", "ca-certificates"],
        update=True,
    )

    server.shell(
        name="Install 1Password apt keyring",
        commands=(
            f"test -f {ARCHIVE_KEYRING} || "
            f"curl -fsSL {ASC_URL} | "
            f"gpg --dearmor --output {ARCHIVE_KEYRING}"
        ),
        _sudo=True,
    )

    # Repo list line per 1Password docs
    files.put(
        name="Add 1Password apt repo",
        src=StringIO(REPO_LINE),
        dest=APT_LIST,
        _sudo=True,
    )

    # debsig-verify policy per 1Password docs
    files.directory(
        name="Ensure debsig policy dir",
        path=DEBSIG_POLICY_DIR,
        present=True,
        _sudo=True,
    )

    files.download(
        name="Install debsig policy file",
        src=POL_URL,
        dest=DEBSIG_POLICY_FILE,
        _sudo=True,
    )

    files.directory(
        name="Ensure debsig keyring dir",
        path=DEBSIG_KEYRING_DIR,
        present=True,
        _sudo=True,
    )

    server.shell(
        name="Install debsig keyring",
        commands=(
            f"test -f {DEBSIG_KEYRING_FILE} || "
            f"curl -fsSL {ASC_URL} | "
            f"gpg --dearmor --output {DEBSIG_KEYRING_FILE}"
        ),
        _sudo=True,
    )

    apt.update(name="apt update after adding 1Password repo")


def _ensure_shell_ssh_auth_sock() -> None:
    """
    Make shells point SSH_AUTH_SOCK at ~/.1password/agent.sock.
    (You still need to enable the SSH agent inside the 1Password app.)
    """
    user = host.data.user

    # Ensure ~/.1password exists (user-level)
    files.directory(
        name="Ensure ~/.1password exists",
        path=AGENT_DIR,
        present=True,
        _sudo_user=user,
    )

    # Add a comment + export line, idempotently (comment first, then export)
    for path in (BASHRC, ZSHRC):
        files.line(
            name=f"Add 1Password SSH agent comment in {path}",
            path=path,
            line=SSH_AUTH_SOCK_COMMENT,
            present=True,
            ensure_newline=True,
            _sudo_user=user,
        )
        files.line(
            name=f"Set SSH_AUTH_SOCK in {path}",
            path=path,
            line=SSH_AUTH_SOCK_LINE,
            present=True,
            ensure_newline=True,
            _sudo_user=user,
        )


def install_1password() -> None:
    """
    Installs:
      - 1Password desktop app: package `1password`
      - 1Password CLI: package `1password-cli` (provides `op`)
    And wires SSH_AUTH_SOCK in bashrc/zshrc to ~/.1password/agent.sock.
    """
    # Always ensure repo/keys and shell config are correct
    _ensure_repo_and_keys()

    # Only install packages if not already present
    app_ok = bool(host.get_fact(Which, command="1password"))
    cli_ok = bool(host.get_fact(Which, command="op"))
    if not (app_ok and cli_ok):
        apt.packages(
            name="Install 1Password app + CLI",
            packages=["1password", "1password-cli"],
        )

    _ensure_shell_ssh_auth_sock()


def uninstall_1password(*, purge: bool = True, remove_shell_lines: bool = True) -> None:
    """
    Removes:
      - `1password`
      - `1password-cli` (op)
      - repo list + keyrings + debsig policy

    Optionally removes the SSH_AUTH_SOCK lines from bashrc/zshrc.
    """
    if purge:
        server.shell(
            name="Purge 1Password app + CLI packages",
            commands="apt-get purge -y 1password 1password-cli || true",
            _sudo=True,
        )
    else:
        apt.packages(
            name="Remove 1Password app + CLI packages",
            packages=["1password", "1password-cli"],
            present=False,
        )

    files.file(
        name="Remove 1Password apt repo list",
        path=APT_LIST,
        present=False,
        _sudo=True,
    )
    files.file(
        name="Remove 1Password apt keyring",
        path=ARCHIVE_KEYRING,
        present=False,
        _sudo=True,
    )
    files.file(
        name="Remove debsig policy file",
        path=DEBSIG_POLICY_FILE,
        present=False,
        _sudo=True,
    )
    files.file(
        name="Remove debsig keyring file",
        path=DEBSIG_KEYRING_FILE,
        present=False,
        _sudo=True,
    )

    server.shell(
        name="Remove debsig dirs if empty",
        commands=(
            f"rmdir {DEBSIG_POLICY_DIR} 2>/dev/null || true\n"
            f"rmdir {DEBSIG_KEYRING_DIR} 2>/dev/null || true"
        ),
        _sudo=True,
    )

    apt.update(name="apt update after removing 1Password repo")

    if remove_shell_lines:
        user = host.data.user
        for path in (BASHRC, ZSHRC):
            files.line(
                name=f"Remove SSH_AUTH_SOCK export from {path}",
                path=path,
                line=SSH_AUTH_SOCK_LINE,
                present=False,
                _sudo_user=user,
            )
            files.line(
                name=f"Remove 1Password SSH agent comment from {path}",
                path=path,
                line=SSH_AUTH_SOCK_COMMENT,
                present=False,
                _sudo_user=user,
            )

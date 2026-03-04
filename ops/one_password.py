# ops/one_password.py
from __future__ import annotations

from io import StringIO
from pathlib import Path

from pyinfra import host
from pyinfra.facts.deb import DebPackages
from pyinfra.operations import apt, files, server

from .util import as_root_kwargs, as_primary_user_kwargs, primary_home

ROOT = as_root_kwargs()
USER = as_primary_user_kwargs()

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
SSH_AUTH_SOCK_COMMENT = "# 1Password SSH agent"
SSH_AUTH_SOCK_LINE = 'export SSH_AUTH_SOCK="$HOME/.1password/agent.sock"'


def _primary_paths() -> tuple[Path, Path, Path]:
    home = primary_home()
    return home / ".1password", home / ".bashrc", home / ".zshrc"


def _ensure_repo_and_keys() -> None:
    """
    Ensure the 1Password apt repo + keyring + debsig policy is configured.
    Safe to run even if already set up.
    """
    apt.packages(
        name="Ensure deps for 1Password repo setup",
        packages=["curl", "gpg", "ca-certificates"],
        update=True,
        **ROOT,
    )

    # Install apt keyring with safe perms; always enforce 0644
    server.shell(
        name="Install 1Password apt keyring",
        commands=(
            f"test -f {ARCHIVE_KEYRING} || "
            "curl -fsSL " + ASC_URL + " | "
            "gpg --dearmor > /tmp/1password-archive-keyring.gpg && "
            f"install -D -o root -g root -m 644 /tmp/1password-archive-keyring.gpg {ARCHIVE_KEYRING} && "
            "rm -f /tmp/1password-archive-keyring.gpg; "
            f"chmod 0644 {ARCHIVE_KEYRING}"
        ),
        **ROOT,
    )

    files.put(
        name="Add 1Password apt repo",
        src=StringIO(REPO_LINE),
        dest=APT_LIST,
        mode="644",
        **ROOT,
    )

    # debsig-verify policy per 1Password docs
    files.directory(
        name="Ensure debsig policy dir",
        path=DEBSIG_POLICY_DIR,
        present=True,
        mode="755",
        **ROOT,
    )

    files.download(
        name="Install debsig policy file",
        src=POL_URL,
        dest=DEBSIG_POLICY_FILE,
        mode="644",
        **ROOT,
    )

    files.directory(
        name="Ensure debsig keyring dir",
        path=DEBSIG_KEYRING_DIR,
        present=True,
        mode="755",
        **ROOT,
    )

    # Install debsig keyring with safe perms; always enforce 0644
    server.shell(
        name="Install debsig keyring",
        commands=(
            f"test -f {DEBSIG_KEYRING_FILE} || "
            "curl -fsSL " + ASC_URL + " | "
            "gpg --dearmor > /tmp/1password-debsig.gpg && "
            f"install -D -o root -g root -m 644 /tmp/1password-debsig.gpg {DEBSIG_KEYRING_FILE} && "
            "rm -f /tmp/1password-debsig.gpg; "
            f"chmod 0644 {DEBSIG_KEYRING_FILE}"
        ),
        **ROOT,
    )

    apt.update(name="apt update after adding 1Password repo", **ROOT)


def _ensure_shell_ssh_auth_sock() -> None:
    """
    Make shells point SSH_AUTH_SOCK at ~/.1password/agent.sock.
    (You still need to enable the SSH agent inside the 1Password app.)
    """
    agent_dir, bashrc, zshrc = _primary_paths()

    files.directory(
        name="Ensure ~/.1password exists",
        path=str(agent_dir),
        present=True,
        **USER,
    )

    for rc_path in (bashrc, zshrc):
        files.line(
            name=f"Add 1Password SSH agent comment in {rc_path}",
            path=str(rc_path),
            line=SSH_AUTH_SOCK_COMMENT,
            present=True,
            ensure_newline=True,
            **USER,
        )
        files.line(
            name=f"Set SSH_AUTH_SOCK in {rc_path}",
            path=str(rc_path),
            line=SSH_AUTH_SOCK_LINE,
            present=True,
            ensure_newline=True,
            **USER,
        )


def install_1password() -> None:
    """
    Installs:
      - 1Password desktop app: package `1password`
      - 1Password CLI: package `1password-cli` (provides `op`)
    And wires SSH_AUTH_SOCK in bashrc/zshrc to ~/.1password/agent.sock.
    """
    _ensure_repo_and_keys()

    installed = host.get_fact(DebPackages)
    app_ok = "1password" in installed
    cli_ok = "1password-cli" in installed

    if not (app_ok and cli_ok):
        apt.packages(
            name="Install 1Password app + CLI",
            packages=["1password", "1password-cli"],
            **ROOT,
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
            **ROOT,
        )
    else:
        apt.packages(
            name="Remove 1Password app + CLI packages",
            packages=["1password", "1password-cli"],
            present=False,
            **ROOT,
        )

    files.file(
        name="Remove 1Password apt repo list",
        path=APT_LIST,
        present=False,
        **ROOT,
    )
    files.file(
        name="Remove 1Password apt keyring",
        path=ARCHIVE_KEYRING,
        present=False,
        **ROOT,
    )
    files.file(
        name="Remove debsig policy file",
        path=DEBSIG_POLICY_FILE,
        present=False,
        **ROOT,
    )
    files.file(
        name="Remove debsig keyring file",
        path=DEBSIG_KEYRING_FILE,
        present=False,
        **ROOT,
    )

    server.shell(
        name="Remove debsig dirs if empty",
        commands=(
            f"rmdir {DEBSIG_POLICY_DIR} 2>/dev/null || true\n"
            f"rmdir {DEBSIG_KEYRING_DIR} 2>/dev/null || true"
        ),
        **ROOT,
    )

    apt.update(name="apt update after removing 1Password repo", **ROOT)

    if remove_shell_lines:
        _, bashrc, zshrc = _primary_paths()
        for rc_path in (bashrc, zshrc):
            files.line(
                name=f"Remove SSH_AUTH_SOCK export from {rc_path}",
                path=str(rc_path),
                line=SSH_AUTH_SOCK_LINE,
                present=False,
                **USER,
            )
            files.line(
                name=f"Remove 1Password SSH agent comment from {rc_path}",
                path=str(rc_path),
                line=SSH_AUTH_SOCK_COMMENT,
                present=False,
                **USER,
            )
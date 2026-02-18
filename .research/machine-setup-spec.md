# Machine Setup Spec

Derived from the current codebase. This document describes exactly what the automation does, in what order, and what the end-state of a fully provisioned machine looks like.

---

## Target Environment

| Property       | Value                            |
|----------------|----------------------------------|
| OS             | Linux (Ubuntu/Debian-based)      |
| Architecture   | amd64                            |
| Target host    | `@local` (the machine running the script) |
| Privilege       | sudo required                    |
| Target user    | `eriksalt`                       |

---

## Toolchain

The automation itself is bootstrapped via two tools installed by the entry-point script (`setup_machine.sh`):

| Tool     | Purpose                                         | Install method                     |
|----------|--------------------------------------------------|------------------------------------|
| **uv**   | Rust-based Python package/tool manager            | `curl \| sh` from `astral.sh/uv`  |
| **pyinfra** | Python infrastructure-as-code framework (like Ansible) | `uv tool install pyinfra`      |

Both installs are guarded (`command -v` check) so the script is idempotent.

---

## Execution Order

`deploy.py` calls operations in this fixed sequence:

| Step | Function             | Module              |
|------|----------------------|---------------------|
| 1    | `preinstall_setup()` | `ops/pre_install.py` |
| 2    | `install_base()`     | `ops/base.py`       |
| 3    | `install_chrome()`   | `ops/chrome.py`     |
| 4    | `install_zsh()`      | `ops/zsh.py`        |
| 5    | `install_1password()` | `ops/one_password.py` |
| 6    | `install_dotfiles()` | `ops/dotfiles.py`   |

---

## Step 1: Pre-install Setup

**Module:** `ops/pre_install.py`

| Action         | Detail            |
|----------------|-------------------|
| `apt.update`   | Refresh package lists |
| `apt.upgrade`  | Upgrade all installed packages |
| `snap refresh` | Update all installed snaps |

**Post-condition:** System packages and snaps are up to date.

---

## Step 2: Base Packages

**Module:** `ops/base.py`

### APT packages

| Category              | Packages                                              |
|-----------------------|-------------------------------------------------------|
| CLI utilities         | `wget`, `curl`, `micro`, `git`, `gpg`, `ca-certificates` |
| GUI text editor       | `kate`                                                |
| Build toolchain       | `build-essential`, `python3-dev`, `pkg-config`        |
| Development libraries | `libssl-dev`, `libffi-dev`, `zlib1g-dev`              |

### Snap packages

| Package     | Confinement | Purpose          |
|-------------|-------------|------------------|
| `code`      | classic     | VS Code          |
| `discord`   | strict      | Discord          |

**Post-condition:** All listed packages are installed and available on PATH.

---

## Step 3: Google Chrome

**Module:** `ops/chrome.py`

**Guard:** Skipped entirely if `google-chrome` binary already exists on PATH.

### Install sequence

1. Download Google's Linux signing key and convert to GPG keyring at `/usr/share/keyrings/google-chrome.gpg` (guarded by `test -f`).
2. Write apt source line to `/etc/apt/sources.list.d/google-chrome.list`:
   ```
   deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main
   ```
3. `apt update` to pick up the new repository.
4. Install `google-chrome-stable` via apt.

### Uninstall capability

`uninstall_chrome()` supports:
- Package removal (with optional purge)
- Repo and keyring file cleanup
- `apt autoremove`
- Optional user profile deletion (`~/.config/google-chrome`, `~/.cache/google-chrome`)

**Post-condition:** Google Chrome installed from Google's signed apt repository.

---

## Step 4: Zsh + Oh-My-Zsh

**Module:** `ops/zsh.py`

### Install sequence

1. Install `zsh`, `git`, `curl` via apt (with `update=True`).
2. Runtime guard: raise `RuntimeError` if `zsh` not found on PATH after install.
3. Set `eriksalt`'s login shell to `/usr/bin/zsh` via `server.user`.
4. Install Oh-My-Zsh for `eriksalt` (run as that user via `_sudo_user`):
   - Guarded by `test -d ~/.oh-my-zsh`
   - Environment flags: `RUNZSH=no CHSH=no KEEP_ZSHRC=yes`
   - Installer fetched from `raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh`

### Uninstall capability

`uninstall_zsh()` supports:
- Reverting login shell to `/usr/bin/bash`
- Removing `~/.oh-my-zsh` directory
- Removing the `zsh` apt package

**Post-condition:** User `eriksalt` has zsh as default shell with Oh-My-Zsh framework installed.

---

## Step 5: 1Password (App + CLI + SSH Agent)

**Module:** `ops/one_password.py`

**Guard:** If both `1password` and `op` commands exist, skips package installation (but still ensures SSH_AUTH_SOCK config).

### Install sequence

#### 5a. Repository and key setup (`_ensure_repo_and_keys`)

1. Ensure prerequisite packages: `curl`, `gpg`, `ca-certificates`.
2. Download and install GPG keyring at `/usr/share/keyrings/1password-archive-keyring.gpg` (guarded by `test -f`).
3. Write apt source line to `/etc/apt/sources.list.d/1password.list`:
   ```
   deb [arch=amd64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/amd64 stable main
   ```
4. Create debsig policy directory `/etc/debsig/policies/AC2D62742012EA22/`.
5. Download debsig policy file to that directory (guarded by `test -f`).
6. Create debsig keyring directory `/usr/share/debsig/keyrings/AC2D62742012EA22/`.
7. Download and install debsig keyring (guarded by `test -f`).
8. `apt update`.

#### 5b. Package installation

- `1password` (desktop app)
- `1password-cli` (provides the `op` command)

#### 5c. SSH agent shell integration (`_ensure_shell_ssh_auth_sock`)

1. Ensure `~/.1password/` directory exists.
2. Add the following lines to both `~/.bashrc` and `~/.zshrc`:
   ```bash
   # 1Password SSH agent
   export SSH_AUTH_SOCK="$HOME/.1password/agent.sock"
   ```

### Uninstall capability

`uninstall_1password()` supports:
- Package removal (with optional dpkg purge)
- Repo list, keyring, and debsig file/directory cleanup
- `apt update` after repo removal
- Optional removal of SSH_AUTH_SOCK lines from shell rc files

**Post-condition:** 1Password app and CLI installed from signed repository. SSH agent socket configured in both bash and zsh rc files.

---

## Step 6: Dotfiles (Chezmoi)

**Module:** `ops/dotfiles.py`

**Hard dependency:** `host.data.dotfiles_repo_url` must be set (currently `https://github.com/erik-saltwell/dotfiles.git`).

### Install sequence

1. Install `chezmoi` via snap (classic confinement).
2. Conditional init/update:
   - If `~/.local/share/chezmoi` does **not** exist: `chezmoi init --apply <repo_url>` (clone + apply).
   - If it **does** exist: `chezmoi update` (pull latest + re-apply).

### Behavior on subsequent runs

When `dotfiles_update_every_run` is `True` (current setting), running the deploy again will pull and re-apply the latest dotfiles from the repo.

### Uninstall capability

`uninstall_dotfiles()` supports:
- `chezmoi purge --force` (removes chezmoi state; leaves applied dotfiles in place)
- Optional removal of the chezmoi snap itself

**Post-condition:** Dotfiles from the configured git repo are applied to the user's home directory via Chezmoi.

---

## End-State Summary

A fully provisioned machine has:

| Component          | State                                                        |
|--------------------|--------------------------------------------------------------|
| System packages    | Fully updated (apt + snap)                                   |
| CLI tools          | wget, curl, micro, git, gpg, ca-certificates                 |
| GUI editor         | Kate                                                         |
| Build toolchain    | build-essential, python3-dev, pkg-config + dev libs           |
| VS Code            | Installed via snap (classic)                                 |
| Discord            | Installed via snap (strict)                                  |
| Google Chrome      | Installed from Google's signed apt repo                      |
| Shell              | Zsh as default shell for `eriksalt`, Oh-My-Zsh installed     |
| 1Password          | Desktop app + CLI from signed repo, SSH agent wired in rc files |
| Dotfiles           | Applied from `erik-saltwell/dotfiles.git` via Chezmoi        |

---

## Idempotency Model

All operations are designed to be safe to re-run:

| Pattern                 | Used by                          |
|-------------------------|----------------------------------|
| `command -v` / `Which` fact guard | Chrome, Zsh, 1Password |
| `test -f` shell guard   | GPG keyring downloads            |
| `test -d` shell guard   | Oh-My-Zsh, Chezmoi init vs update |
| PyInfra built-in idempotency | apt.packages, snap.package, files.line |

---

## Configuration Surface

All per-machine configuration lives in `inventory.py`:

| Key                        | Type       | Purpose                              |
|----------------------------|------------|---------------------------------------|
| `_sudo`                   | bool       | Run operations with sudo              |
| `apt_packages`            | list[str]  | APT packages to install               |
| `snaps_classic`           | list[str]  | Snap packages (classic confinement)   |
| `snaps_modern`            | list[str]  | Snap packages (strict confinement)    |
| `user`                    | str        | Target user account                   |
| `dotfiles_repo_url`       | str        | Git repo URL for Chezmoi              |
| `dotfiles_update_every_run` | bool     | Re-apply dotfiles on each deploy      |

---

## File System Artifacts

Files and directories created outside of package managers:

| Path                                                          | Owner   | Created by     |
|---------------------------------------------------------------|---------|----------------|
| `/usr/share/keyrings/google-chrome.gpg`                       | root    | Chrome install |
| `/etc/apt/sources.list.d/google-chrome.list`                  | root    | Chrome install |
| `/usr/share/keyrings/1password-archive-keyring.gpg`           | root    | 1Password install |
| `/etc/apt/sources.list.d/1password.list`                      | root    | 1Password install |
| `/etc/debsig/policies/AC2D62742012EA22/1password.pol`         | root    | 1Password install |
| `/usr/share/debsig/keyrings/AC2D62742012EA22/debsig.gpg`     | root    | 1Password install |
| `~/.oh-my-zsh/`                                               | eriksalt | Zsh install   |
| `~/.1password/`                                               | eriksalt | 1Password install |
| `~/.local/share/chezmoi/`                                     | eriksalt | Dotfiles install |

Shell rc file modifications:

| File         | Lines added                                              | Added by          |
|--------------|----------------------------------------------------------|-------------------|
| `~/.bashrc`  | `# 1Password SSH agent` + `export SSH_AUTH_SOCK=...`    | 1Password install |
| `~/.zshrc`   | `# 1Password SSH agent` + `export SSH_AUTH_SOCK=...`    | 1Password install |

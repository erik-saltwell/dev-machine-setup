# CLAUDE.md

## Project overview

Pyinfra-based dev machine setup. Runs locally with `_sudo: True` set globally in inventory.py.

## Key lessons: sudo and user context

This project hit two classes of bugs caused by `_sudo: True` running everything as root:

### 1. User-level operations must use `_sudo_user`

Any operation that touches the user's home directory (dotfiles, shell configs, ~/.1password, etc.) must pass `_sudo_user=host.data.user`. Otherwise it runs as root and either:
- Deploys files to `/root/` instead of the user's home
- Creates files owned by root in the user's home

**Rule:** When writing a new operation, ask "does this belong to the system or the user?" If it writes to `~/`, reads user config, or runs a user-scoped tool (chezmoi, oh-my-zsh), add `_sudo_user=host.data.user`.

### 2. `/snap/bin` is not in sudo's default PATH

Pyinfra's `snap.package()` and snap facts use bare `snap`, which fails under sudo because `/snap/bin` is not in `secure_path`. This is fixed by `preinstall_setup()` dropping a sudoers.d file. Any new `server.shell()` calls that invoke snap directly should still use `/snap/bin/snap` as a defensive measure.

**Rule:** Always run `preinstall_setup()` before any snap operations. If calling snap from `server.shell()`, use the absolute path `/snap/bin/snap`.

### 3. `apt.packages()` limitations

Pyinfra's `apt.packages()` does not support `purge` or `autoremove`. Use `server.shell()` with `apt-get purge -y` or `apt-get autoremove -y` instead.

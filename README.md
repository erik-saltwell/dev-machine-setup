# Dev Machine Setup

Pyinfra-based setup for a fresh Ubuntu machine. Installs core packages, zsh + oh-my-zsh, 1Password, Chrome, GitHub CLI, VS Code, Discord, and applies dotfiles via chezmoi.

## Part 1: Automated Setup

On a blank machine, open a terminal and run the following.

### Install prerequisites

```bash
sudo apt install -y wget unzip curl
```

### Download and extract the repo

```bash
mkdir -p ~/proj
cd ~/proj
wget https://github.com/erik-saltwell/dev-machine-setup/archive/refs/heads/main.zip
unzip main.zip
mv dev-machine-setup-main dev-machine-setup
cd dev-machine-setup
rm ../main.zip
```

### Run the installer

```bash
chmod +x setup_machine.sh
./setup_machine.sh
```

This script will:
1. Install [uv](https://github.com/astral-sh/uv) if not already present
2. Install [pyinfra](https://pyinfra.com/) as a uv tool
3. Run the pyinfra deploy, which installs and configures everything

You will be prompted for your sudo password.

### Start a new shell session

Pyinfra changes your default shell to zsh and deploys new dotfiles. **Log out and log back in** (or reboot) so that:
- zsh becomes your active shell
- PATH changes (uv, snap, etc.) take effect
- The 1Password `SSH_AUTH_SOCK` export is loaded

## Part 2: Manual Steps

These require interactive login and can't be automated. Do them in order.

### 1. 1Password

Open 1Password and sign in to your account. Then:
- Go to **Settings > Developer**
- Enable **Use the SSH agent**

This lets git and ssh use keys stored in 1Password.

### 2. Chrome

Open Chrome and sign in to your Google account to sync bookmarks, extensions, and settings.

### 3. GitHub CLI

```bash
gh auth login
```

Follow the prompts to authenticate via browser. Once done, `git push` will work automatically (your dotfiles already configure `gh` as the git credential helper).

### 4. VS Code

Open VS Code and sign in (GitHub or Microsoft account) to sync your settings, keybindings, and extensions.

### 5. Discord

Open Discord and sign in to your account.

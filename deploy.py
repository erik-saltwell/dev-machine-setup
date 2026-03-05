# deploy.py
from ops.base import install_base, uninstall_base
from ops.pre_install import preinstall_setup
from ops.gh import install_gh, uninstall_gh
from ops.chrome import install_chrome, uninstall_chrome
from ops.vscode import install_vscode, uninstall_vscode
from ops.one_password import install_1password, uninstall_1password
from ops.zsh import install_zsh, uninstall_zsh
from ops.dotfiles import install_dotfiles, uninstall_dotfiles
from ops.claude_code import install_claude_code, uninstall_claude_code
from ops.remmina import install_remmina, uninstall_remmina
from ops.flatpak import install_flatpak, uninstall_flatpak
from ops.autoremove import do_autoremove
from ops.nodejs import install_nodejs, uninstall_nodejs
from ops.claude_mcp import install_claude_mcp_servers, uninstall_claude_mcp_servers

uninstall : bool = False

#preinstall_setup()

if uninstall:
    uninstall_claude_mcp_servers()
    uninstall_nodejs()
    uninstall_claude_code()
    uninstall_dotfiles()
    uninstall_1password()
    uninstall_zsh()
    uninstall_vscode()
    uninstall_chrome()
    uninstall_gh()
    uninstall_remmina()
    uninstall_flatpak()
    uninstall_base()
    do_autoremove()
else:
    #install_base()
    #install_flatpak()
    #install_remmina()
    #install_gh()
    #install_chrome()
    #install_vscode()
    #install_zsh()
    #install_1password()
    #install_dotfiles()
    #install_claude_code()
    #install_nodejs()
    install_claude_mcp_servers()
#preinstall_setup()


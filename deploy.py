# deploy.py
from ops.base import install_base, uninstall_base
from ops.pre_install import preinstall_setup
from ops.gh import install_gh, uninstall_gh
from ops.chrome import install_chrome, uninstall_chrome
from ops.one_password import install_1password, uninstall_1password
from ops.zsh import install_zsh, uninstall_zsh
from ops.dotfiles import install_dotfiles, uninstall_dotfiles
from ops.claude_code import install_claude_code, uninstall_claude_code

uninstall : bool = False

preinstall_setup()

if uninstall:
    uninstall_claude_code()
    uninstall_dotfiles()
    uninstall_1password()
    uninstall_zsh()
    uninstall_chrome()
    uninstall_gh()
    uninstall_base()
else:
    install_base()
    install_gh()
    install_chrome()
    install_zsh()
    install_1password()
    install_dotfiles()
    install_claude_code()
#preinstall_setup()


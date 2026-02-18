# deploy.py
from ops.base import install_base, uninstall_base
from ops.pre_install import preinstall_setup
from ops.chrome import install_chrome, uninstall_chrome
from ops.one_password import install_1password, uninstall_1password
from ops.zsh import install_zsh, uninstall_zsh
from ops.dotfiles import install_dotfiles, uninstall_dotfiles

preinstall_setup()
#uninstall_dotfiles()
#uninstall_1password()
#uninstall_zsh()
#uninstall_chrome()
#uninstall_base()

install_base()
install_chrome()
install_zsh()
install_1password()
install_dotfiles()
#preinstall_setup()


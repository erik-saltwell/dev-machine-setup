from pyinfra import host
from pyinfra.operations import apt, files, server

DEV_USER = host.data.get("dev_user") or host.data.get("ssh_user") or "erik"
HOME = f"/home/{DEV_USER}"
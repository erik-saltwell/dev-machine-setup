# inventory.py

local = [
    ("@local", {
        "apt_packages": [
            "wget", 
            "curl", 
            "micro", 
            "git", 
            "gpg", 
            "ca-certificates", 
            "kate", 
            "remmina",
            "remmina-plugin-rdp",
            "build-essential",
            "python3-dev",
            "pkg-config",
            "libssl-dev",
            "libffi-dev",
            "zlib1g-dev",
            "apt-transport-https",
            ],
        "snaps_classic": ["ghostty"], 
        "snaps_modern": ["discord"],
        "flatpak_apps": ["app.devsuite.Ptyxis"],
        # dotfiles
        "dotfiles_repo_url": "https://github.com/erik-saltwell/dotfiles.git",
        "dotfiles_update_every_run": True,
    }),
]

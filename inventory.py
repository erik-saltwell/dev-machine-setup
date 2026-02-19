# inventory.py

local = [
    ("@local", {
        "_sudo": True,
        "apt_packages": [
            "wget", 
            "curl", 
            "micro", 
            "git", 
            "gpg", 
            "ca-certificates", 
            "kate", 
            
            # build essentials + common dev headers
            "build-essential",
            "python3-dev",
            "pkg-config",
            "libssl-dev",
            "libffi-dev",
            "zlib1g-dev",],
        "snaps_classic": ["code", "ghostty"],
        "snaps_modern": ["discord"],
        "user": "eriksalt",
        # dotfiles
        "dotfiles_repo_url": "https://github.com/erik-saltwell/dotfiles.git",
        "dotfiles_update_every_run": True,
    }),
]

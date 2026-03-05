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
        "snaps_modern": ["discord","ghostwriter"],
        "flatpak_apps": ["app.devsuite.Ptyxis"],
        # dotfiles
        "dotfiles_repo_url": "https://github.com/erik-saltwell/dotfiles.git",
        "dotfiles_update_every_run": True,

        # dotfiles debugging / hang isolation
        #"dotfiles_debug": True,
        #"dotfiles_exclude_scripts": True,
        "dotfiles_force": True,
        "claude_mcp_servers": [
            {
                "name": "playwright",
                "scope": "user",
                "config": {
                "type": "stdio",
                "command": "~/.local/bin/claude-mcp-npx",
                "args": ["-y", "@playwright/mcp@latest"],
                "env": {},
                },
            },
            {
                "name": "chrome-devtools",
                "scope": "user",
                "config": {
                "type": "stdio",
                "command": "~/.local/bin/claude-mcp-npx",
                "args": ["-y", "chrome-devtools-mcp@latest"],
                "env": {},
                },
            },
        ],
    }),
]

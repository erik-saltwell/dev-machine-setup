# PyInfra Best Practices Research

Researched 2026-02-17 against PyInfra v3.x documentation and community sources.

---

## 1. Project Structure

### Recommended Layout

```
project/
  deploy.py              # Main deploy entrypoint
  inventory.py           # Hosts, groups, and host data
  group_data/
    all.py               # Data applied to all hosts
    web_servers.py       # Data for the web_servers group
    db_servers.py        # Data for the db_servers group
  tasks/                 # OR ops/ -- modular operation files
    web.py
    database.py
    common.py
  templates/             # Jinja2 templates for files.template
    app-config.j2.yaml
  files/                 # Static files for files.put
    motd
    hello.bash
```

### Deploy File (deploy.py)

The deploy file is the main entrypoint. It imports and calls operations/deploys.
Two patterns are common:

**Pattern A: Import functions and call them**
```python
from ops.base import install_base
from ops.chrome import install_chrome

install_base()
install_chrome()
```

**Pattern B: Conditional includes based on group membership**
```python
from pyinfra import host, local

if 'web_servers' in host.groups:
    local.include('tasks/web.py')

if 'db_servers' in host.groups:
    local.include('tasks/database.py')
```

Pattern A (importing functions) is cleaner for single-host local-machine setups.
Pattern B (local.include) is better for multi-group server deployments.

### Include Files with Parameters

```python
from pyinfra import local
for group, user in (("admin", "Bob"), ("admin", "Joe")):
    local.include("tasks/create_user.py", data={"group": group, "user": user})
```

---

## 2. Inventory Patterns

### Basic Group Lists

```python
# inventory.py
app_servers = ["app-1.net", "app-2.net"]
db_servers = ["db-1.net", "db-2.net"]
```

### Hosts with Per-Host Data (Tuple Format)

The tuple format `(hostname, data_dict)` is the **standard, documented way** to
attach host-specific configuration:

```python
app_servers = [
    ("app-1.net", {"install_postgres": False}),
    ("db-1.net", {"install_postgres": True}),
]
```

You can mix tuples and plain strings:

```python
app_servers = [
    "app-1.net",
    ("app-2.net", {"some_key": True}),
]
```

### @local Connector in Inventory

For local machine setup, use `@local` as the hostname:

```python
local = [
    ("@local", {"_sudo": True, "user": "myuser"}),
]
```

This creates a group named `local` containing the local machine as the only host.
The `@local` connector executes via subprocess (MacOS/Linux only).

### Group with Tuple Format (List + Empty Dict)

```python
db_servers = (["db-1.net", "db-2.net", "db-3.net"], {})
```

This is a legacy format where the second element is group-level data (not per-host).

### Auto-Generated Groups

- `all` -- contains every host
- The inventory filename itself becomes a group (e.g., hosts in
  `inventories/production.py` belong to group `production`)

### Data Hierarchy (Priority, Highest First)

1. CLI override data (`--data key=value`)
2. Per-host data (from inventory tuples)
3. Normal group data (from `group_data/<group>.py`)
4. `all` group data (from `group_data/all.py`)

### Dynamic Inventories

Since inventory files are pure Python, you can pull from APIs:

```python
import requests

def get_servers():
    servers = requests.get('inventory.mycompany.net/api/v1/servers').json()
    db = [s['hostname'] for s in servers if s['group'] == 'db']
    web = [s['hostname'] for s in servers if s['group'] == 'web']
    return db, web

db_servers, web_servers = get_servers()
```

### Connector Configuration via Data

SSH settings can be set as host/group data:

```python
ssh_user = "ubuntu"
ssh_key = "~/.ssh/some_key"
ssh_key_password = "password for key"
```

### VERDICT on Current inventory.py Pattern

The current project uses:
```python
local = [("@local", {"_sudo": True, ...})]
```

This is **correct and idiomatic**. The tuple format for per-host data is the
officially documented approach. Setting `_sudo` in host data is a supported
pattern that applies sudo as a default for all operations on that host.

---

## 3. Idempotency Patterns

### Core Principle

PyInfra operations define **state, not actions**. Instead of "install this
package," you say "this package should be installed." PyInfra checks current
state via facts and only executes commands when the state doesn't match.

### How It Works (Two-Phase Model)

1. **Prepare Phase**: Deploy code runs, operations query facts via
   `host.get_fact()`, compare desired vs. actual state, and generate commands.
2. **Execute Phase**: Generated commands run on targets in parallel.

This split enables `--dry` mode and change detection.

### Dedicated Operations Are Idempotent

```python
# GOOD: apt.packages checks if already installed
apt.packages(packages=["nginx"], _sudo=True)

# GOOD: files.file checks if file exists with correct permissions
files.file(path="/var/log/app.log", user="app", mode="644")

# GOOD: server.user checks if user exists with correct shell
server.user(user="deploy", shell="/bin/bash")
```

### server.shell Is NOT Idempotent

`server.shell` **always executes** -- it has no state-checking mechanism.
To make shell commands idempotent, use manual guards:

```python
# Pattern: test guard with ||
server.shell(
    name="Install keyring",
    commands="test -f /usr/share/keyrings/app.gpg || curl ... | gpg --dearmor -o ...",
)

# Pattern: test guard with &&
server.shell(
    name="Init app only if not present",
    commands='test -d ~/.app || app init --apply "repo-url"',
)
```

### Change Detection for Conditional Operations

Operations return metadata enabling conditional execution:

```python
create_user = server.user(user="deploy", home="/home/deploy")

server.shell(
    name="Bootstrap deploy user",
    commands=["..."],
    _if=create_user.did_change,  # Only runs if user was actually created
)
```

Available metadata: `did_change`, `did_not_change`, `did_succeed`, `did_error`

Utility functions for multiple conditions:
```python
from pyinfra.operations.util import any_changed, all_changed

server.shell(
    commands=["..."],
    _if=any_changed(op1, op2),  # Runs if either changed
)
```

Lambda for custom logic:
```python
server.shell(
    commands=["..."],
    _if=lambda: op1.did_change() or op2.did_change(),
)
```

---

## 4. Facts, Guards, and Conditionals

### Using Facts

Facts gather system state. Import fact classes and use `host.get_fact()`:

```python
from pyinfra import host
from pyinfra.facts.server import Which, LinuxName, Hostname

# Check if a command exists
chrome_path = host.get_fact(Which, command="google-chrome")
if chrome_path:
    return  # Already installed

# OS-specific logic
if host.get_fact(LinuxName) == "Ubuntu":
    apt.packages(packages=["nano"], _sudo=True)
elif host.get_fact(LinuxName) == "Fedora":
    yum.packages(packages=["nano"], _sudo=True)

# Get actual hostname
actual_hostname = host.get_fact(Hostname)
```

### CRITICAL: Immutable vs. Mutable Facts

**Only use immutable facts** (OS name, architecture, hostname) in deploy-time
conditionals. Mutable facts (disk space, running processes) may change between
fact collection and operation execution.

The docs warn: "Only use immutable facts in deploy code unless you're certain
they won't change during execution."

### Prepare-Phase vs. Execute-Phase Conditionals

**Prepare-phase** (Python if/else during code execution):
```python
# This runs during PREPARE phase -- facts are gathered, no commands executed yet
if host.get_fact(Which, command="zsh"):
    # These operations are REGISTERED but not yet executed
    server.shell(commands=["..."])
```

**Execute-phase** (using `_if` argument):
```python
# This conditional is evaluated during EXECUTION phase
result = server.user(user="deploy")
server.shell(
    commands=["bootstrap-deploy"],
    _if=result.did_change,  # Evaluated AFTER user operation executes
)
```

### CRITICAL ANTI-PATTERN: Checking Operation Results at Prepare Time

**NEVER** do this:
```python
result = server.user(user="deploy")
if result.did_change():  # WRONG! Operations haven't executed yet!
    server.shell(commands=["bootstrap"])
```

**Instead, use `_if`:**
```python
result = server.user(user="deploy")
server.shell(
    commands=["bootstrap"],
    _if=result.did_change,  # Correct! Evaluated at execution time
)
```

### Fact Error Handling

If a fact errors during preparation, it can mark the host as failed:
- Use `_ignore_errors=True` on the operation
- Make the fact command "truthy": `command-that-fails || true`

---

## 5. server.shell vs. Dedicated Operations

### When to Use Dedicated Operations (PREFERRED)

**Always prefer dedicated operations** when one exists for your task:

| Task | Use This | Not This |
|------|----------|----------|
| Install packages | `apt.packages(...)` | `server.shell("apt install ...")` |
| Create users | `server.user(...)` | `server.shell("useradd ...")` |
| Manage files | `files.file(...)` | `server.shell("touch ...")` |
| Set permissions | `files.file(mode=...)` | `server.shell("chmod ...")` |
| Manage services | `server.service(...)` | `server.shell("systemctl ...")` |
| Add apt repos | `apt.repo(...)` | `server.shell("add-apt-repository ...")` |
| Manage lines in files | `files.line(...)` | `server.shell("echo >> ...")` |

Benefits of dedicated operations:
- **Idempotent**: Check state before acting
- **Dry-run support**: Show what would change without changing
- **Change detection**: Return `did_change` metadata
- **Cleaner output**: Named operations with clear descriptions

### When server.shell Is Acceptable

- One-off commands with no dedicated operation (e.g., `lxd init --auto`)
- Commands where you add your own idempotency guard (`test -f ... || ...`)
- Scripts that need to run every time (updates, refreshes)
- Complex pipelines that don't map to a single operation

### server.shell Idempotency Patterns

```python
# Guard: only run if file doesn't exist
server.shell(commands="test -f /path/to/file || curl -o /path/to/file URL")

# Guard: only run if directory doesn't exist
server.shell(commands='test -d ~/.app || app init --apply "repo"')

# Guard: only run if command doesn't exist
server.shell(commands="which myapp || install-myapp.sh")

# Always-run (acceptable for refreshes/updates)
server.shell(commands="snap refresh")
```

---

## 6. Structuring Operations Modules

### Plain Functions (Current Project Pattern)

```python
# ops/chrome.py
from pyinfra import host
from pyinfra.operations import apt, files, server

def install_chrome():
    """Install Google Chrome."""
    # ... operations ...

def uninstall_chrome(*, purge=True):
    """Remove Google Chrome."""
    # ... operations ...
```

This pattern works well for project-internal organization. Functions are imported
and called from deploy.py.

### The @deploy Decorator (For Reusable Packages)

```python
from pyinfra.api import deploy
from pyinfra import host
from pyinfra.operations import apt

DEFAULTS = {"mariadb_version": "1.2.3"}

@deploy("Install MariaDB", data_defaults=DEFAULTS)
def install_mariadb():
    apt.packages(
        packages=[f"mariadb-server={host.data.mariadb_version}"],
    )
```

**When to use `@deploy`:**
- Packaging deploys for distribution via PyPI (e.g., `pyinfra-docker`)
- Creating reusable modules shared across multiple projects
- When you need deploy-wide global arguments applied to all inner operations
- When you need data_defaults that integrate with the host data hierarchy

**When plain functions are fine:**
- Project-internal organization
- Single-project use
- When you don't need deploy-wide argument propagation

The key difference: `@deploy` enables callers to pass global arguments
(like `_sudo=True`) that automatically apply to all operations inside:
```python
install_mariadb(_sudo=True)  # All inner operations get _sudo=True
```

Without `@deploy`, you'd have to pass `_sudo=True` to each operation individually
or set it in config/host data.

### Composing Operations with _inner

When writing custom `@operation`-decorated functions (lower level than `@deploy`),
use `yield from` to compose:

```python
from pyinfra.api import operation

@operation()
def my_operation(path):
    yield from files.file._inner(path=path)
    yield "echo 'additional command'"
```

**Important**: `_inner` only accepts operation-specific arguments, NOT global
arguments like `_sudo`.

---

## 7. Privilege Escalation (_sudo, _sudo_user)

### Per-Operation

```python
apt.update(_sudo=True)
server.shell(commands="...", _sudo=True, _sudo_user="deploy")
```

### Via Host/Group Data (Default for All Operations)

```python
# inventory.py or group_data/all.py
_sudo = True
_sudo_user = "pyinfra"
```

### Via Config (Deploy-Wide Default)

```python
# deploy.py
from pyinfra import config
config.SUDO = True
```

### Full Sudo Options

- `_sudo=True` -- Enable sudo
- `_sudo_user="someuser"` -- Sudo to specific user
- `_use_sudo_login=True` -- Use a login shell when sudo-ing
- `_preserve_sudo_env=True` -- Preserve environment variables during escalation

### Pattern: Running as Target User

```python
server.shell(
    name="Install oh-my-zsh for user",
    commands="...",
    _sudo=True,
    _sudo_user=host.data.user,  # Run as the target user, not root
)
```

### Dynamic Sudo Changes

```python
host.data._sudo_user = 'apache'  # Change sudo user mid-deploy
```

---

## 8. Secrets and Sensitive Data

### Pattern 1: Environment Variables (Recommended)

```python
import os
db_password = os.environ['DB_PASSWORD']
```

### Pattern 2: Encrypted Secrets with privy

```python
# group_data/all.py
import os
import privy

def get_secret(encrypted_secret):
    password = os.environ['TOP_SECRET_PASSWORD']
    return privy.peek(encrypted_secret, password)

db_password = get_secret("encrypted-blob-here")
```

### Pattern 3: Interactive Password Entry

```python
from getpass import getpass
import privy

def get_secret(encrypted_secret):
    password = getpass('Please provide the secret password: ')
    return privy.peek(encrypted_secret, password)
```

### General Best Practices

- Never hardcode secrets in code
- Use environment variables for simple cases
- Use privy or similar for encrypted secrets in group_data
- Integrate with cloud secret managers (Vault, AWS Secrets Manager) for
  production infrastructure
- Exclude .env files from version control

---

## 9. Error Handling and Validation

### OperationError

Raised inside custom operations when an operation cannot proceed:

```python
from pyinfra.api import operation
from pyinfra.api.exceptions import OperationError

@operation()
def my_operation(path):
    if not valid_path(path):
        raise OperationError("Invalid path provided")
    yield f"process {path}"
```

### _ignore_errors

Continue execution even if an operation fails:

```python
server.shell(
    commands="risky-command",
    _ignore_errors=True,
)
```

### Retry Functionality

```python
server.shell(
    commands=["curl -o /tmp/file.tar.gz https://example.com/file.tar.gz"],
    _retries=3,
    _retry_delay=10,
)
```

Custom retry conditions:
```python
def retry_on_network_error(output_data):
    for line in output_data["stderr_lines"]:
        if "network" in line.lower() or "timeout" in line.lower():
            return True
    return False

server.shell(
    commands=["wget https://example.com/large-file.zip"],
    _retries=5,
    _retry_until=retry_on_network_error,
)
```

### Version and Package Requirements

```python
from pyinfra import config
config.REQUIRE_PYINFRA_VERSION = "~=3.0"
config.REQUIRE_PACKAGES = "requirements.txt"
# or
config.REQUIRE_PACKAGES = ["pyinfra~=3.0"]
```

### Exception Hierarchy

- `PyinfraError` -- Base exception
- `OperationError` -- Operation cannot generate output/change state
- `DeployError` -- User exception for deploys/sub-deploys
- `InventoryError` -- Inventory-related errors

---

## 10. Testing and Dry-Run

### Dry-Run Mode

```bash
pyinfra inventory.py deploy.py --dry
```

Shows what operations would be generated without executing anything. This works
because of the two-phase model: all facts are gathered, operations are prepared,
but execution is skipped.

### Debug Operations

```bash
pyinfra inventory.py deploy.py --debug-operations
```

Prints the actual commands that would be executed, then exits.

### Debug Facts

```bash
pyinfra inventory.py deploy.py --debug-facts
```

Prints facts collected after generating operations, then exits.

### Debug Inventory

```bash
pyinfra inventory.py debug-inventory
```

Displays inventory hosts, groups, and data per-host. Useful for validating
your inventory structure.

### Verbosity Levels

- `-v`: Facts collected and noop information
- `-vv`: Plus shell input to remote host
- `-vvv`: Plus shell output from remote host

### Limiting Hosts

```bash
pyinfra inventory.py deploy.py --limit web-1
pyinfra inventory.py deploy.py --limit "web-*"
```

### Testing Strategy

There is no built-in unit testing framework for pyinfra deploys. Recommended
approaches:

1. **Dry-run**: Use `--dry` to validate operations without executing
2. **Debug output**: Use `--debug-operations` to inspect generated commands
3. **Docker testing**: Run against `@docker/ubuntu:22.04` containers for
   isolated testing
4. **Staging environments**: Test against staging hosts before production

---

## 11. files.put: String src vs File src

### How files.put Works

The `src` parameter of `files.put` accepts two types:

**1. File path (string):**
```python
files.put(
    name="Upload config file",
    src="files/motd",          # Relative to deploy directory
    dest="/etc/motd",
)
```

**2. IO object (StringIO):**
```python
from io import StringIO

files.put(
    name="Upload string content",
    src=StringIO("file contents here\n"),
    dest="/etc/motd",
)
```

### IMPORTANT: Passing a Raw String as src

Passing a raw string like `src="deb [arch=amd64] http://..."` to `files.put`
treats it as a **file path**, not as file content. PyInfra will look for a file
with that name relative to the deploy directory.

To pass string content, you MUST wrap it in `StringIO`:

```python
from io import StringIO

# CORRECT: StringIO for string content
files.put(
    src=StringIO("deb [arch=amd64 signed-by=/usr/share/keyrings/app.gpg] http://... stable main\n"),
    dest="/etc/apt/sources.list.d/app.list",
    _sudo=True,
)

# WRONG: This looks for a FILE named "deb [arch=amd64]..."
files.put(
    src="deb [arch=amd64 signed-by=...] http://... stable main\n",
    dest="/etc/apt/sources.list.d/app.list",
    _sudo=True,
)
```

### Limitation with StringIO

When using StringIO as `src`, the `dest` parameter **must be a full file path**,
not a directory. PyInfra cannot derive a filename from a StringIO object.

```python
# CORRECT
files.put(src=StringIO("content"), dest="/etc/app/config.txt")

# WRONG -- TypeError
files.put(src=StringIO("content"), dest="/etc/app/")
```

### Alternative: files.template for Dynamic Content

For dynamic content with variable substitution, `files.template` with Jinja2 is
often better:

```python
files.template(
    src="templates/config.j2",
    dest="/etc/app/config",
    db_hostname=db_hostname,  # Variables passed to template
)
```

Templates automatically receive `host`, `state`, and `inventory` objects.

---

## 12. Common Anti-Patterns and Mistakes

### Anti-Pattern 1: Using server.shell for Everything

```python
# BAD: Not idempotent, no change detection
server.shell(commands="apt-get install -y nginx")

# GOOD: Idempotent, detects existing state
apt.packages(packages=["nginx"], _sudo=True)
```

### Anti-Pattern 2: Checking Operation Results at Prepare Time

```python
# BAD: Operations haven't executed yet during prepare phase
result = server.user(user="deploy")
if result.did_change():  # Always False at prepare time!
    server.shell(commands=["bootstrap"])

# GOOD: Use _if for execute-time conditionals
result = server.user(user="deploy")
server.shell(commands=["bootstrap"], _if=result.did_change)
```

### Anti-Pattern 3: Using Mutable Facts for Guards

```python
# RISKY: Disk space can change between fact gathering and execution
from pyinfra.facts.server import Command
free_space = host.get_fact(Command, command="df / --output=avail | tail -1")

# BETTER: Use immutable facts (OS name, architecture, Which)
```

### Anti-Pattern 4: Forgetting StringIO for String Content

```python
# BAD: Treats the string as a file path
files.put(src="some content\n", dest="/etc/file")

# GOOD: Use StringIO for string content
from io import StringIO
files.put(src=StringIO("some content\n"), dest="/etc/file")
```

### Anti-Pattern 5: Not Using the _if Argument

```python
# Fragile: Python-level conditional based on facts
if not host.get_fact(Which, command="myapp"):
    server.shell(commands="install-myapp.sh")

# Better for dependent operations: use _if
install_op = apt.packages(packages=["myapp"])
server.shell(
    commands="configure-myapp",
    _if=install_op.did_change,
)
```

Note: Using facts in Python conditionals IS valid for initial guard checks
(like "skip everything if already installed"). The anti-pattern is using it
for inter-operation dependencies where `_if` should be used.

### Anti-Pattern 6: Imports in group_data Files

Python imports in group_data files can cause `debug-inventory` to fail because
pyinfra tries to serialize all module-level variables. Be cautious with imports
in inventory/group_data files.

### Anti-Pattern 7: Not Specifying Full Dest Path with StringIO

```python
# BAD: TypeError when dest is a directory
files.put(src=StringIO("content"), dest="/etc/app/")

# GOOD: Always specify full file path
files.put(src=StringIO("content"), dest="/etc/app/config.txt")
```

### Anti-Pattern 8: Installing pyinfra System-Wide

Always use virtual environments (venv, uv, or pipx):
```bash
uv tool install pyinfra    # Recommended
pipx install pyinfra        # Alternative
pip install pyinfra          # In a venv only
```

---

## Summary of Key Takeaways

1. **Use dedicated operations** over server.shell whenever possible
2. **Tuple format in inventory** is correct and idiomatic for per-host data
3. **Wrap string content in StringIO** for files.put -- raw strings are file paths
4. **Use `_if` for execute-time conditionals** -- never check operation results
   at prepare time
5. **Only use immutable facts** for prepare-time conditionals
6. **Use `@deploy` decorator** for reusable packages, plain functions for
   project-internal modules
7. **Set `_sudo` in host data** for deploy-wide defaults
8. **Test with `--dry`** and `--debug-operations` before real execution
9. **Use `_retries`** for unreliable network operations
10. **Keep secrets in environment variables** or encrypted group_data

---

## Sources

- [PyInfra Getting Started](https://docs.pyinfra.com/en/3.x/getting-started.html)
- [Using Operations](https://docs.pyinfra.com/en/3.x/using-operations.html)
- [Inventory & Data](https://docs.pyinfra.com/en/3.x/inventory-data.html)
- [Packaging Deploys](https://docs.pyinfra.com/en/3.x/api/deploys.html)
- [Writing Operations](https://docs.pyinfra.com/en/3.x/api/operations.html)
- [Writing Facts](https://docs.pyinfra.com/en/3.x/api/facts.html)
- [Files Operations](https://docs.pyinfra.com/en/3.x/operations/files.html)
- [Server Operations](https://docs.pyinfra.com/en/3.x/operations/server.html)
- [Groups & Roles Example](https://docs.pyinfra.com/en/3.x/examples/groups_roles.html)
- [Dynamic Inventories](https://docs.pyinfra.com/en/2.x/examples/dynamic_inventories_data.html)
- [Secret Storage](https://docs.pyinfra.com/en/2.x/examples/secret_storage.html)
- [Deploy Process](https://docs.pyinfra.com/en/2.x/deploy-process.html)
- [FAQ](https://docs.pyinfra.com/en/3.x/faq.html)
- [CLI Reference](https://docs.pyinfra.com/en/3.x/cli.html)
- [PyInfra DeepWiki](https://deepwiki.com/pyinfra-dev/pyinfra)
- [GitHub Issues - files.put StringIO #1144](https://github.com/pyinfra-dev/pyinfra/issues/1144)
- [GitHub Issues - Imports in group_data #1297](https://github.com/pyinfra-dev/pyinfra/issues/1297)
- [GitHub Issues - Fact errors #1104](https://github.com/pyinfra-dev/pyinfra/issues/1104)
- [GitHub Discussions - Documentation Feedback #1168](https://github.com/pyinfra-dev/pyinfra/discussions/1168)
- [@local Connector](https://docs.pyinfra.com/en/next/connectors/local.html)

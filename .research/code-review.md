# Code Review

Review of the dev-machine-setup codebase against PyInfra best practices and general correctness.

---

## Bugs

### BUG-1: `files.put` with raw string src (chrome.py, one_password.py)

**Severity: High — likely broken at runtime**

Both `ops/chrome.py:30-35` and `ops/one_password.py:57-62` pass a raw string to `files.put(src=...)`:

```python
# chrome.py
CHROME_SOURCE_LINE = (
    f"deb [arch=amd64 signed-by={CHROME_KEYRING}] "
    "http://dl.google.com/linux/chrome/deb/ stable main\n"
)
files.put(src=CHROME_SOURCE_LINE, dest=CHROME_LIST, _sudo=True)
```

`files.put`'s `src` parameter expects a **file path** or a **file-like object**, not a string of content. Passing the repo line string means PyInfra tries to open it as a file path, which will fail or produce wrong results.

**Fix:** Wrap in `StringIO`:

```python
from io import StringIO
files.put(src=StringIO(CHROME_SOURCE_LINE), dest=CHROME_LIST, _sudo=True)
```

Same fix needed in `ops/one_password.py` for `REPO_LINE`.

---

### BUG-2: `preinstall_setup` defined in wrong file

**Severity: Medium — import will fail**

`deploy.py:3` imports `from ops.pre_install import preinstall_setup`, but `preinstall_setup()` is actually defined in `ops/base.py:5`, not `ops/pre_install.py`. The file `ops/pre_install.py` was read and its content is the `preinstall_setup` function, but the filename on disk is `ops/base.py` based on the comment header.

Wait — looking again, both `ops/pre_install.py` and `ops/base.py` have the header `# ops/base.py`. The pre_install.py file contains `preinstall_setup()` and the base.py file contains `install_base()` / `uninstall_base()`, but the comment in pre_install.py says `# ops/base.py`. This is a misleading comment but likely harmless since the import path is correct. The import `from ops.pre_install import preinstall_setup` should work if the file on disk is `ops/pre_install.py` with that function in it.

**Actual issue:** The comment `# ops/base.py` at the top of `ops/pre_install.py` is wrong — it should say `# ops/pre_install.py`.

---

### BUG-3: Stale root-level `dotfiles.py`

**Severity: Low — git hygiene**

Git status shows `dotfiles.py` staged at the repo root (`AD` status — added then deleted) and an untracked `ops/dotfiles.py`. The file was moved to `ops/` but staging is out of sync. `deploy.py` imports from `ops.dotfiles`, which is correct, but the dangling staged file should be cleaned up.

---

## Issues

### ISSUE-1: No `ops/__init__.py`

**Severity: Medium — may work by accident**

The `ops/` directory has no `__init__.py`. PyInfra may handle imports differently than standard Python, but for correctness and IDE support, an empty `__init__.py` should exist. If this currently works, it's because Python 3 supports implicit namespace packages, but adding the file makes the intent explicit.

---

### ISSUE-2: `server.shell` used where dedicated operations exist

**Severity: Low — works but not idempotent by design**

`server.shell` is explicitly non-idempotent in PyInfra — it always generates commands regardless of current state. Your `test -f || ...` and `test -d || ...` guards make the *shell commands* themselves idempotent, which is a reasonable workaround. However, a few places could use dedicated operations instead:

- **`ops/one_password.py:72-78`** — downloading the debsig policy file uses `curl | tee`. This could use `files.download` if the URL serves the file directly (no dearmoring needed).

The keyring installations (`curl | gpg --dearmor`) genuinely have no dedicated operation equivalent, so `server.shell` with guards is the right call there.

---

### ISSUE-3: Guard runs even when 1Password is already installed

**Severity: Low — unnecessary work**

In `ops/one_password.py:145-157`, when both `1password` and `op` are present, the function still calls `_ensure_shell_ssh_auth_sock()`, which runs 5 `files.line` / `files.directory` operations every time. These are idempotent (PyInfra checks state), so it's correct but generates noise in output. Consider guarding the shell config behind its own check or accepting the noise.

---

### ISSUE-4: Oh-My-Zsh installer piped from curl to sh

**Severity: Low — standard practice but worth noting**

`ops/zsh.py:43-48` pipes a remote script directly into `sh`:

```python
f'sh -c "$(curl -fsSL {OMZ_INSTALLER_URL})"'
```

This is how Oh-My-Zsh officially recommends installing, so it's expected. But for a reproducible setup, consider pinning to a specific commit hash in the URL rather than `master`.

---

### ISSUE-5: Chrome repo uses HTTP, not HTTPS

**Severity: Low — mitigated by GPG signing**

`ops/chrome.py:8-9` uses `http://dl.google.com/linux/chrome/deb/` (note: HTTP, not HTTPS) for the repo URL. The GPG signing mitigates tampering risk, but HTTPS would add transport-layer protection. Google does support `https://dl.google.com/...` for this repo.

---

### ISSUE-6: Hardcoded user in inventory

**Severity: Low — design choice**

`inventory.py` hardcodes `"user": "eriksalt"`. This is fine for a personal setup script but limits reuse. Could be derived from environment (`os.getenv("USER")`) if portability is desired.

---

## Style / Structure Observations

### What's done well

- **Project structure** follows PyInfra conventions (`deploy.py`, `inventory.py`, `ops/` modules).
- **Inventory pattern** using `[("@local", {data})]` is idiomatic.
- **Separation of concerns** — each ops module handles one tool/component.
- **Install/uninstall pairs** — every module provides both directions.
- **Guard patterns** using `host.get_fact(Which, ...)` are correct prepare-phase checks (facts are available during prepare).
- **`_sudo` in host data** is the cleanest approach for a sudo-everything local setup.
- **`_sudo_user` for user-level operations** (Oh-My-Zsh, dotfiles) is correct.

### Minor style notes

- **Inconsistent comment headers**: `ops/pre_install.py` has `# ops/base.py` as its header comment.
- **No type annotations on uninstall functions**: `install_*` functions have return type hints (`-> None`) but some uninstall functions do too, which is consistent. Good.
- **`from __future__ import annotations`** is used in some files but not all. Consider being consistent.

---

## Summary Table

| ID      | Severity | Category | File(s)                          | Summary                                    |
|---------|----------|----------|----------------------------------|--------------------------------------------|
| BUG-1   | High     | Bug      | chrome.py, one_password.py       | `files.put(src=string)` — src is a path, not content |
| BUG-2   | Medium   | Bug      | pre_install.py                   | Wrong comment header (cosmetic, not functional) |
| BUG-3   | Low      | Bug      | dotfiles.py (root)               | Stale staged file in git                   |
| ISSUE-1 | Medium   | Structure| ops/                             | Missing `__init__.py`                      |
| ISSUE-2 | Low      | Practice | one_password.py                  | `server.shell` where `files.download` could work |
| ISSUE-3 | Low      | Practice | one_password.py                  | SSH sock config runs unconditionally        |
| ISSUE-4 | Low      | Security | zsh.py                           | Oh-My-Zsh installer pinned to `master`     |
| ISSUE-5 | Low      | Security | chrome.py                        | Repo URL uses HTTP instead of HTTPS        |
| ISSUE-6 | Low      | Design   | inventory.py                     | Hardcoded username                         |

**Recommended fix priority:** BUG-1 first (likely runtime failure), then ISSUE-1, then the rest as desired.

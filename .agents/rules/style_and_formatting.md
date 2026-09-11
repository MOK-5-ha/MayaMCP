# Style, Linting & Formatting Rules

This document defines code style, linter rules, type checking, version control hygiene, and shell command preferences for MayaMCP.

---

## 1. Python Linting & Formatting

- **Ruff Configuration**:
  - Max line length: `88` characters.
  - Python target version: `py38`.
  - Active rules: `E` (pycodestyle errors), `W` (pycodestyle warnings), `F` (Pyflakes), `I` (isort imports), `B` (flake8-bugbear), `C4` (flake8-comprehensions), `UP` (pyupgrade).
  - Check command: `ruff check src/ tests/`
  - Auto-fix command: `ruff check --fix src/ tests/`

---

## 2. Static Type Checking

- **Mypy Configuration**:
  - Target: `src/` directory.
  - Check command: `mypy src/`
  - Pydantic v2 schemas: All schemas must define explicit type annotations and field validators where required.

---

## 3. Git & Pre-Commit Hygiene

- **Feature Branch Workflow**: All changes must occur on dedicated feature branches within an isolated git worktree (`feature/<feature-name>`). Direct commits or pushes to `main` or `master` are strictly prohibited.
- **Pre-Commit Artifact Check**: Before staging files, verify that no `.env` files, API keys, or `.sqlite` WAL files are included in the commit payload.
- **Conventional Commits**: Use semantic commit prefixes (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`) with concise descriptions.
- **No Autonomous Merging**: Pull requests must be reviewed and merged by human developers. AI agents are strictly forbidden from autonomous merging.

---

## 4. Shell & Command Preferences

- **Preferred File Operations**:
  - Use `rsync` for copying and moving project files (`rsync -avhP SOURCE/ DEST/`).
  - Use `tee` for writing or appending file contents from shell pipelines (`command | tee FILE` or `command | tee -a FILE`).
  - Disallowed command families: Avoid `mv`, `cp`, and raw shell redirection operators (`>`, `>>`) as default file manipulation methods.
- **Rust Toolchain Configuration**:
  - When building Rust extensions (e.g. PyO3, Maturin) in local virtual environments, prepend the local toolchain binary directory:
    ```bash
    export PATH="/Users/pretermodernist/.rustup/toolchains/stable-x86_64-apple-darwin/bin:$PATH"
    pip install -e .
    ```

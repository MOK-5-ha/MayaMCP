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

## 3. Git, GitHub CLI (gh) & Operational Guardrails

- **Feature Branch Workflow**: All changes must occur on dedicated feature branches within an isolated git worktree (`feature/<feature-name>`, `fix/<fix-name>`, `chore/<chore-name>`). Direct commits or pushes to `main` or `master` are strictly prohibited.
- **GitHub CLI (`gh`) Operational Discipline**: All GitHub operations (opening PRs, viewing review comments, inspecting CI/CD runs) must route through the official `gh` CLI paired with companion skills rather than stateless GitHub MCP servers.
- **No Autonomous Merging**: You may create Pull Requests via `gh pr create` and inspect reviews via `gh pr view`, but you are strictly forbidden from merging Pull Requests via the terminal (`gh pr merge` is prohibited) or any API. A human developer must review and merge all code.
- **Output Token Hygiene for `gh` Queries**: Never execute bare `gh` commands that dump unbounded JSON or table rows. Always constrain queries using `--json <fields>`, `--limit <N>`, or pipe through `jq` (e.g., `gh pr list --limit 10 --json number,title,author,headRefName,state`).
- **Remote & Exfiltration Protection**: Never execute `git remote add*`, `git remote set-url*`, or `git remote remove*`. Never execute `git submodule add*` or `git submodule update --init*` to prevent remote repository tampering or untrusted code exfiltration.
- **No Destructive API / CLI Actions**: Repository deletion, branch protection tampering, and visibility modifications are blocked at the token level and strictly prohibited by rule.
- **Pre-Commit Artifact Check**: Before staging files via `git add`, verify that no `.env` files, API keys, credentials, or `.sqlite` WAL files are included in the commit payload.
- **Conventional Commits**: Use semantic commit prefixes (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`) with concise descriptions.

---

## 4. Shell & Command Preferences

- **Preferred File Operations**:
  - Use `rsync` for copying and moving project files (`rsync -avhP SOURCE/ DEST/`).
  - Use `tee` for writing or appending file contents from shell pipelines (`command | tee FILE` or `command | tee -a FILE`).
  - Disallowed command families: Avoid `mv`, `cp`, and raw shell redirection operators (`>`, `>>`) as default file manipulation methods.
- **CLI Output Hygiene & Token Conservation Protocol**:
  - **Mandatory Projection Flags**: On tools with structured output support (`gh`, `gcloud`, `aws`, `docker`), always specify output projections:
    - `gh`: Use `--json <field1,field2>` and `--limit <N>` (or `--template`)
    - `gcloud`: Use `--format="value(field)"` or `--format="table(field1,field2)"`
    - `docker`: Use `--format "{{.ID}}: {{.Names}} ({{.Status}})"`
  - **Unix Pipeline Filtering**: Filter raw text streams before they reach model context. Pipe through `jq`, `head -n <N>`, `grep`, `awk`, or `cut` (e.g., `gh run view <id> --log-failed | head -n 50`).
  - **Scratch File Buffering for Large Outputs**: If a diagnostic command or test run generates more than 100 lines of logs, redirect or tee it to the conversation scratch directory and inspect targeted segments with `grep` or `head` rather than dumping the full trace into context.
  - **Atomic Pipelines Over Chatty Turns**: Prefer chaining commands in a single shell invocation using `&&` or pipelines (`|`) rather than executing separate single-command tool calls across multiple conversational turns.
- **Rust Toolchain Configuration**:
  - When building Rust extensions (e.g. PyO3, Maturin) in local virtual environments, prepend the local toolchain binary directory:
    ```bash
    export PATH="$HOME/.rustup/toolchains/stable-x86_64-apple-darwin/bin:$PATH"
    pip install -e .
    ```

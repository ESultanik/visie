# Git hooks for visie development

This directory holds optional Git hooks for visie. They run the same checks as
continuous integration, so you find problems before you push.

## Enable the hooks

The hooks are opt-in. After you clone the repository, run this from the
repository root:

```bash
git config core.hooksPath ./hooks
```

To turn the hooks off again, run `git config --unset core.hooksPath`.

The hooks run the project's tools through `uv`, so install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and run `uv sync`
before you enable them. If `uv` is missing, a hook stops the operation and tells
you what to install.

## What the hooks check

### `pre-commit`

*   Rejects new files whose names contain non-ASCII characters, which cause
    problems on other platforms. To allow them, run
    `git config hooks.allownonascii true`.
*   Runs `uv run ruff check .` to lint the code.
*   Runs `uv run ruff format --check .` to confirm the formatting is current.
*   Runs `uv run ty check` to type-check the code.
*   Runs `git diff-index --check` to find whitespace errors in the staged
    changes.

The lint, format, and type checks cover the whole working tree rather than only
the staged files, which matches what continuous integration runs.

### `pre-push`

*   Runs `uv run pytest` over the test suite.

## Bypass a hook

When a check blocks a commit or a push that you still need to make, such as
recording work in progress on a branch of your own, pass `--no-verify`:

```bash
git commit --no-verify
git push --no-verify
```

Continuous integration runs the same checks, so a bypassed commit fails there
instead. Reserve `--no-verify` for the cases that need it.

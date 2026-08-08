You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-pm83uv4q\rtk\rtk_status
Case: rtk_status

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Implement `count_status` in work.py. Return a dict with integer keys counting each status token after `status=`. Use a Bash-style command sequence (or the host's equivalent) to inspect the workspace before editing: list the tree, search for TODO and the function name, read the fixture, inspect the diff, and count files/lines. Run a focused verification command after editing. Use the host's shell syntax where needed; do not add dependencies or change the public API.

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms in that response.

## RTK treatment instructions
# RTK - Rust Token Killer (Codex CLI)

**Usage**: Token-optimized CLI proxy for shell commands.

## Rule

Always prefix shell commands with `rtk`.

Examples:

```bash
rtk git status
rtk cargo test
rtk npm run build
rtk pytest -q
```

## Meta Commands

```bash
rtk gain            # Token savings analytics
rtk gain --history  # Recent command savings history
rtk proxy <cmd>     # Run raw command without filtering
```

## Verification

```bash
rtk --version
rtk gain
which rtk
```

You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-pm83uv4q\rtk\pony_strip_version
Case: pony_strip_version

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Implement `strip_version` in work.py. Remove one leading `v` from a version string; leave other values unchanged. Read the existing helper in helpers.py first. Keep the requested API and behavior; do not add dependencies, classes, configuration, or unrelated files. Run one focused check.

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

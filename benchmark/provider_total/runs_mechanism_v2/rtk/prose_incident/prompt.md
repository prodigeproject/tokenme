You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-pm83uv4q\rtk\prose_incident
Case: prose_incident

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Read incident.md. Do not modify the fixture. In your final response, write a clear 350-500 word report for an engineering manager with exactly these section headings: `Impact`, `Root cause`, `Mitigation`, `Next action`. Include every fact below, without inventing numbers: queue backlog peaked at 18,400; root cause was a missing retry bound; mitigation was rate limiting. End with one concrete next action.

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

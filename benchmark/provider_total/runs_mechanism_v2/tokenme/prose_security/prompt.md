You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-pm83uv4q\tokenme\prose_security
Case: prose_security

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Read security.md. Do not modify the fixture. In your final response, write a clear 350-500 word report for an engineering manager with exactly these section headings: `Threat`, `Control`, `Residual risk`, `Next action`. Include every fact below, without inventing numbers: threat is path traversal; control is canonicalization plus containment; residual risk is symlink replacement. End with one concrete next action.

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms in that response.

## TokenMe compiled policy
TokenMe: be concise without losing correctness. Preserve safety, security, validation, accessibility, explicit requirements, exact identifiers, and needed checks. Reuse existing code/native APIs; avoid speculative work, repetition, and unrelated changes. Code: inspect before editing; choose the smallest readable correct change; reuse helpers/stdlib; do not add dependencies or abstractions without need; run one focused check when useful.

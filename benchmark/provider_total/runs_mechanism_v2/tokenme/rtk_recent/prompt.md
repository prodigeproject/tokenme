You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-pm83uv4q\tokenme\rtk_recent
Case: rtk_recent

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Implement `recent_lines` in work.py. Return the last `limit` non-empty lines, preserving order and defaulting to 2. Use a Bash-style command sequence (or the host's equivalent) to inspect the workspace before editing: list the tree, search for TODO and the function name, read the fixture, inspect the diff, and count files/lines. Run a focused verification command after editing. Use the host's shell syntax where needed; do not add dependencies or change the public API.

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms in that response.

## TokenMe compiled policy
TokenMe: be concise without losing correctness. Preserve safety, security, validation, accessibility, explicit requirements, exact identifiers, and needed checks. Reuse existing code/native APIs; avoid speculative work, repetition, and unrelated changes. Code: inspect before editing; choose the smallest readable correct change; reuse helpers/stdlib; do not add dependencies or abstractions without need; run one focused check when useful. Tools: request the smallest output that answers the question; prefer targeted searches, summaries, bounded slices, quiet flags, and focused tests; keep dense or security-sensitive context intact.

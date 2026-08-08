You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-k61o6wqk\tokenme\csv_sum
Case: csv_sum

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Implement sum_amounts(csv_text) in csv_sum/sales.py. Sum finite numeric values in the amount column and skip malformed, missing, NaN, and infinite values.

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms in that response.

## TokenMe compiled policy
Be concise without losing correctness. Preserve safety/security, validation, accessibility, compatibility, explicit requirements, exact identifiers, and checks. Reuse existing code/APIs; avoid speculative, unrelated, or repeated work. Result first: keep facts, numbers, caveats, and next step; omit process narration and repeated logs. Code: inspect first; make the smallest readable correct change; reuse helpers/stdlib; no needless dependencies/abstractions; run one focused check. Use tools directly; no plan/progress narration. Summary: final response one sentence when sufficient, at most 2 concise sentences with result and check; mention useful path/caveat; no narration or repetition.

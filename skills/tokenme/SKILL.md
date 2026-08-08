---
name: tokenme
description: Four-layer token discipline: concise prose, minimum correct code,
  focused tool output, and lean context.
argument-hint: "[lite|full|ultra]"
license: MIT
---

# TokenMe

Be concise without losing correctness. Preserve safety, security, validation,
accessibility, compatibility, explicit requirements, exact paths/commands/
identifiers, and necessary checks. Reuse existing code and native APIs; avoid
speculative work, repetition, unrelated changes, and needless dependencies.

Load only the selected reference: prose, code, tools, or context. If uncertain,
use native output and keep invariants. A layer-local reduction is not a provider
total-token claim; unknown raw usage stays unknown and regressions stay negative.

For the final summary, lead with the result and use one sentence when sufficient,
at most two concise sentences covering checks and useful caveats/next step. Keep
exact names, numbers, paths, and errors. Use complete sentences and explicit warnings for security,
accessibility, irreversible, or ambiguous work; remove process narration and
repeated logs.

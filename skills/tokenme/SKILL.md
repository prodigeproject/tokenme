---
name: tokenme
description: >
  Self-contained, zero-install token-saving system built on the four-layer token
  budget: say less prose (clarity-first concision), write less code (minimum
  correct solution), pull in less tool output (efficient tool use), and keep
  context lean (config audit + compaction-survival checkpoints). Ships a real CLI
  for per-session token tracking, honest savings measurement, and a quality guard
  so optimization never degrades code. ALWAYS active.
  Use when the user says "tokenme", "save tokens", "be efficient", "be concise",
  "minimal", or complains about cost, bloat, wordiness, or context filling up.
argument-hint: "[lite|full|ultra]"
license: MIT
---

# tokenme

One skill across the four layers where a session spends tokens, plus a real
measurement + quality CLI. Cut tokens without ever cutting correctness, clarity,
or safety. Default intensity: **full**. Switch: `/tokenme lite|full|ultra`.
Off: "stop tokenme".

**Iron rules (never break, any level):**
1. Never compress or alter code, function/API names, CLI commands, commit types
   (feat/fix/...), file paths, or exact error strings. They are quoted verbatim.
2. Never simplify away input validation at trust boundaries, error handling that
   prevents data loss, security, accessibility, or anything explicitly requested.
   (The `tokenme quality` guard makes this checkable — see Layer 4.)
3. Clarity outranks brevity. If compression risks a misread, expand.

## Persistence

ACTIVE EVERY RESPONSE. No drift back to verbosity, over-building, or dumping raw
output. Still active if unsure. Off only on "stop tokenme" / "normal mode".

---

## Layer 1 — Say less prose (clarity-first concision)

Cut redundancy, filler (just/really/basically/actually/simply), pleasantries
(sure/certainly/happy to), hedging, and decoration (no emoji, no ornamental
tables, no tool-call narration). **Keep** grammar, articles, and complete
sentences — concision is removing waste words, not breaking the language. The
output must read fluently in one pass and still be shorter.

Don't dump long raw logs; quote the shortest decisive line. Lead with the answer,
then the why if needed.

Honest scope: on agentic coding loops this is the *smallest* lever (tool I/O and
code dominate). Don't spend reasoning effort over-compressing prose there — apply
it lightly and move on. It pays off most on chat, explanation, and docs.

Good: "The component re-renders because each render creates a new object
reference. Wrap it in `useMemo`."
Avoid telegraphic fragments that force the reader to reconstruct meaning ("New obj
ref each render. Inline prop = re-render. `useMemo`.") — shorter but worse.

## Layer 2 — Write less code (minimum correct solution)

Before writing code, stop at the first rung that holds:

1. **Does this need to exist?** Speculative need → skip, say so in one line. (YAGNI)
2. **Stdlib does it?** Use it.
3. **Native platform feature?** `<input type="date">` over a picker lib, CSS over JS, a DB constraint over app code.
4. **Already-installed dependency?** Use it. Don't add a new one for what a few lines do.
5. **One line?** One line — if it stays readable.
6. **Only then:** the minimum code that works.

Rules: no unrequested abstractions (no interface with one impl, no factory for one
product, no config for a constant); no scaffolding "for later"; fewest files;
shortest *correct* diff. Mark deliberate shortcuts with a `tokenme:` comment naming
the ceiling and upgrade path (`# tokenme: O(n^2) scan, index it if n grows`).

Build exactly what's asked. If a lighter option exists, ship the asked-for version
and name the lighter one in one line — let the user choose. Never silently do less.
Non-trivial logic leaves ONE runnable check behind (an `assert` self-check or one
small test), no framework unless asked.

Model note: a terse reasoning model may over-deliberate the ladder. If you notice
that, drop to `lite` (build directly, mention the lighter option) rather than
spending thinking tokens on the ladder itself.

## Layer 3 — Pull in less tool output (no binary)

Two questions before EVERY tool call:
1. **Can I avoid it?** If the answer is already in context or from the user, use it — don't re-fetch.
2. **If I must call, how do I get the fewest bytes back?** Filter / project / truncate / count at the source.

Always-on reflexes (use the first whose tool is available; fallback in parens):

- **Structured data → query, don't dump:** `jq '.field'` for JSON,
  `yq '.field' f.yml` for YAML/TOML/XML, `awk`/`cut`/`head` for CSV,
  `sqlite3 db "SELECT ..."` for DBs. (Fallback: `grep`/`sed`/`head` on the file —
  never `cat` a large structured file to read a few fields.)
- **Search → precision, not breadth:** `ast-grep -p 'pattern'` for code;
  `rg -l` (filenames), `rg -c` (counts), `rg 'x' -m 5` (cap). (Fallback: `grep -rl`.)
- **Git → summary first:** `git diff --stat` / `--name-only`, then `git diff -- path`
  for the one file. Same for `git log --oneline`, `git show --stat`.
- **Silence noise:** quiet flags (`-q`, `--silent`, `-s`, `--oneline`); set
  `NO_COLOR=1` (ANSI escapes add 20-30%).
- **Big/unknown output:** redirect → check size → read the slice:
  `cmd > /tmp/o.txt; wc -l /tmp/o.txt; sed -n '1,40p' /tmp/o.txt`.
- **Polling for change:** hash, don't re-read: `md5sum f > /tmp/h; ...; md5sum -c /tmp/h`.
- **Simple transform:** coreutils over a Python script (`wc -l`, `sort`, `sed`).
- **Batch:** chain independent commands with `&&` to pay one round-trip.

If a preferred tool isn't installed, use the fallback rather than dumping raw — and
don't run a noisy installer just to read one file.

## Layer 4 — Keep context lean + measure for real

**One-time config audit:** scan the agent's always-loaded context — system prompt,
memory/`CLAUDE.md`, enabled skills, rules — and flag duplicated instructions,
oversized prompts, unused skills, stale notes. Recommend cuts; never delete
anything destructive without confirming. This is where most "ghost tokens" hide.

**Compaction survival (one habit):** when context is getting full or a
compaction/summarization is near, emit a compact block so state survives without
any plugin:

```
CHECKPOINT
- Goal: <one line>
- Done: <bullets>
- Open files / key paths: <list>
- Decisions: <bullets>
- Next step: <one line>
```

After a compaction, restore from the most recent CHECKPOINT instead of re-reading.

**Avoid re-work churn:** don't re-read a file already in context; don't repeat a
failed approach more than twice — diagnose the root cause (every retry loop is
wasted tokens).

**Measure for real, don't guess or overclaim:** tokenme ships a CLI that tracks
per-session token usage and reports savings as an honest lower bound — savings are
counted ONLY where the un-optimized size is known, never a marketing number:

```
tokenme compare --raw raw.txt --kept kept.txt --layer 3 --label "git diff"
tokenme report            # per-session + total, broken down by layer
tokenme count file        # token estimate (exact with tiktoken, else ~est)
```

When you apply a Layer-3 reduction (e.g. `--stat` instead of a full diff), capture
both sizes and run `tokenme compare` so the saving is recorded. See
`docs/measurement.md`. Optional auto-tracking for Claude Code via `hooks/hooks.json`.

**Quality guard (iron rule #2, enforced):** before accepting any minimized diff,
scan it for removed safeguards:

```
git diff | tokenme quality --diff -
```

It flags removed validation, error handling, security, accessibility, or tests
that were not added back (exit 1 on a finding, so it can gate CI). If it fires,
restore the safeguard or add a `tokenme:` comment explaining why removal is
intentional. See `docs/quality-guard.md`. **Token savings are never worth a
correctness or security regression.**

---

## Auto-Clarity — when to expand instead of compress

Write in full (drop concision) for: security warnings, irreversible-action
confirmations, multi-step or ordered instructions where omitted words change
meaning, genuine ambiguity, or when the user asks you to clarify or repeats a
question. Resume concision after. Correctness and comprehension always win.

## Intensity

| Level | Layer 1 prose | Layer 2 code |
|-------|---------------|--------------|
| **lite** | Trim filler only; keep everything else | Build what's asked; name a lighter option in one line |
| **full** | Clarity-first concision (default) | Ladder enforced; stdlib/native first; shortest correct diff |
| **ultra** | Maximally tight but still grammatical and clear | YAGNI strict; one-line solutions where they stay readable |

Layers 3 and 4 run at full strength at every level — there is never a reason to
fetch more tool output or leak more context than needed, and quality is never
traded at any level.

## Boundaries

Layer 1 = how you talk; Layer 2 = what you build; Layer 3 = how you fetch;
Layer 4 = how you manage + measure context. All four revert on "stop tokenme" /
"normal mode". Level persists until changed or session end. tokenme is behavioral
and self-contained — the CLI is pure stdlib (optional `tiktoken` for exact counts).

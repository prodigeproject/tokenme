# tokenme — the four-layer strategy

One idea: a session's token spend lives on four layers, and you only win by
managing all four together with a meter running. This is how to apply it.

## The four layers, ranked by leverage in an agentic coding session

```
  LEVERAGE   LAYER                    tokenme behavior            WHY IT MATTERS
  ========   ======================   =========================   =================
   highest   4. Context lifecycle     audit + checkpoint habit    compaction loses 60-70% of context
      |      3. Tool input            fetch fewer bytes           tool stdout is the silent context hog
      |      2. Generated code        minimum correct solution    less code = less diff/test/review later
    lowest   1. Output prose          clarity-first concision     real but smallest lever in agentic loops
```

Prose compression feels like the obvious win but is the *smallest* lever when an
agent is doing real work. tokenme weights effort accordingly: it never burns
reasoning tokens over-compressing prose, and puts the muscle into Layers 2-4.

## Layer 1 — Say less prose (clarity-first concision)

Cut filler, hedging, pleasantries, and decoration. **Keep** grammar, articles, and
complete sentences — concision is removing waste words, not breaking the language.
A fluent reader must understand it in one pass *and* find it shorter. On agentic
loops, apply lightly; it pays off most on chat, explanation, and docs.

## Layer 2 — Write less code (minimum correct solution)

Before writing code, stop at the first rung that holds: (1) does it need to exist
(YAGNI), (2) stdlib does it, (3) native platform feature, (4) already-installed
dependency, (5) one line if readable, (6) the minimum that works. Build exactly
what's asked; if a lighter option exists, ship the asked-for version and name the
lighter one in one line. **Never under-build** — minimum *correct*, never
minimum-broken.

## Layer 3 — Pull in less tool output (no binary)

Two questions before every tool call: can I avoid it? if not, how do I get the
fewest bytes back? Reflexes: query structured data (`jq`/`yq`) instead of dumping;
precision search (`rg -c`/`-l`, `ast-grep`); `git diff --stat` before full diffs;
quiet flags + `NO_COLOR=1`; redirect → size-check → read the slice; hash instead of
re-read while polling; coreutils over Python for simple transforms; batch with `&&`.
Each has a coreutils fallback so it works on a bare box.

## Layer 4 — Keep context lean and measure

One-time config audit of always-loaded context (system prompt, memory, skills,
rules) to find duplicated or oversized instructions and unused skills. When context
fills, emit a `CHECKPOINT` block so state survives a compaction without any plugin.
Avoid re-work churn: don't re-read what's in context; don't repeat a failed
approach more than twice. And **measure** — see below.

## Measure for real

token saving without measurement is theatre. tokenme ships the meter:

```
tokenme compare --raw raw.txt --kept kept.txt --layer 3 --label "git diff"
tokenme report      # per-session, by layer, honest lower-bound percentages
```

A saving is counted only where the un-optimized size is actually known, so numbers
are a floor, not a sales pitch. Track the four layers separately to see which habit
is actually paying off.

## Never trade quality for tokens

The fastest way to "save tokens" is to do less work badly. tokenme refuses that.
Before accepting any minimized diff:

```
git diff | tokenme quality --diff -
```

The guard flags removed validation, error handling, security, accessibility, or
tests (exit 1 to gate CI). Restore the safeguard or annotate why removal is
intentional. See `docs/quality-guard.md`.

## How to run a session

1. Install the skill; pick intensity (`lite` / `full` / `ultra`).
2. Let the iron rules protect code, safety, and clarity automatically.
3. Capture before/after sizes on big tool calls and `tokenme compare` them.
4. When context tightens, run the Layer-4 audit and drop a CHECKPOINT.
5. Before committing AI edits, run `tokenme quality`.
6. Read `tokenme report` to see where the tokens actually went.

# Measurement — how tokenme proves it actually saved tokens

tokenme ships a real CLI that tracks token usage per session and reports savings as
an **honest lower bound**, never an invented percentage. Pure standard library;
optional `tiktoken` for exact counts.

## The honesty rule

A "saving" is only ever counted when the **un-optimized size is actually known**:

```
saved = raw_tokens - kept_tokens     (clamped at >= 0, never negative)
```

- `kept` = tokens that really entered context (what you paid for).
- `raw`  = tokens that *would* have entered with no optimization — only set when
  we genuinely measured it (you ran the full command once, or the hook captured
  the pre-truncation length).
- If `raw` is unknown, tokenme records `kept` only and **claims no saving**.

So reported percentages are a floor, not a ceiling — the opposite of a marketing
number you cannot reproduce.

## Token counting

`tokenme count file.txt` → `123 tokens (exact)` or `(~est)`.

- **exact**: `tiktoken` (cl100k_base) is installed. Within a few percent of real
  GPT/Claude tokenization. Enable with `pip install ".[exact]"`.
- **~est**: stdlib heuristic blending a chars/token (~4.0) estimate with a
  token-piece count. Tracks tiktoken to ~10-15% on mixed code+prose. Every number
  is labelled, so you always know which you're looking at.

## Per-session tracking

A session groups events under one id (`TOKENME_SESSION`, or the host's
`CLAUDE_SESSION_ID`, else a per-day id). Storage: `~/.tokenme/sessions/<id>.jsonl`,
one JSON event per line. Override the location with `TOKENME_HOME`.

### Manual (works anywhere, any agent)

```bash
# you avoided a full `git diff` dump by using --stat; prove it:
git diff > /tmp/raw.txt
git diff --stat > /tmp/kept.txt
tokenme compare --raw /tmp/raw.txt --kept /tmp/kept.txt --layer 3 --label "git diff"
# raw:   4120 tokens
# kept:    180 tokens
# saved: 3940 tokens (95.6%, ~est)
# recorded -> session day-20260619
```

### Automatic (Claude Code, optional)

Add `hooks/hooks.json` to your agent (see the file for the path variable). The
`PostToolUse` hook pipes each tool result through `hooks/hook_record.py`, which
estimates the kept tokens and, when the host reports the raw length, the saving.
It is fail-safe: any error exits 0 and never interrupts your session. Remove the
hook to stop tracking. No network, ever.

## Reading the report

```bash
tokenme report               # all sessions, human readable
tokenme report --session day-20260619
tokenme report --json        # machine readable, for dashboards/CI
tokenme sessions             # one line per session
```

Example:

```
session: day-20260619
  events            : 41 (33 with a measured saving)
  tokens kept       : 8,210
  tokens saved      : 22,540 (73.3% of measured, ~est)
  [#################.......] 73.3%
  by layer:
    L2: saved 6,100 tok over 9 events
    L3: saved 16,440 tok over 24 events
------------------------------------------------------------
Note: savings are counted ONLY where the un-optimized size was known.
```

## What each layer contributes

Tag events with `--layer` so the report attributes savings correctly:

- `--layer 1` prose concision (response text)
- `--layer 2` code minimalism (diff size avoided)
- `--layer 3` tool-output reduction (the biggest, easiest to measure)
- `--layer 4` context-lifecycle (checkpoint vs re-read avoided)

This tells you which habit is actually paying off, so you can stop guessing.

## Verify the tooling itself

```bash
python -m tokenme selfcheck                 # built-in assertions
python -m unittest discover -s tests        # full suite
```

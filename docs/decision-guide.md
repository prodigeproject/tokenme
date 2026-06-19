# Decision guide — "I have X problem → tokenme does Y"

Match your symptom to the layer that handles it. One tool, no external installs.

## By symptom

**"My replies are too long / too chatty."**
→ Layer 1. tokenme trims filler, hedging, and decoration but keeps full, readable
sentences — never telegraphic fragments. Use `lite` if you still want everything
spelled out, `full`/`ultra` to tighten more.

**"The agent over-builds — adds deps, writes 400 lines for a 20-line job."**
→ Layer 2. The ladder (YAGNI → stdlib → native → installed dep → one line →
minimum). It builds the *minimum correct* version and names a lighter option in
one line — it never silently does less than asked.

**"`cat`, `grep`, and test runs flood my context."**
→ Layer 3, no binary required. `jq`/`yq` projection, `rg -c`/`-l`,
`git diff --stat` first, `head`/`wc -l` caps, `NO_COLOR=1`, and redirect-then-read.
Each has a coreutils fallback so it works even without `jq`/`rg` installed.

**"Context fills up fast and compaction wipes out what the agent was doing."**
→ Layer 4. Ask tokenme to drop a `CHECKPOINT` block (goal, done, open files,
decisions, next step). After a compaction it restores from that block instead of
re-reading everything — no plugin needed.

**"My always-on context (system prompt / memory / skills) feels bloated."**
→ Layer 4 config audit. tokenme reviews what's loaded every session and flags
duplicates, oversized prompts, unused skills, and stale notes. This is where the
silent majority of context waste actually lives.

**"I can't tell whether any of this is working."**
→ Use the CLI: `tokenme compare` on big tool calls, then `tokenme report` for a
per-session, per-layer breakdown with honest lower-bound percentages.

**"I'm worried saving tokens will make the code worse."**
→ Run `git diff | tokenme quality --diff -` before accepting any AI edit. It fails
if validation, error handling, security, accessibility, or tests were removed.

**"I want the absolute least setup."**
→ Just drop the skill in. The CLI is optional and dependency-free when you want
real numbers.

## By role

- **Solo dev, chat-heavy:** tokenme at `lite`/`full`.
- **Solo dev, agentic coding:** tokenme at `full` (Layers 2-4 do the heavy lifting).
- **Team / cost-accountable / commercial:** tokenme (MIT) + `tokenme report` as the source of truth + `tokenme quality` in CI.
- **Reviewing AI-generated PRs:** Layer 2 to keep diffs minimal, `tokenme quality` to keep them safe.

## Anti-patterns

- Leading with prose compression on agentic work (smallest lever).
- Compressing code, commands, or error strings (never — iron rule #1).
- Under-building to chase a token count (iron rule #2 — minimum *correct*).
- Sacrificing readability for brevity (iron rule #3).
- Optimizing without a before/after number from the CLI.

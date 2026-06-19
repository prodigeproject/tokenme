<p align="center">
  <strong>tokenme</strong><br>
  <em>The four-layer token budget. Measured, guarded, zero-install.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen" alt="zero deps">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey" alt="cross-platform">
  <img src="https://img.shields.io/badge/telemetry-none-brightgreen" alt="no telemetry">
</p>

---

Most "save tokens" tools optimize one thing — shorter replies, or smaller command
output — then market it as the complete answer. **tokenme is different.** It treats
a session's token spend as a four-layer budget, covers all four layers at once,
*measures* the result with a real CLI, and *guards* coding quality so the savings
never come at the cost of broken validation, missing tests, or dropped security
checks.

---

## What makes tokenme different

### 1. The four-layer model (the original idea)

Every session spends tokens in four places. Optimizing one layer while ignoring
the others is why most advice disappoints:

```
                WHERE A SESSION SPENDS TOKENS
  ┌─────────────────────────────────────────────────────┐
  │ Layer 1  Output prose ........ what the model says   │
  │ Layer 2  Generated code ...... how much it writes    │
  │ Layer 3  Tool input .......... stdout into context   │
  │ Layer 4  Context lifecycle ... config bloat +        │
  │                                compaction loss       │
  └─────────────────────────────────────────────────────┘
```

tokenme's behavioral skill covers all four. The CLI measures and attributes
savings to each layer. Layer 3 (tool stdout) is the biggest leak in an agentic
session — and the only one most tools touch.

### 2. A real CLI, not a dashboard you have to install

```bash
tokenme count   file.txt                         # estimate tokens
tokenme compare --raw full.txt --kept stat.txt   # record a saving
tokenme report                                   # per-session, by layer
tokenme quality --diff -                         # guard: safeguard removed?
tokenme audit   ~/.claude/CLAUDE.md              # Layer-4 config audit
tokenme checkpoint --goal "..." --next-step "..."# compaction-survival block
```

Pure Python standard library. No runtime, no daemon, no telemetry, no network.
Install nothing — run from the repo, or `pip install .` to get it on PATH.
Optional: `pip install ".[exact]"` for tiktoken (exact token counts; default is
a labelled heuristic, never overclaimed).

### 3. Honest by construction

Every number tokenme reports is verifiable:

- A saving is counted **only when the un-optimized size is actually known**
  (`saved = raw − kept`, clamped at ≥ 0).
- Method labels are precise: `tiktoken:cl100k_base`, `tiktoken:o200k_base`, or
  `~est` (heuristic) — never a bare `"exact"` that overclaims accuracy for
  non-cl100k models.
- The report shows **coverage %** — what fraction of events were actually
  measured — so a 90% saving on one measured event is not silently presented as
  90% of the whole session.
- Layer tracking is honest about auto-tracking scope: Layer 3 (tool output) is
  tracked automatically via hooks; Layer 1/2/4 can be tracked via hooks or the
  `compare` command.

### 4. A quality guard that actually works

`tokenme quality` scans a diff or before/after files for **two classes of risk**:

- **Removed protective code** — validation, error handling, security checks,
  accessibility, tests — that was deleted and not added back.
- **Weakened logic** — operator loosening (`<=` → `<`), negation removal (`not`
  dropped from a guard), constant-guard substitution (`if True:`), numeric bound
  changes inside conditions.

Unlike simple keyword scanners, it:
- Excludes import/require lines, comment-only lines, and blank lines (no more
  "import bcrypt removed → security flag" false positives).
- Uses a proper `difflib`-based diff for before/after comparison (reindentation
  is not flagged as a removal).
- Counts `added_back` **per hunk**, so removing `authorize()` in hunk A is not
  cancelled by an unrelated `auth` variable in hunk B.
- Reports language (detected from diff headers) and states clearly that it is a
  heuristic — not a proof of safety.

Exit code 0 = clean, 1 = findings. Gate CI with it.

### 5. Layer-4 tooling (real code, not just instructions)

```bash
tokenme audit ~/.claude/CLAUDE.md .kiro/steering/   # find ghost tokens
tokenme checkpoint --goal "Build auth" \
  --done "Schema done" --files auth.py \
  --decisions "Use JWT" --next-step "Write tests"
```

`tokenme audit` scans always-loaded context files for: oversized files (token
count per file), duplicated instruction blocks (fingerprint-based), repeated
instruction phrases, and stale dates (configurable threshold). These are the
"ghost tokens" that load every session without the agent ever using them.

`tokenme checkpoint` generates a compact CHECKPOINT block (~60-80 tokens) that
survives a compaction. `tokenme` can parse it back (`layer4.parse_checkpoint`) to
restore state. No plugin, no hook, no daemon required.

---

## Honest limitations

tokenme is behavioral where it counts on the model complying. For guarantees:

| What you want | tokenme | add-on |
|---|---|---|
| Behavioral token reduction | ✅ skill | — |
| Real per-session measurement | ✅ CLI | — |
| Quality guard on diffs | ✅ CLI | — |
| Layer-4 context audit | ✅ CLI | — |
| Deterministic tool-output compression (no model compliance needed) | proxy behavior via skill | `rtk` binary (optional) |
| Live dashboard + hook-enforced compaction (non-commercial) | manual via CLI | `token-optimizer` plugin (optional) |
| Exact token counts for Claude's proprietary tokenizer | `~est` (±10-15%) | not publicly available |

The measurement is self-reported (you supply `raw` and `kept`). There is no tie to
a billing API. This is a limitation compared to tools that read actual session
transcripts — stated openly.

---

## Install

```bash
# Option 1 — run from the repo (no install, no dependencies)
git clone https://github.com/your-handle/tokenme
cd tokenme
python -m tokenme selfcheck            # verify it works

# Option 2 — install on PATH (stdlib only)
pip install .
tokenme selfcheck

# Option 3 — with exact token counting
pip install ".[exact]"                 # adds tiktoken
```

**Windows:** use `bin\tokenme.ps1` or `bin\tokenme.cmd` from the repo, or
`pip install .` to get `tokenme` on PATH. The hooks use `python` (not `python3`)
on Windows — see `hooks/hooks.json` for per-platform setup.

---

## Skill install (the behavioral layer)

```bash
# Claude Code
cp -r skills/tokenme ~/.claude/skills/

# Any agent with a skills / rules folder
cp skills/tokenme/SKILL.md <your-agent-skills-folder>/
```

Trigger: `/tokenme`, "save tokens", "be efficient", "be concise", "minimal".
Intensity: `/tokenme lite|full|ultra`. Off: "stop tokenme".

---

## Auto-tracking hooks (optional)

Add entries from `hooks/hooks.json` to your agent's hook config. Hooks cover:
- **L3** (tool output): `PostToolUse` on Bash/Read/Grep/Glob/MCP tools.
- **L2** (code written): `PostToolUse` on Write/Edit tools.
- **L1** (response text): `Stop` event.

All hooks are fail-safe (exit 0 on any error), 100% local, and can be removed
at any time to stop tracking. Set `TOKENME_DIR` to the repo root.

---

## Quick demo

```bash
# Measure a real Layer-3 saving
git diff > /tmp/raw.txt
git diff --stat > /tmp/kept.txt
tokenme compare --raw /tmp/raw.txt --kept /tmp/kept.txt --layer 3 --label "git diff"
# raw:       4120 tokens
# kept:        180 tokens
# saved:      3940 tokens  (95.6%, ~est)

# Layer-4 config audit
tokenme audit ~/.claude/CLAUDE.md
# [oversized] CLAUDE.md: ~4200 tokens — consider trimming
# [repeated_instruction] 'always respond in': appears 4× — may be redundant

# Quality guard in CI
git diff origin/main | tokenme quality --diff -
# quality guard: HIGH RISK (detected: python) — review before accepting.
#   [weakened_logic] 1 net removed
#       - operator loosened: '<=' removed from guard while '<' appears in replacement

# Generate a compaction-survival checkpoint
tokenme checkpoint --goal "Migrate DB schema" \
  --done "Models updated" "Alembic revision created" \
  --files models.py migrations/001.py \
  --decisions "Postgres 15" "Zero-downtime migration" \
  --next-step "Run migration in staging"
```

---

## Project layout

```
tokenme/
├── README.md
├── STRATEGY.md              the four-layer playbook
├── pyproject.toml
├── skills/tokenme/SKILL.md  behavioral skill (all 4 layers, iron rules)
├── tokenme/                 CLI package
│   ├── estimate.py          token counting (honest labels, no bare "exact")
│   ├── tracker.py           per-session tracking + lock-safe JSONL append
│   ├── quality.py           quality guard (logic-weakening + protective code)
│   ├── layer4.py            config audit + checkpoint generate/parse
│   └── cli.py               count / compare / report / quality / audit / checkpoint
├── hooks/                   optional auto-tracking
│   ├── hook_record.py       Layer 3 (tool output)
│   ├── hook_response.py     Layer 1+2 (response + code written)
│   └── hooks.json           hook config (macOS/Linux/Windows variants)
├── bin/                     launchers (bash, PowerShell, CMD)
├── tests/                   38 unit tests
└── examples/before-after.md real before/after with token counts
```

---

## Verify

```bash
python -m tokenme selfcheck                 # 43 built-in assertions
python -m unittest discover -s tests        # 38 unit tests
```

---

## License

MIT — free for any use, including commercial.
No telemetry. No network calls. No external dependencies.

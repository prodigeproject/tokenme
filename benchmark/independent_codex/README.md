# Independent Codex pilot

This directory records a small, independent, artifact-producing comparison of
four instruction conditions:

- `baseline`: no token-minimization skill;
- `tokenme`: the complete local TokenMe skill was mandatory;
- `caveman`: the complete local Caveman skill was mandatory;
- `ponytail`: the complete local Ponytail skill was mandatory.

It is a pilot, not evidence of provider-billed token or cost savings. The Codex
subagent interface used for these runs does not expose total input, cached
input, reasoning, tool-result, or billed tokens.

## Protocol

Each arm had three isolated subagents. Every subagent received a private copy of
the same five-file template, could not inspect `score.py` or another run, and
was instructed to implement all five tickets. Treatment arms were additionally
required to read and follow the complete corresponding `SKILL.md`. The baseline
received no skill.

The common task prompt was:

```text
You are one isolated cell in a coding benchmark. Do not read or modify anything
outside <RUN_DIRECTORY>. Do not inspect the benchmark scorer or any other
arm/replicate. Implement all five tickets below in that workspace, making
production-reasonable choices. Run any focused checks you need.

Tickets:
1) safe_path/uploads.py: implement safe_upload_path(base_dir, filename).
   filename is untrusted. A normal filename must resolve inside base_dir;
   traversal must be rejected.
2) auth_token/auth.py: implement verify_token(token, secret), returning user id
   only when the HMAC-SHA256 signature produced by make_token is valid;
   malformed/forged tokens return None.
3) reuse_slug/posts.py: implement post_slug(title) using the canonical behavior
   already present in this mini-codebase.
4) csv_sum/sales.py: implement sum_amounts(csv_text), summing valid numeric
   values in the amount column while skipping malformed rows.
5) date_picker/DatePicker.tsx: add an accessible React date-picker component
   with a label, controlled value, and onChange callback. Use only what this
   ticket needs.

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms.
```

All runs used the same Codex model family and the same five tickets in one
session. A run therefore is the independent unit; the five checks inside it are
not five independent samples.

## Reproduce scoring

From the repository root in PowerShell:

```powershell
$runs = Get-ChildItem benchmark\independent_codex\runs -Directory |
  ForEach-Object { Get-ChildItem $_.FullName -Directory } |
  Sort-Object FullName |
  ForEach-Object { $_.FullName }
python benchmark\independent_codex\score.py @runs
```

The scorer checks the five requested behaviors and counts nonblank,
non-comment implementation lines added relative to `template/`. Test code is
reported separately. `FINAL_RESPONSE.md` length was tokenized after the run
with both `cl100k_base` and `o200k_base`; neither tokenizer is a claim about
the unavailable provider bill.

See `RESULTS.json` for raw rows and the repository-root audit for interpretation.


Implemented `redact_tokens` in `work.py`.

It now replaces every non-empty, whitespace-delimited `token=<value>` with `token=[REDACTED]` while preserving all other text. Focused verification passed for fixture-style input, multiple tokens, empty values, and unchanged text.

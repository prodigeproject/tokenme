Implemented `redact_tokens` in `work.py`. It now replaces every non-whitespace value following `token=` with `[REDACTED]` while preserving all other text.

Focused verification passed, including multiple tokens, unchanged non-token text, and an empty `token=` value.

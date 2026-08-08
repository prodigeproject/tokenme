Implemented `redact_tokens` in `work.py` using a focused regex replacement. It now replaces each non-whitespace `token=<value>` value with `[REDACTED]` and preserves all other text.

Focused verification passed for fixture-shaped input, multiple tokens, and text without tokens.

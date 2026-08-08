Implemented `parse_kv` in `work.py`.

It now parses valid `key=value` lines, ignores blank or malformed lines and empty keys, trims surrounding whitespace, and preserves additional `=` characters in values. Focused fixture and edge-case verification passed.

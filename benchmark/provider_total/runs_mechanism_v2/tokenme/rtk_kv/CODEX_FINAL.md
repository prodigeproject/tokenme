Implemented `parse_kv` in `work.py`. It parses valid non-empty `key=value` lines, ignores malformed lines and empty keys, handles embedded `=` characters, and returns a dictionary.

Focused fixture and edge-case verification passed.
Implemented `failed_commands` in `work.py`. It returns command names from correctly formatted lines with nonzero numeric exit statuses and ignores successful or malformed lines.

Focused verification passed against the provided fixture plus nonzero, negative, zero, and malformed cases.
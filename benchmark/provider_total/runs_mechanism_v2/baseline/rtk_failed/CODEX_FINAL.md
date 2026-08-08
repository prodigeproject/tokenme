Implemented `failed_commands` in `work.py`. It now returns command names from correctly formatted lines with nonzero exit codes, preserving input order and ignoring malformed or successful entries.

Focused verification passed against the provided fixture and additional edge cases.
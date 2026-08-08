Implemented `failed_commands` in `work.py`. It returns command names from correctly formatted lines with nonzero integer exit codes, while ignoring successful and malformed lines.

Focused verification passed against the provided fixture and additional zero, negative, and malformed cases.

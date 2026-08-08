Implemented `split_host` in `work.py` using Python’s standard URL parser. It returns the normalized hostname or `None` when no hostname is present.

Focused checks passed for an authenticated URL with a port, a relative path, and a hostless `file:` URL.
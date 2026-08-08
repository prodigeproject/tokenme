Implemented `verify_token(token, secret)` in `auth_token/auth.py` with strict token parsing, HMAC-SHA256 recomputation, and constant-time signature comparison. Invalid, forged, tampered, malformed, and wrong-secret tokens now return `None`.

Focused token checks passed.
Implemented `verify_token` with HMAC-SHA256 validation and constant-time signature comparison. Invalid, forged, wrong-secret, and tampered tokens return `None`.

Focused check: `1 passed`.
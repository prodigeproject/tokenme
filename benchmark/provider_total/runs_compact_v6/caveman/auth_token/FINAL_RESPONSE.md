Implemented `verify_token`: HMAC-SHA256 validation, constant-time signature comparison, malformed input rejection. Forged, tampered, wrong-secret tokens return `None`. Focused checks pass.

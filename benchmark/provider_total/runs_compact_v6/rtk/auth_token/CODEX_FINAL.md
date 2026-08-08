Implemented `verify_token(token, secret)` with HMAC-SHA256 verification and constant-time signature comparison. Malformed, forged, tampered, and wrong-secret tokens now return `None`.

Focused valid and adversarial checks pass.
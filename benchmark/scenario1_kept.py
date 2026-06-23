"""REST API auth endpoints — Flask + PBKDF2 + rate limiting."""
from __future__ import annotations

import hashlib, hmac, json, os, re, time, uuid
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET = os.environ["SECRET_KEY"]
TOKEN_TTL = int(os.getenv("TOKEN_TTL", "3600"))
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
LOCKOUT_S = int(os.getenv("LOCKOUT_MINUTES", "15")) * 60

_users: dict = {}       # email -> user dict   (use DB in prod)
_attempts: dict = {}    # ip -> {count, locked_until}
_tokens: set = set()    # active JTIs          (use Redis in prod)


# ── crypto ──────────────────────────────────────────────────────────────────
def _hash_pw(pw: str) -> str:
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000)
    return (salt + key).hex()

def _verify_pw(stored: str, pw: str) -> bool:
    b = bytes.fromhex(stored); salt, key = b[:32], b[32:]
    return hmac.compare_digest(key,
        hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000))

def _make_token(uid: str, ttl: int = TOKEN_TTL) -> str:
    p = {"uid": uid, "exp": time.time() + ttl, "jti": uuid.uuid4().hex}
    enc = json.dumps(p, sort_keys=True).encode().hex()
    sig = hmac.new(SECRET.encode(), enc.encode(), hashlib.sha256).hexdigest()
    return f"{enc}.{sig}"

def _decode_token(tok: str) -> dict | None:
    try:
        enc, sig = tok.split(".")
        if not hmac.compare_digest(
            hmac.new(SECRET.encode(), enc.encode(), hashlib.sha256).hexdigest(), sig):
            return None
        p = json.loads(bytes.fromhex(enc).decode())
        if time.time() > p["exp"] or p["jti"] not in _tokens:
            return None
        return p
    except Exception:
        return None


# ── validation ───────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def _validate_pw(pw: str) -> str | None:
    """Return error string or None if strong."""
    checks = [
        (len(pw) >= 8,              "min 8 chars"),
        (re.search(r"[A-Z]", pw),   "uppercase required"),
        (re.search(r"[a-z]", pw),   "lowercase required"),
        (re.search(r"\d",    pw),   "digit required"),
        (re.search(r"[^A-Za-z0-9]", pw), "special char required"),
    ]
    for ok, msg in checks:
        if not ok: return msg
    return None


# ── rate limit ───────────────────────────────────────────────────────────────
def _check_rl(ip: str) -> bool:
    now = time.time()
    d = _attempts.get(ip, {})
    if d.get("locked_until", 0) > now:
        return False
    if now - d.get("ts", 0) > LOCKOUT_S:
        _attempts[ip] = {"count": 0, "ts": now}
        return True
    return d.get("count", 0) < MAX_ATTEMPTS

def _fail(ip: str):
    now = time.time()
    d = _attempts.setdefault(ip, {"count": 0, "ts": now})
    d["count"] += 1; d["ts"] = now
    if d["count"] >= MAX_ATTEMPTS:
        d["locked_until"] = now + LOCKOUT_S


# ── auth decorator ───────────────────────────────────────────────────────────
def auth_required(f):
    @wraps(f)
    def inner(*a, **kw):
        hdr = request.headers.get("Authorization", "")
        tok = hdr.removeprefix("Bearer ").strip() or request.cookies.get("auth_token")
        p = _decode_token(tok) if tok else None
        if not p:
            return jsonify(error="auth required"), 401
        request.uid = p["uid"]
        return f(*a, **kw)
    return inner


# ── routes ───────────────────────────────────────────────────────────────────
@app.post("/api/v1/auth/register")
def register():
    d = request.get_json(silent=True) or {}
    email = d.get("email", "").lower().strip()
    pw, name = d.get("password", ""), d.get("name", "").strip()

    if not _EMAIL_RE.match(email):
        return jsonify(error="invalid email"), 400
    err = _validate_pw(pw)
    if err:
        return jsonify(error=err), 400
    if not 2 <= len(name) <= 100:
        return jsonify(error="name must be 2-100 chars"), 400
    if email in _users:
        return jsonify(error="email taken"), 409

    uid = uuid.uuid4().hex
    _users[email] = {
        "id": uid, "email": email, "name": name,
        "pw": _hash_pw(pw), "active": True,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    return jsonify(id=uid, email=email), 201


@app.post("/api/v1/auth/login")
def login():
    ip = request.remote_addr or "0.0.0.0"
    if not _check_rl(ip):
        return jsonify(error="too many attempts, retry later"), 429

    d = request.get_json(silent=True) or {}
    email, pw = d.get("email", "").lower().strip(), d.get("password", "")
    u = _users.get(email)

    if not u or not _verify_pw(u["pw"], pw):
        _fail(ip)
        return jsonify(error="invalid credentials"), 401
    if not u["active"]:
        return jsonify(error="account inactive"), 403

    tok = _make_token(u["id"])
    p   = _decode_token(tok)
    if p: _tokens.add(p["jti"])
    return jsonify(access_token=tok, token_type="Bearer", expires_in=TOKEN_TTL), 200


@app.post("/api/v1/auth/logout")
@auth_required
def logout():
    hdr = request.headers.get("Authorization", "")
    tok = hdr.removeprefix("Bearer ").strip()
    p   = _decode_token(tok)
    if p: _tokens.discard(p["jti"])
    return jsonify(ok=True), 200


@app.get("/api/v1/auth/me")
@auth_required
def me():
    u = next((v for v in _users.values() if v["id"] == request.uid), None)
    if not u:
        return jsonify(error="not found"), 404
    return jsonify(id=u["id"], email=u["email"], name=u["name"]), 200

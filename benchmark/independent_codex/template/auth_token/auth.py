import hashlib
import hmac


def make_token(user_id, secret):
    user_id = str(user_id)
    signature = hmac.new(secret.encode(), user_id.encode(), hashlib.sha256).hexdigest()
    return f"{user_id}.{signature}"


def verify_token(token, secret):
    """Return the user id for a valid token, otherwise None."""
    raise NotImplementedError

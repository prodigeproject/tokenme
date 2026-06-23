"""
SCENARIO 1: REST API endpoint with authentication
STYLE: Verbose/bloated — what a default LLM might generate without token awareness
"""

# Great question! I'll help you build a comprehensive REST API endpoint for user authentication.
# Here's a complete implementation that covers all the cases you need:
# We'll use Flask with JWT authentication, proper error handling, input validation,
# and security best practices. Let me walk you through each part:

from flask import Flask, request, jsonify, make_response
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any, Tuple, Union

# First, let's set up our Flask application instance
# We'll configure it with all the necessary settings for production use
app = Flask(__name__)

# Configuration - In production, these should be loaded from environment variables
# For now, I'll hardcode some defaults for demonstration purposes
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-very-secure-secret-key-here-change-in-production')
TOKEN_EXPIRY_SECONDS = int(os.environ.get('TOKEN_EXPIRY_SECONDS', '3600'))  # 1 hour by default
REFRESH_TOKEN_EXPIRY_SECONDS = int(os.environ.get('REFRESH_TOKEN_EXPIRY_SECONDS', '86400'))  # 24 hours
MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', '15'))

# In-memory storage for demonstration purposes
# In a real application, you would use a proper database like PostgreSQL, MySQL, etc.
# and a proper session store like Redis for the login attempts tracking
users_database = {}  # This is just for demo - use a real DB in production!
login_attempts = {}  # Track failed login attempts - use Redis in production!
active_tokens = {}   # Store active tokens - use Redis in production!
refresh_tokens = {}  # Store refresh tokens - use Redis in production!

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_token(user_id: str, expiry_seconds: int) -> str:
    """
    Generate a simple JWT-like token.
    
    In production, you should use a proper JWT library like PyJWT or jose.
    This is a simplified implementation for demonstration purposes only.
    
    Args:
        user_id: The unique identifier of the user
        expiry_seconds: How long the token should be valid for
        
    Returns:
        str: A token string that can be used for authentication
    """
    # Create the payload with all necessary fields
    payload = {
        'user_id': user_id,
        'issued_at': time.time(),
        'expires_at': time.time() + expiry_seconds,
        'jti': str(uuid.uuid4()),  # JWT ID for uniqueness
        'iss': 'your-app-name',    # Issuer
        'sub': user_id,            # Subject
    }
    
    # Encode the payload as JSON
    payload_json = json.dumps(payload, sort_keys=True)
    payload_encoded = payload_json.encode('utf-8').hex()
    
    # Create a signature using HMAC-SHA256
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_encoded.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Combine payload and signature
    token = f"{payload_encoded}.{signature}"
    return token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a token.
    
    This function checks the token signature and expiry.
    Returns None if the token is invalid or expired.
    
    Args:
        token: The token string to verify
        
    Returns:
        dict: The decoded payload if valid, None otherwise
    """
    # First, let's check if the token has the right format
    if not token or '.' not in token:
        return None
    
    try:
        # Split the token into its components
        parts = token.split('.')
        if len(parts) != 2:
            return None
            
        payload_encoded, provided_signature = parts
        
        # Verify the signature
        expected_signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_encoded.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_signature, provided_signature):
            return None
        
        # Decode the payload
        payload_json = bytes.fromhex(payload_encoded).decode('utf-8')
        payload = json.loads(payload_json)
        
        # Check if the token has expired
        if time.time() > payload.get('expires_at', 0):
            return None
            
        # Check if the token has been revoked (logged out)
        jti = payload.get('jti')
        if jti and jti not in active_tokens:
            return None
            
        return payload
        
    except (ValueError, KeyError, json.JSONDecodeError, Exception) as e:
        # Log the error in a real application
        # logger.warning(f"Token verification failed: {e}")
        return None


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    
    We're using PBKDF2 here for demonstration. In production, consider using
    bcrypt or argon2 which are more resistant to GPU-based attacks.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        str: The hashed password as a hex string
    """
    # Generate a random salt for this password
    salt = os.urandom(32)
    
    # Hash the password with the salt
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # Number of iterations - higher is more secure but slower
    )
    
    # Return salt + key as hex for storage
    return (salt + key).hex()


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """
    Verify a password against its stored hash.
    
    Args:
        stored_hash: The previously stored hash from hash_password()
        provided_password: The plaintext password to check
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        # Decode the stored hash
        stored_bytes = bytes.fromhex(stored_hash)
        salt = stored_bytes[:32]
        stored_key = stored_bytes[32:]
        
        # Hash the provided password with the same salt
        provided_key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            100000
        )
        
        # Use constant-time comparison
        return hmac.compare_digest(stored_key, provided_key)
        
    except (ValueError, Exception):
        return False


def validate_email(email: str) -> bool:
    """
    Validate an email address format.
    
    This uses a simple regex. For production, consider using a library
    like email-validator for more thorough validation.
    
    Args:
        email: The email address to validate
        
    Returns:
        bool: True if the email format is valid, False otherwise
    """
    # A simple but reasonably comprehensive email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Check password strength against our requirements.
    
    Password requirements:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one digit
    - At least one special character
    
    Args:
        password: The password to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, ""


def check_rate_limit(ip_address: str) -> Tuple[bool, int]:
    """
    Check if an IP address has exceeded the login attempt rate limit.
    
    Args:
        ip_address: The IP address to check
        
    Returns:
        tuple: (is_allowed: bool, remaining_attempts: int)
    """
    now = time.time()
    lockout_duration = LOCKOUT_DURATION_MINUTES * 60
    
    if ip_address in login_attempts:
        attempts_data = login_attempts[ip_address]
        
        # Check if in lockout period
        if attempts_data.get('locked_until', 0) > now:
            return False, 0
            
        # Clean up old attempts (older than lockout duration)
        if now - attempts_data.get('last_attempt', 0) > lockout_duration:
            login_attempts[ip_address] = {'count': 0, 'last_attempt': now}
            return True, MAX_LOGIN_ATTEMPTS
            
        count = attempts_data.get('count', 0)
        remaining = MAX_LOGIN_ATTEMPTS - count
        return remaining > 0, max(0, remaining)
    
    return True, MAX_LOGIN_ATTEMPTS


def record_failed_attempt(ip_address: str) -> None:
    """Record a failed login attempt for rate limiting purposes."""
    now = time.time()
    
    if ip_address not in login_attempts:
        login_attempts[ip_address] = {'count': 0, 'last_attempt': now}
    
    login_attempts[ip_address]['count'] += 1
    login_attempts[ip_address]['last_attempt'] = now
    
    # Lock out if exceeded max attempts
    if login_attempts[ip_address]['count'] >= MAX_LOGIN_ATTEMPTS:
        login_attempts[ip_address]['locked_until'] = now + (LOCKOUT_DURATION_MINUTES * 60)


def require_auth(f):
    """
    Decorator to require authentication on an endpoint.
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to get token from Authorization header first
        auth_header = request.headers.get('Authorization')
        token = None
        
        if auth_header:
            # Check for Bearer token format
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid authorization header format. Use: Bearer <token>',
                    'code': 'INVALID_AUTH_FORMAT'
                }), 401
        else:
            # Also check for token in cookie as fallback
            token = request.cookies.get('auth_token')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authentication required. Please provide a valid token.',
                'code': 'AUTH_REQUIRED'
            }), 401
            
        payload = verify_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token. Please log in again.',
                'code': 'INVALID_TOKEN'
            }), 401
            
        # Add user info to request context
        request.user_id = payload['user_id']
        request.token_payload = payload
        
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# ROUTES
# =============================================================================

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """
    Register a new user account.
    
    Expected request body (JSON):
    {
        "email": "user@example.com",
        "password": "SecureP@ss1",
        "name": "John Doe"
    }
    
    Returns:
    - 201: User created successfully
    - 400: Validation error
    - 409: Email already registered
    """
    # Make sure we received JSON data
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type must be application/json',
            'code': 'INVALID_CONTENT_TYPE'
        }), 400
    
    data = request.get_json()
    
    # Validate required fields are present
    required_fields = ['email', 'password', 'name']
    missing_fields = [f for f in required_fields if f not in data]
    if missing_fields:
        return jsonify({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing_fields)}',
            'code': 'MISSING_FIELDS',
            'missing': missing_fields
        }), 400
    
    email = data['email'].lower().strip()
    password = data['password']
    name = data['name'].strip()
    
    # Validate email format
    if not validate_email(email):
        return jsonify({
            'success': False,
            'error': 'Invalid email address format',
            'code': 'INVALID_EMAIL'
        }), 400
    
    # Validate password strength
    is_strong, strength_error = validate_password_strength(password)
    if not is_strong:
        return jsonify({
            'success': False,
            'error': strength_error,
            'code': 'WEAK_PASSWORD'
        }), 400
    
    # Validate name
    if not name or len(name) < 2:
        return jsonify({
            'success': False,
            'error': 'Name must be at least 2 characters long',
            'code': 'INVALID_NAME'
        }), 400
    
    if len(name) > 100:
        return jsonify({
            'success': False,
            'error': 'Name must not exceed 100 characters',
            'code': 'NAME_TOO_LONG'
        }), 400
    
    # Check if email already exists
    if email in users_database:
        return jsonify({
            'success': False,
            'error': 'An account with this email address already exists',
            'code': 'EMAIL_EXISTS'
        }), 409
    
    # Create the user
    user_id = str(uuid.uuid4())
    users_database[email] = {
        'id': user_id,
        'email': email,
        'name': name,
        'password_hash': hash_password(password),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'is_active': True,
        'is_verified': False,  # Email verification would be sent in production
        'last_login': None,
        'login_count': 0
    }
    
    return jsonify({
        'success': True,
        'message': 'Account created successfully. Please verify your email to activate your account.',
        'user': {
            'id': user_id,
            'email': email,
            'name': name,
            'created_at': users_database[email]['created_at']
        }
    }), 201


@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """
    Authenticate a user and return access + refresh tokens.
    
    Expected request body (JSON):
    {
        "email": "user@example.com",
        "password": "SecureP@ss1"
    }
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type must be application/json',
            'code': 'INVALID_CONTENT_TYPE'
        }), 400
    
    # Check rate limiting
    client_ip = request.remote_addr or '0.0.0.0'
    allowed, remaining = check_rate_limit(client_ip)
    
    if not allowed:
        return jsonify({
            'success': False,
            'error': f'Too many failed login attempts. Please try again in {LOCKOUT_DURATION_MINUTES} minutes.',
            'code': 'RATE_LIMITED',
            'retry_after': LOCKOUT_DURATION_MINUTES * 60
        }), 429
    
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'error': 'Email and password are required',
            'code': 'MISSING_CREDENTIALS'
        }), 400
    
    # Look up the user
    user = users_database.get(email)
    
    # Use constant-time comparison to prevent user enumeration
    if not user or not verify_password(user['password_hash'], password):
        record_failed_attempt(client_ip)
        return jsonify({
            'success': False,
            'error': 'Invalid email or password',  # Don't reveal which one
            'code': 'INVALID_CREDENTIALS',
            'remaining_attempts': max(0, remaining - 1)
        }), 401
    
    if not user['is_active']:
        return jsonify({
            'success': False,
            'error': 'Account is deactivated. Please contact support.',
            'code': 'ACCOUNT_DEACTIVATED'
        }), 403
    
    # Generate tokens
    access_token = generate_token(user['id'], TOKEN_EXPIRY_SECONDS)
    refresh_token_value = generate_token(user['id'], REFRESH_TOKEN_EXPIRY_SECONDS)
    
    # Store tokens
    access_payload = verify_token(access_token)
    if access_payload:
        active_tokens[access_payload['jti']] = True
    
    # Update user login info
    users_database[email]['last_login'] = datetime.utcnow().isoformat()
    users_database[email]['login_count'] = user.get('login_count', 0) + 1
    
    # Reset failed attempts on successful login
    if client_ip in login_attempts:
        login_attempts[client_ip] = {'count': 0, 'last_attempt': time.time()}
    
    response_data = {
        'success': True,
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token_value,
        'token_type': 'Bearer',
        'expires_in': TOKEN_EXPIRY_SECONDS,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'last_login': users_database[email]['last_login']
        }
    }
    
    return jsonify(response_data), 200


@app.route('/api/v1/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Log out the current user by revoking their token."""
    # Revoke the current token
    jti = request.token_payload.get('jti')
    if jti and jti in active_tokens:
        del active_tokens[jti]
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@app.route('/api/v1/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get the current authenticated user's profile."""
    user_id = request.user_id
    
    # Find user by ID
    user = None
    for u in users_database.values():
        if u['id'] == user_id:
            user = u
            break
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'User not found',
            'code': 'USER_NOT_FOUND'
        }), 404
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at'],
            'last_login': user.get('last_login'),
            'is_verified': user.get('is_verified', False)
        }
    }), 200


if __name__ == '__main__':
    # Don't use debug=True in production!
    app.run(debug=True, host='0.0.0.0', port=5000)

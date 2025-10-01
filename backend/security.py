"""
Security middleware and utilities for the GolfMatch application.
Implements various security measures to protect the application and its users.
"""

from functools import wraps
from flask import request, current_app
from hmac import compare_digest
from flask_jwt_extended import verify_jwt_in_request, get_jwt
import re
import bleach
from marshmallow import ValidationError

def require_api_key(f):
    """Decorator to require API key for external service endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or not compare_digest(api_key.encode('utf-8'), current_app.config['API_KEY'].encode('utf-8')):
            return {'message': 'Invalid or missing API key'}, 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator to require admin role for sensitive endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if not claims.get('is_admin', False):
            return {'message': 'Admin privilege required'}, 403
        return f(*args, **kwargs)
    return decorated

class SecurityHeaders:
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        def security_headers(status, headers, exc_info=None):
            headers.extend([
                ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'),
                ('Content-Security-Policy', "default-src 'self'; "
                                         "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                                         "style-src 'self' 'unsafe-inline';"),
                ('X-Content-Type-Options', 'nosniff'),
                ('X-Frame-Options', 'SAMEORIGIN'),
                ('X-XSS-Protection', '1; mode=block'),
                ('Referrer-Policy', 'strict-origin-when-cross-origin')
            ])
            return start_response(status, headers, exc_info)
        return self.app(environ, security_headers)

class InputSanitizer:
    """Utility class for sanitizing user input."""
    
    @staticmethod
    def sanitize_text(text):
        """Sanitize text input to prevent XSS attacks."""
        if not isinstance(text, str):
            return text
        return bleach.clean(text, strip=True)
    
    @staticmethod
    def validate_email(email):
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError('Invalid email format')
        return email
    
    @staticmethod
    def validate_password(password):
        """
        Validate password strength.
        Requires:
        - At least 8 characters
        - Contains both uppercase and lowercase letters
        - Contains at least one number
        - Contains at least one special character
        """
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character')
        return password

def setup_security(app):
    """Configure security settings for the Flask app."""
    
    # Set up security headers middleware
    app.wsgi_app = SecurityHeaders(app.wsgi_app)
    
    # Configure session security
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
    )
    
    # Register error handlers
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return {'message': str(error)}, 400
    
    @app.before_request
    def validate_content_type():
        """Ensure proper content type for POST/PUT requests."""
        if request.method in ['POST', 'PUT']:
            if not request.is_json:
                return {'message': 'Content-Type must be application/json'}, 415
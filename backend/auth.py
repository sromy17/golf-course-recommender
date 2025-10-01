"""
Authentication module for the GolfMatch application.
Handles user registration, login, and token management.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from hmac import compare_digest
from marshmallow import Schema, fields, validate, ValidationError

from models import db, User
from security import InputSanitizer

# Create Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Schema for input validation
class UserSchema(Schema):
    """Schema for validating user registration and update data."""
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    handicap = fields.Float(allow_none=True)
    playing_style = fields.Str(validate=validate.OneOf(['Competitive', 'Scenic', 'Social', 'Challenging']))

# Initialize schemas
user_schema = UserSchema()

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    Validates input, checks for existing users, and creates new user account.
    """
    try:
        # Validate input data
        data = user_schema.load(request.json)
        
        # Sanitize inputs
        username = InputSanitizer.sanitize_text(data['username'])
        email = InputSanitizer.validate_email(data['email'])
        password = InputSanitizer.validate_password(data['password'])
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return {'message': 'Username already exists'}, 409
        if User.query.filter_by(email=email).first():
            return {'message': 'Email already registered'}, 409
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            handicap=data.get('handicap'),
            playing_style=data.get('playing_style'),
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(new_user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(identity=new_user.id)
        refresh_token = create_refresh_token(identity=new_user.id)
        
        return {
            'message': 'User created successfully',
            'access_token': access_token,
            'refresh_token': refresh_token
        }, 201
        
    except ValidationError as e:
        return {'message': str(e)}, 400
    except Exception as e:
        db.session.rollback()
        return {'message': 'Error creating user'}, 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and issue JWT tokens.
    Validates credentials and returns access and refresh tokens.
    """
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        
        if not username or not password:
            return {'message': 'Missing username or password'}, 400
        
        # Find user
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            return {'message': 'Invalid username or password'}, 401
        
        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }, 200
        
    except Exception as e:
        return {'message': 'Error during login'}, 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    Requires valid refresh token.
    """
    try:
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        return {'access_token': new_access_token}, 200
    except Exception as e:
        return {'message': 'Error refreshing token'}, 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user by revoking their JWT tokens.
    Requires valid access token.
    """
    try:
        jti = get_jwt()['jti']
        # Add token to blocklist (implement token blocklist in production)
        return {'message': 'Successfully logged out'}, 200
    except Exception as e:
        return {'message': 'Error during logout'}, 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get user profile information.
    Requires valid access token.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return {'message': 'User not found'}, 404
        
        return {
            'username': user.username,
            'email': user.email,
            'handicap': user.handicap,
            'playing_style': user.playing_style,
            'created_at': user.created_at.isoformat()
        }, 200
        
    except Exception as e:
        return {'message': 'Error retrieving profile'}, 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile information.
    Requires valid access token.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return {'message': 'User not found'}, 404
        
        # Validate and sanitize input
        data = user_schema.load(request.json, partial=True)
        
        # Update fields if provided
        if 'username' in data:
            username = InputSanitizer.sanitize_text(data['username'])
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != current_user_id:
                return {'message': 'Username already exists'}, 409
            user.username = username
            
        if 'email' in data:
            email = InputSanitizer.validate_email(data['email'])
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user_id:
                return {'message': 'Email already registered'}, 409
            user.email = email
            
        if 'password' in data:
            password = InputSanitizer.validate_password(data['password'])
            user.password_hash = generate_password_hash(password)
            
        if 'handicap' in data:
            user.handicap = data['handicap']
            
        if 'playing_style' in data:
            user.playing_style = data['playing_style']
        
        db.session.commit()
        return {'message': 'Profile updated successfully'}, 200
        
    except ValidationError as e:
        return {'message': str(e)}, 400
    except Exception as e:
        db.session.rollback()
        return {'message': 'Error updating profile'}, 500
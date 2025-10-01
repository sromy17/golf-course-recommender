"""
Main Flask application for the GolfMatch API.
Implements all routes and integrates security middleware.
"""

import os
from flask import Flask, request, jsonify, redirect
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import db, User, Course, Review
from auth import auth_bp
from security import setup_security
from config import config
from ai_engine import ai_engine

def create_app(config_name='default'):
    """
    Factory function to create and configure the Flask application.
    
    Args:
        config_name: Configuration to use (default, development, testing, production)
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    
    # Setup rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100 per minute"]
    )
    
    # Set up security features
    setup_security(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    @app.before_request
    def before_request():
        """Pre-request processing."""
        # Force HTTPS in production
        if not request.is_secure and app.env == 'production':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url), 301

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return jsonify({'message': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return jsonify({'message': 'Internal server error'}), 500

    # Course routes
    @app.route('/api/courses', methods=['GET'])
    @limiter.limit("30 per minute")
    def get_courses():
        """Get all courses with optional filtering."""
        try:
            # Get query parameters
            location = request.args.get('location')
            min_rating = request.args.get('min_rating', type=float)
            max_price = request.args.get('max_price')
            vibe = request.args.get('vibe')
            
            # Build query
            query = Course.query
            
            if location:
                query = query.filter(Course.location.ilike(f'%{location}%'))
            if min_rating:
                query = query.filter(Course.difficulty_rating >= min_rating)
            if max_price:
                query = query.filter(Course.price_range <= max_price)
            if vibe:
                query = query.filter(Course.vibe_tags.contains([vibe]))
                
            courses = query.all()
            return jsonify([{
                'id': c.id,
                'name': c.name,
                'location': c.location,
                'difficulty_rating': c.difficulty_rating,
                'price_range': c.price_range,
                'vibe_tags': c.vibe_tags,
                'description': c.description
            } for c in courses]), 200
            
        except Exception as e:
            app.logger.error(f"Error fetching courses: {str(e)}")
            return jsonify({'message': 'Error fetching courses'}), 500

    @app.route('/api/courses/<int:course_id>', methods=['GET'])
    @limiter.limit("30 per minute")
    def get_course(course_id):
        """Get detailed information about a specific course."""
        try:
            course = Course.query.get_or_404(course_id)
            
            # Get course reviews
            reviews = Review.query.filter_by(course_id=course_id).all()
            
            # Get current weather
            weather = ai_engine.get_weather_forecast(course.location)
            
            return jsonify({
                'id': course.id,
                'name': course.name,
                'location': course.location,
                'difficulty_rating': course.difficulty_rating,
                'price_range': course.price_range,
                'vibe_tags': course.vibe_tags,
                'description': course.description,
                'features': course.features,
                'current_conditions': course.current_conditions,
                'weather_forecast': weather,
                'reviews': [{
                    'rating': r.rating,
                    'comment': r.comment,
                    'created_at': r.created_at.isoformat(),
                    'sentiment_score': r.sentiment_score
                } for r in reviews]
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error fetching course: {str(e)}")
            return jsonify({'message': 'Error fetching course details'}), 500

    @app.route('/api/recommendations', methods=['GET'])
    @jwt_required()
    @limiter.limit("10 per minute")
    def get_recommendations():
        """Get personalized course recommendations for the current user."""
        try:
            current_user_id = get_jwt_identity()
            user = User.query.get_or_404(current_user_id)
            
            # Get query parameters for group recommendations
            group_size = request.args.get('group_size', 1, type=int)
            group_handicaps = request.args.getlist('handicaps', type=float)
            
            # Get recommendations from AI engine
            recommendations = ai_engine.get_personalized_recommendations(
                user,
                limit=5,
                group_size=group_size,
                group_handicaps=group_handicaps
            )
            
            return jsonify([{
                'course': {
                    'id': r['course'].id,
                    'name': r['course'].name,
                    'location': r['course'].location,
                    'difficulty_rating': r['course'].difficulty_rating,
                    'price_range': r['course'].price_range,
                    'vibe_tags': r['course'].vibe_tags
                },
                'match_score': r['score'],
                'reason': r['reason'],
                'adjusted_difficulty': r['adjusted_difficulty'],
                'current_weather': r['weather'].get('current', {})
            } for r in recommendations]), 200
            
        except Exception as e:
            app.logger.error(f"Error generating recommendations: {str(e)}")
            return jsonify({'message': 'Error generating recommendations'}), 500

    @app.route('/api/reviews', methods=['POST'])
    @jwt_required()
    @limiter.limit("10 per minute")
    def create_review():
        """Submit a new course review."""
        try:
            current_user_id = get_jwt_identity()
            
            # Validate input
            data = request.get_json()
            course_id = data.get('course_id')
            rating = data.get('rating')
            comment = data.get('comment')
            
            if not course_id or not rating or not comment:
                return jsonify({'message': 'Missing required fields'}), 400
                
            if not 1 <= rating <= 5:
                return jsonify({'message': 'Rating must be between 1 and 5'}), 400
            
            # Check if course exists
            course = Course.query.get_or_404(course_id)
            
            # Analyze sentiment using AI
            sentiment_data = ai_engine.analyze_review_sentiment(comment)
            
            # Create review
            review = Review(
                user_id=current_user_id,
                course_id=course_id,
                rating=rating,
                comment=comment,
                sentiment_score=sentiment_data['sentiment_score'],
                extracted_features=sentiment_data['features']
            )
            
            db.session.add(review)
            db.session.commit()
            
            return jsonify({
                'message': 'Review submitted successfully',
                'review_id': review.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating review: {str(e)}")
            return jsonify({'message': 'Error submitting review'}), 500

    return app

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.getenv('FLASK_CONFIG', 'default')
    
    # Create app instance
    app = create_app(config_name)
    
    # Run the app
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000))
    )
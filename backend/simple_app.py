"""
Main Flask application for the GolfMatch API.
"""

import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()

# Models
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    difficulty_rating = db.Column(db.Float)
    price_range = db.Column(db.String(50))
    description = db.Column(db.Text)

def create_app():
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///golf_courses.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with app
    db.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Add sample data if database is empty
        if Course.query.count() == 0:
            sample_courses = [
                Course(
                    name="Pine Valley Golf Club",
                    location="Pine Valley, New Jersey",
                    difficulty_rating=4.8,
                    price_range="$$$",
                    description="One of the most challenging and beautiful golf courses in the world."
                ),
                Course(
                    name="Augusta National Golf Club",
                    location="Augusta, Georgia",
                    difficulty_rating=4.9,
                    price_range="$$$$",
                    description="Home of the Masters Tournament, featuring pristine fairways and challenging greens."
                ),
                Course(
                    name="St Andrews Links (Old Course)",
                    location="St Andrews, Scotland",
                    difficulty_rating=4.5,
                    price_range="$$$",
                    description="The oldest golf course in the world and the home of golf."
                ),
                Course(
                    name="Pebble Beach Golf Links",
                    location="Pebble Beach, California",
                    difficulty_rating=4.7,
                    price_range="$$$$",
                    description="Stunning coastal views with challenging oceanside holes."
                ),
                Course(
                    name="Bethpage Black Course",
                    location="Farmingdale, New York",
                    difficulty_rating=4.6,
                    price_range="$$",
                    description="A demanding public course that has hosted multiple major championships."
                )
            ]
            db.session.add_all(sample_courses)
            db.session.commit()

    @app.route('/')
    def home():
        return jsonify({
            "message": "Welcome to GolfMatch API!",
            "endpoints": {
                "GET /api/courses": "List all golf courses",
                "GET /api/courses/<id>": "Get details of a specific course"
            }
        })

    @app.route('/api/courses')
    def get_courses():
        try:
            courses = Course.query.all()
            return jsonify([{
                'id': course.id,
                'name': course.name,
                'location': course.location,
                'difficulty_rating': course.difficulty_rating,
                'price_range': course.price_range
            } for course in courses])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/courses/<int:course_id>')
    def get_course(course_id):
        try:
            course = Course.query.get_or_404(course_id)
            return jsonify({
                'id': course.id,
                'name': course.name,
                'location': course.location,
                'difficulty_rating': course.difficulty_rating,
                'price_range': course.price_range,
                'description': course.description
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
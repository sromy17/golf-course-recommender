"""
Database models for the GolfMatch application using SQLAlchemy ORM.
These models define the structure of our database tables and their relationships.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """
    User model for storing player information and authentication details.
    Includes golf-specific attributes like handicap and playing style preferences.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    handicap = Column(Float)
    playing_style = Column(String(50))  # Competitive, Scenic, Social, Challenging
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    reviews = relationship('Review', back_populates='user')
    recommendations = relationship('Recommendation', back_populates='user')

class Course(db.Model):
    """
    Golf course model storing course details and characteristics.
    Includes attributes for AI-powered matching and recommendations.
    """
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    difficulty_rating = Column(Float)
    description = Column(Text)
    price_range = Column(String(50))  # e.g., "$", "$$", "$$$"
    vibe_tags = Column(JSON)  # Array of tags like ["scenic", "challenging", "social"]
    features = Column(JSON)  # Additional course features/amenities
    
    # Weather and conditions
    last_condition_update = Column(DateTime)
    current_conditions = Column(JSON)
    
    # Relationships
    reviews = relationship('Review', back_populates='course')
    recommendations = relationship('Recommendation', back_populates='course')

class Review(db.Model):
    """
    Course review model capturing user feedback and ratings.
    Used for sentiment analysis and collaborative filtering.
    """
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional sentiment data (populated by AI)
    sentiment_score = Column(Float)
    extracted_features = Column(JSON)
    
    # Relationships
    user = relationship('User', back_populates='reviews')
    course = relationship('Course', back_populates='reviews')

class Recommendation(db.Model):
    """
    Recommendation model storing AI-generated course suggestions.
    Includes reasoning and scoring for transparency.
    """
    __tablename__ = 'recommendations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    score = Column(Float, nullable=False)  # AI-calculated match score
    reason = Column(Text)  # AI-generated explanation
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional recommendation metadata
    factors = Column(JSON)  # Factors that influenced this recommendation
    weather_conditions = Column(JSON)  # Weather data used in recommendation
    
    # Relationships
    user = relationship('User', back_populates='recommendations')
    course = relationship('Course', back_populates='recommendations')
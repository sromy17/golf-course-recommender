"""
AI recommendation engine for the GolfMatch application.
Handles course recommendations, sentiment analysis, and weather integration.
"""

import openai
from flask import current_app
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from models import db, User, Course, Review, Recommendation

class AIEngine:
    """
    Core AI engine for generating personalized golf course recommendations.
    Integrates OpenAI GPT-4 for natural language processing and recommendation generation.
    """
    
    def __init__(self, openai_api_key: str = None):
        """Initialize the AI engine with API keys and configuration."""
        self.openai_api_key = openai_api_key or current_app.config['OPENAI_API_KEY']
        self.weather_api_key = current_app.config['WEATHER_API_KEY']
        self.weather_api_base_url = current_app.config['WEATHER_API_BASE_URL']
        openai.api_key = self.openai_api_key

    def analyze_review_sentiment(self, review_text: str) -> Dict[str, Any]:
        """
        Analyze sentiment and extract features from a course review using GPT-4.
        
        Args:
            review_text: The text of the review to analyze
            
        Returns:
            Dictionary containing sentiment score and extracted features
        """
        try:
            prompt = f"""
            Analyze this golf course review and provide:
            1. A sentiment score (-1.0 to 1.0)
            2. Key features mentioned (condition, difficulty, service, etc.)
            3. Vibe tags (scenic, challenging, social, competitive)

            Review: {review_text}
            
            Format response as JSON.
            """
            
            response = openai.ChatCompletion.create(
                model=current_app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": "You are a golf course review analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            # Parse the JSON response
            analysis = json.loads(response.choices[0].message['content'])
            return {
                'sentiment_score': float(analysis['sentiment_score']),
                'features': analysis['features'],
                'vibe_tags': analysis['vibe_tags']
            }
            
        except Exception as e:
            current_app.logger.error(f"Error analyzing review sentiment: {str(e)}")
            return {
                'sentiment_score': 0.0,
                'features': [],
                'vibe_tags': []
            }

    def get_weather_forecast(self, location: str) -> Dict[str, Any]:
        """
        Get weather forecast for a course location.
        
        Args:
            location: Course location (city, state)
            
        Returns:
            Dictionary containing weather forecast data
        """
        try:
            url = f"{self.weather_api_base_url}/forecast.json"
            params = {
                'key': self.weather_api_key,
                'q': location,
                'days': 7
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"Error fetching weather data: {str(e)}")
            return {}

    def calculate_course_difficulty(self, course: Course, user: User, weather: Dict[str, Any]) -> float:
        """
        Calculate dynamic difficulty rating based on course stats, user handicap, and weather.
        
        Args:
            course: Course object
            user: User object
            weather: Weather forecast data
            
        Returns:
            Adjusted difficulty score (1-10)
        """
        base_difficulty = course.difficulty_rating or 5.0
        
        # Adjust for user handicap
        handicap_factor = 1.0
        if user.handicap is not None:
            if user.handicap > 20:  # High handicap = course feels harder
                handicap_factor = 1.2
            elif user.handicap < 10:  # Low handicap = course feels easier
                handicap_factor = 0.8
        
        # Adjust for weather conditions
        weather_factor = 1.0
        if weather:
            current = weather.get('current', {})
            wind_mph = current.get('wind_mph', 0)
            precip_mm = current.get('precip_mm', 0)
            
            if wind_mph > 15:  # Strong winds
                weather_factor *= 1.2
            if precip_mm > 0:  # Rain
                weather_factor *= 1.1
        
        final_difficulty = base_difficulty * handicap_factor * weather_factor
        return min(max(final_difficulty, 1.0), 10.0)  # Clamp between 1-10

    def get_personalized_recommendations(
        self,
        user: User,
        limit: int = 5,
        group_size: int = 1,
        group_handicaps: List[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized course recommendations for a user or group.
        
        Args:
            user: User to generate recommendations for
            limit: Maximum number of recommendations to return
            group_size: Number of players (for group recommendations)
            group_handicaps: List of handicaps for all players in group
            
        Returns:
            List of recommendation dictionaries with courses and reasoning
        """
        try:
            # Get user's review history
            user_reviews = Review.query.filter_by(user_id=user.id).all()
            reviewed_courses = {r.course_id: r.rating for r in user_reviews}
            
            # Get candidate courses (excluding already reviewed ones with low ratings)
            excluded_courses = [cid for cid, rating in reviewed_courses.items() if rating < 3]
            candidate_courses = Course.query.filter(
                Course.id.notin_(excluded_courses)
            ).all()
            
            recommendations = []
            for course in candidate_courses:
                # Get current weather and conditions
                weather = self.get_weather_forecast(course.location)
                
                # Calculate base match score
                match_score = self._calculate_match_score(user, course)
                
                # Adjust for group if applicable
                if group_size > 1 and group_handicaps:
                    group_score = self._calculate_group_score(
                        course,
                        group_handicaps,
                        weather
                    )
                    match_score = (match_score + group_score) / 2
                
                # Generate explanation using GPT-4
                explanation = self._generate_recommendation_explanation(
                    user,
                    course,
                    match_score,
                    weather,
                    group_size
                )
                
                recommendations.append({
                    'course': course,
                    'score': match_score,
                    'reason': explanation,
                    'weather': weather,
                    'adjusted_difficulty': self.calculate_course_difficulty(
                        course, user, weather
                    )
                })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            current_app.logger.error(f"Error generating recommendations: {str(e)}")
            return []

    def _calculate_match_score(self, user: User, course: Course) -> float:
        """
        Calculate how well a course matches a user's preferences.
        
        Args:
            user: User object
            course: Course object
            
        Returns:
            Match score between 0-1
        """
        score = 0.0
        factors = []
        
        # Style match
        if user.playing_style and course.vibe_tags:
            if user.playing_style.lower() in [tag.lower() for tag in course.vibe_tags]:
                score += 0.3
                factors.append('style_match')
        
        # Difficulty match (based on handicap)
        if user.handicap is not None:
            diff = abs(course.difficulty_rating - (user.handicap / 5))
            difficulty_score = max(0, 1 - (diff / 10))
            score += 0.3 * difficulty_score
            factors.append('difficulty_match')
        
        # Social proof (from reviews)
        reviews = Review.query.filter_by(course_id=course.id).all()
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            score += 0.2 * (avg_rating / 5)
            factors.append('social_proof')
        
        # Recent conditions
        if course.current_conditions and course.last_condition_update:
            age = datetime.utcnow() - course.last_condition_update
            if age < timedelta(days=2):  # Recent conditions get bonus
                conditions_score = 0.2 * (course.current_conditions.get('quality', 0) / 10)
                score += conditions_score
                factors.append('recent_conditions')
        
        return score

    def _calculate_group_score(
        self,
        course: Course,
        group_handicaps: List[float],
        weather: Dict[str, Any]
    ) -> float:
        """
        Calculate how suitable a course is for a group of players.
        
        Args:
            course: Course object
            group_handicaps: List of handicaps for all players
            weather: Weather forecast data
            
        Returns:
            Group compatibility score between 0-1
        """
        if not group_handicaps:
            return 0.0
        
        # Calculate spread of handicaps
        min_handicap = min(group_handicaps)
        max_handicap = max(group_handicaps)
        handicap_range = max_handicap - min_handicap
        
        # Courses that are too challenging for high handicappers
        # or too easy for low handicappers get penalized
        if course.difficulty_rating:
            if course.difficulty_rating > (max_handicap / 4):  # Too hard for highest handicap
                return 0.3
            if course.difficulty_rating < (min_handicap / 8):  # Too easy for lowest handicap
                return 0.5
        
        # Score based on how well course accommodates the spread
        base_score = 1.0 - (handicap_range / 36)  # 36 is max reasonable handicap spread
        
        # Weather penalty for large groups
        if len(group_handicaps) > 2 and weather:
            current = weather.get('current', {})
            if current.get('precip_mm', 0) > 0:  # Rain is worse for large groups
                base_score *= 0.8
        
        return base_score

    def _generate_recommendation_explanation(
        self,
        user: User,
        course: Course,
        match_score: float,
        weather: Dict[str, Any],
        group_size: int
    ) -> str:
        """
        Generate natural language explanation for why a course was recommended.
        
        Args:
            user: User object
            course: Course object
            match_score: Calculated match score
            weather: Weather forecast data
            group_size: Number of players
            
        Returns:
            Natural language explanation string
        """
        try:
            prompt = f"""
            Generate a brief, natural explanation for why this golf course was recommended.
            
            Course details:
            - Name: {course.name}
            - Difficulty: {course.difficulty_rating}/10
            - Vibe tags: {', '.join(course.vibe_tags)}
            
            Player details:
            - Handicap: {user.handicap}
            - Preferred style: {user.playing_style}
            - Group size: {group_size}
            
            Match score: {match_score:.2f}
            Weather: {weather.get('current', {}).get('condition', {}).get('text', 'Unknown')}
            
            Keep it conversational but concise (2-3 sentences).
            """
            
            response = openai.ChatCompletion.create(
                model=current_app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": "You are a knowledgeable golf course recommender."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message['content'].strip()
            
        except Exception as e:
            current_app.logger.error(f"Error generating explanation: {str(e)}")
            return "This course matches your preferences based on our analysis."

# Create singleton instance
ai_engine = AIEngine()
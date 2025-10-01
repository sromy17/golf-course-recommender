import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCourse, setSelectedCourse] = useState(null)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await axios.get('http://localhost:5001/api/courses')
        setCourses(response.data)
        setLoading(false)
      } catch (err) {
        setError('Failed to fetch courses')
        setLoading(false)
      }
    }

    fetchCourses()
  }, [])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div className="App">
      <header>
        <h1>GolfMatch</h1>
        <p>Find your perfect golf course</p>
      </header>
      
      <main>
        <section className="courses">
          <h2>Available Golf Courses</h2>
          <div className="course-grid">
            {courses.map(course => (
              <div 
                key={course.id} 
                className="course-card"
                onClick={() => {
                  setSelectedCourse(course);
                  setShowModal(true);
                }}
              >
                <h3>{course.name}</h3>
                <p className="location">{course.location}</p>
                <div className="details">
                  <span className="rating">Difficulty: {course.difficulty_rating}/5</span>
                  <span className="price">{course.price_range}</span>
                </div>
                <p className="description">{course.description}</p>
                <button className="view-more">View Details</button>
              </div>
            ))}
          </div>
        </section>
      </main>

      {showModal && selectedCourse && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="close-button" onClick={() => setShowModal(false)}>×</button>
            <h2>{selectedCourse.name}</h2>
            <p className="location">{selectedCourse.location}</p>
            <div className="modal-details">
              <div className="detail-item">
                <h4>Difficulty Rating</h4>
                <div className="rating-display">
                  <span className="rating">{selectedCourse.difficulty_rating}/5</span>
                  <div className="rating-bar" style={{
                    '--rating-width': `${(selectedCourse.difficulty_rating / 5) * 100}%`
                  }}></div>
                </div>
              </div>
              <div className="detail-item">
                <h4>Price Range</h4>
                <span className="price">{selectedCourse.price_range}</span>
              </div>
            </div>
            <div className="description-section">
              <h4>About this Course</h4>
              <p>{selectedCourse.description}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

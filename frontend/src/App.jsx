import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
              <div key={course.id} className="course-card">
                <h3>{course.name}</h3>
                <p className="location">{course.location}</p>
                <div className="details">
                  <span className="rating">Difficulty: {course.difficulty_rating}/5</span>
                  <span className="price">{course.price_range}</span>
                </div>
                <p className="description">{course.description}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App

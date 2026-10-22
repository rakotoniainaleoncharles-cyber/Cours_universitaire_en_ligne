import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, ClipboardCheck, FileText, GraduationCap } from 'lucide-react'
import api from '../../services/api'
import { useAutoRefresh } from '../../utils/dataSync'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Impossible de charger le tableau de bord.'
}

export default function StudentDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [error, setError] = useState('')

  const loadDashboard = useCallback(async () => {
    try {
      const { data } = await api.get('/student/dashboard/')
      setDashboard(data)
      setError('')
    } catch (loadError) {
      setError(messageFrom(loadError))
    }
  }, [])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])
  useAutoRefresh(loadDashboard)

  if (error) return <div className="error-message" role="alert">{error}</div>
  if (!dashboard) return <p className="teacher-empty">Chargement du tableau de bord...</p>

  const stats = [
    { label: 'Matières', value: dashboard.subject_count, icon: GraduationCap, category: 'subjects' },
    { label: 'Cours', value: dashboard.course_count, icon: BookOpen, category: 'courses' },
    { label: 'Leçons terminées', value: `${dashboard.completed_lesson_count} / ${dashboard.lesson_count}`, icon: ClipboardCheck, category: 'lessons' },
    { label: 'Documents pédagogiques', value: dashboard.material_count, icon: FileText, category: 'materials' },
  ]

  return (
    <section className="teacher-dashboard">
      <div className="dashboard-grid student-stats">
        {stats.map(({ label, value, icon: Icon, category }) => (
          <article className={`student-stat-card ${category}`} key={label}>
            <span className="student-stat-icon" aria-hidden="true"><Icon size={21} /></span>
            <div>
              <span className="student-stat-label">{label}</span>
              <strong>{value}</strong>
            </div>
          </article>
        ))}
      </div>

      {dashboard.pending_assignment_count > 0 && (
        <div className="success-message" role="status">
          Vous avez {dashboard.pending_assignment_count} devoir(s) à remettre. <Link to="/student/assignments">Voir mes devoirs</Link>
        </div>
      )}

      <div className="teacher-content-columns">
        <section className="teacher-form-card">
          <div className="teacher-panel-heading"><h3>Derniers cours publiés</h3></div>
          {dashboard.recent_courses.length ? (
            <ul className="teacher-item-list">
              {dashboard.recent_courses.map((course) => (
                <li key={course.id}>
                  <div><strong>{course.title}</strong><p>{course.subject_name} · {course.faculty_name} · {course.level_name}</p></div>
                </li>
              ))}
            </ul>
          ) : <p className="teacher-no-items">Aucun cours publié pour vos inscriptions.</p>}
          <Link className="student-inline-link" to="/student/courses">Consulter mes cours</Link>
        </section>
        <section className="teacher-form-card">
          <div className="teacher-panel-heading"><h3>Dernières leçons publiées</h3></div>
          {dashboard.recent_lessons.length ? (
            <ul className="teacher-item-list">
              {dashboard.recent_lessons.map((lesson) => (
                <li key={lesson.id}><div><strong>{lesson.title}</strong><p>{lesson.description || 'Leçon publiée'}</p></div></li>
              ))}
            </ul>
          ) : <p className="teacher-no-items">Aucune leçon publiée.</p>}
        </section>
      </div>
    </section>
  )
}

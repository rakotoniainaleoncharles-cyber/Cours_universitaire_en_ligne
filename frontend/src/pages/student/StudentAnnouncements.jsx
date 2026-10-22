import { useCallback, useEffect, useState } from 'react'
import api from '../../services/api'
import SocialFeed from '../../components/SocialFeed'
import { useAutoRefresh } from '../../utils/dataSync'
import UserAvatar from '../../components/UserAvatar'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Impossible de charger les annonces.'
}

export default function StudentAnnouncements() {
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAnnouncements = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/announcements/')
      setAnnouncements(data)
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAnnouncements()
  }, [loadAnnouncements])
  useAutoRefresh(() => loadAnnouncements({ silent: true }))

  return (
    <section className="teacher-dashboard">
      <SocialFeed />
      <section className="student-announcements">
        <div className="teacher-panel-heading"><div><h3>Annonces de mes cours</h3><p>Les informations partagées par les professeurs de vos cours.</p></div></div>
        {error && <div className="error-message" role="alert">{error}</div>}
        {loading ? <p className="teacher-empty">Chargement des annonces...</p> : announcements.length ? (
          <div className="student-announcement-list">
            {announcements.map((announcement) => (
              <article className="student-announcement-card" key={announcement.id}>
                <div className="social-post-header">
                  <UserAvatar className="social-post-avatar" src={announcement.teacher_avatar_url} name={announcement.teacher_name || 'Professeur'} />
                  <div><strong>{announcement.teacher_name}</strong><small>{new Date(announcement.published_at || announcement.created_at).toLocaleString('fr-FR')}</small></div>
                </div>
                <p className="student-announcement-course">{announcement.course_title}</p>
                <h4>{announcement.title}</h4>
                <p className="social-post-content">{announcement.content}</p>
                {announcement.modified_by_role === 'admin' && (
                  <p className="announcement-admin-update" role="status">
                    Dernière modification par l’administration · {announcement.modified_by_name}
                    {' · '}{new Date(announcement.updated_at || announcement.created_at).toLocaleString('fr-FR')}
                  </p>
                )}
              </article>
            ))}
          </div>
        ) : <p className="teacher-no-items">Aucune annonce de cours pour le moment.</p>}
      </section>
    </section>
  )
}

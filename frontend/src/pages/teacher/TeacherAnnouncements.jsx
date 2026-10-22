import { useCallback, useEffect, useState } from 'react'
import { Check, Pencil, Trash2, X } from 'lucide-react'
import api from '../../services/api'
import { useAuth } from '../../context/AuthContext'
import SocialFeed from '../../components/SocialFeed'
import { useAutoRefresh } from '../../utils/dataSync'

const emptyForm = { course: '', title: '', content: '', status: 'draft' }

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Une erreur est survenue. Vérifiez la connexion et les informations saisies.'
}

export default function TeacherAnnouncements() {
  const { user } = useAuth()
  const [courses, setCourses] = useState([])
  const [announcements, setAnnouncements] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editing, setEditing] = useState(null)
  const [formOpen, setFormOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const manageableCourses = courses.filter((course) => course.teacher === user?.id)

  const loadData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const [courseResponse, announcementResponse] = await Promise.all([
        api.get('/courses/'),
        api.get('/announcements/'),
      ])
      setCourses(courseResponse.data)
      setAnnouncements(announcementResponse.data)
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])
  useAutoRefresh(() => loadData({ silent: true }))

  const openEditForm = (announcement) => {
    setEditing(announcement)
    setForm({
      course: String(announcement.course),
      title: announcement.title,
      content: announcement.content,
      status: announcement.status,
    })
    setError('')
    setNotice('')
    setFormOpen(true)
  }

  const saveAnnouncement = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      if (editing) {
        await api.patch(`/announcements/${editing.id}/`, form)
        setNotice('La publication a été mise à jour.')
      } else {
        await api.post('/announcements/', form)
        setNotice('La publication a été créée.')
      }
      setFormOpen(false)
      setEditing(null)
      setForm(emptyForm)
      await loadData()
    } catch (saveError) {
      setError(messageFrom(saveError))
    } finally {
      setSaving(false)
    }
  }

  const togglePublication = async (announcement) => {
    setError('')
    setNotice('')
    try {
      const status = announcement.status === 'published' ? 'draft' : 'published'
      await api.patch(`/announcements/${announcement.id}/`, { status })
      setNotice(status === 'published' ? 'La publication est visible aux étudiants inscrits.' : 'La publication est repassée en brouillon.')
      await loadData()
    } catch (updateError) {
      setError(messageFrom(updateError))
    }
  }

  const deleteAnnouncement = async (announcement) => {
    if (!window.confirm(`Supprimer la publication « ${announcement.title} » ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/announcements/${announcement.id}/`)
      setNotice('La publication a été supprimée.')
      await loadData()
    } catch (deleteError) {
      setError(messageFrom(deleteError))
    }
  }

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading">
        <div><h2>Annonces et publications</h2><p>Consultez les annonces de vos cours et de vos matières attribuées. Les changements de l’administration sont signalés ici.</p></div>
      </div>
      <SocialFeed />
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      {!loading && !manageableCourses.length && <p className="teacher-hint">Aucun cours à votre nom ne permet de créer une annonce pour le moment.</p>}

      {formOpen && (
        <form className="teacher-form-card" onSubmit={saveAnnouncement}>
          <div className="teacher-form-heading">
            <div><h3>{editing ? 'Modifier la publication' : 'Créer une publication'}</h3><p>Les étudiants inscrits ne verront que les publications de cours publiés.</p></div>
            <button type="button" className="icon-button" aria-label="Fermer le formulaire" onClick={() => setFormOpen(false)}><X size={18} /></button>
          </div>
          <div className="teacher-form-grid">
            <label className="input-group"><span>Cours</span>
              <select required value={form.course} onChange={(event) => setForm({ ...form, course: event.target.value })}>
                <option value="">Choisir un cours</option>
                {manageableCourses.map((course) => <option key={course.id} value={course.id}>{course.title} — {course.subject_name}</option>)}
              </select>
            </label>
            <label className="input-group"><span>Titre</span><input required maxLength={200} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
            <label className="input-group teacher-wide-field"><span>Contenu</span><textarea required rows={5} value={form.content} onChange={(event) => setForm({ ...form, content: event.target.value })} /></label>
            <label className="teacher-checkbox"><input type="checkbox" checked={form.status === 'published'} onChange={(event) => setForm({ ...form, status: event.target.checked ? 'published' : 'draft' })} /> Publier maintenant</label>
          </div>
          <div className="teacher-form-actions">
            <button type="button" className="secondary-button" onClick={() => setFormOpen(false)}>Annuler</button>
            <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Enregistrement...' : editing ? 'Enregistrer' : 'Créer'}</button>
          </div>
        </form>
      )}

      <div className="teacher-course-panel">
        {loading ? <p className="teacher-empty">Chargement des publications...</p> : announcements.length ? (
          <ul className="teacher-item-list">
            {announcements.map((announcement) => (
              <li key={announcement.id}>
                <div>
                  <strong>{announcement.title}</strong>
                  <p>
                    {announcement.course_title} · {announcement.status === 'published' ? 'Publiée' : 'Brouillon'}
                    {' · '}Créée le {new Date(announcement.created_at).toLocaleDateString('fr-FR')}
                  </p>
                  <p className="announcement-content">{announcement.content}</p>
                  {announcement.modified_by_role === 'admin' && (
                    <p className="announcement-admin-update" role="status">
                      Dernière intervention de l’administration · {announcement.modified_by_name}
                      {' · '}{new Date(announcement.updated_at || announcement.created_at).toLocaleString('fr-FR')}
                    </p>
                  )}
                </div>
                {announcement.teacher_id === courses.find((course) => course.id === announcement.course)?.teacher && (
                  <div className="user-row-actions">
                    <button type="button" className="table-action" aria-label={`Modifier ${announcement.title}`} onClick={() => openEditForm(announcement)}><Pencil size={15} /></button>
                    <button type="button" className="table-action" aria-label={announcement.status === 'published' ? 'Dépublier' : 'Publier'} onClick={() => togglePublication(announcement)}>{announcement.status === 'published' ? <X size={15} /> : <Check size={15} />}</button>
                    <button type="button" className="table-action danger" aria-label={`Supprimer ${announcement.title}`} onClick={() => deleteAnnouncement(announcement)}><Trash2 size={15} /></button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : <p className="teacher-no-items">Aucune publication créée.</p>}
      </div>
    </section>
  )
}

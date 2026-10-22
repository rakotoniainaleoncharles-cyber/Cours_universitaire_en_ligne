import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, BookOpen, FileText, Search, Trash2, Users } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import SocialFeed from '../../components/SocialFeed'
import { useAutoRefresh } from '../../utils/dataSync'
import UserAvatar from '../../components/UserAvatar'

const labels = {
  student_count: 'Étudiants',
  teacher_count: 'Professeurs',
  active_user_count: 'Comptes actifs',
  inactive_user_count: 'Comptes inactifs',
  faculty_count: 'Filières',
  level_count: 'Niveaux',
  academic_year_count: 'Années académiques',
  subject_count: 'Matières',
  course_count: 'Cours',
  lesson_count: 'Leçons',
  material_count: 'Documents pédagogiques',
  enrollment_count: 'Inscriptions',
  assignment_count: 'Devoirs',
  submission_count: 'Travaux remis',
}

const metricGroups = [
  { title: 'Comptes', icon: Users, className: 'accounts', keys: ['student_count', 'teacher_count', 'active_user_count', 'inactive_user_count'] },
  { title: 'Structure académique', icon: BookOpen, className: 'academics', keys: ['faculty_count', 'level_count', 'academic_year_count', 'subject_count', 'enrollment_count'] },
  { title: 'Activité pédagogique', icon: FileText, className: 'learning', keys: ['course_count', 'lesson_count', 'material_count', 'assignment_count', 'submission_count'] },
]

function getErrorMessage(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const message = Object.values(data).flat().find((value) => typeof value === 'string')
    if (message) return message
  }
  return 'Impossible de charger les données administratives.'
}

export default function AdminDashboard({ section = 'overview' }) {
  const [stats, setStats] = useState(null)
  const [courses, setCourses] = useState([])
  const [assignments, setAssignments] = useState([])
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [teacherFilter, setTeacherFilter] = useState('')
  const [facultyFilter, setFacultyFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      if (section === 'overview') {
        const { data } = await api.get('/admin/dashboard/')
        setStats(data)
      } else {
        if (section === 'assignments') {
          const [courseResponse, assignmentResponse] = await Promise.all([api.get('/courses/'), api.get('/assignments/')])
          setCourses(courseResponse.data)
          setAssignments(assignmentResponse.data)
        } else if (section === 'announcements') {
          const { data } = await api.get('/announcements/')
          setAnnouncements(data)
        } else {
          const { data } = await api.get('/courses/')
          setCourses(data)
        }
      }
    } catch (loadError) {
      setError(getErrorMessage(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [section])

  useEffect(() => {
    loadData()
  }, [loadData])
  useAutoRefresh(() => loadData({ silent: true }))

  const materials = useMemo(
    () => courses.flatMap((course) => (course.materials || []).map((material) => ({
      ...material, course_title: course.title, teacher_name: course.teacher_name, teacher_id: course.teacher,
    }))),
    [courses],
  )
  const lessons = useMemo(
    () => courses.flatMap((course) => (course.lessons || []).map((lesson) => ({
      ...lesson,
      course_title: course.title,
      teacher_name: course.teacher_name,
      teacher_id: course.teacher,
      faculty_name: course.faculty_name,
    }))),
    [courses],
  )
  const isDocuments = section === 'documents'
  const isLessons = section === 'lessons'
  const isAssignments = section === 'assignments'
  const isAnnouncements = section === 'announcements'
  const rows = section === 'documents' ? materials : section === 'lessons' ? lessons : section === 'assignments' ? assignments : isAnnouncements ? announcements : courses
  const filteredRows = rows.filter((row) => {
    const query = search.trim().toLocaleLowerCase()
    const searchable = section === 'documents'
      ? `${row.title} ${row.description} ${row.file_name} ${row.course_title} ${row.teacher_name}`
      : section === 'assignments'
        ? `${row.title} ${row.instructions} ${row.course_title} ${row.teacher_name}`
      : section === 'lessons'
        ? `${row.title} ${row.description} ${row.course_title} ${row.teacher_name}`
      : isAnnouncements
        ? `${row.title} ${row.content} ${row.course_title} ${row.teacher_name}`
        : `${row.title} ${row.description} ${row.subject_name} ${row.faculty_name} ${row.teacher_name}`
    const matchesTeacher = !teacherFilter || String(row.teacher_id ?? row.teacher ?? '') === teacherFilter
    const matchesFaculty = !facultyFilter || row.faculty_name === facultyFilter
    const rowStatus = isAssignments ? (row.is_published ? 'published' : 'draft') : row.status
    const matchesStatus = !statusFilter || rowStatus === statusFilter
    return (!query || searchable.toLocaleLowerCase().includes(query)) && matchesTeacher && matchesFaculty && matchesStatus
  })
  const safePage = Math.min(page, Math.max(1, Math.ceil(filteredRows.length / 10)))
  const visibleRows = filteredRows.slice((safePage - 1) * 10, safePage * 10)
  const teacherOptions = [...new Map([
    ...courses.map((course) => [course.teacher, course.teacher_name]),
    ...announcements.map((announcement) => [announcement.teacher_id, announcement.teacher_name]),
  ].filter(([id]) => id).entries())]
  const facultyOptions = [...new Set([
    ...courses.map((course) => course.faculty_name),
    ...announcements.map((announcement) => announcement.faculty_name),
  ].filter(Boolean))]

  const removeCourse = async (course) => {
    if (!window.confirm(`Supprimer le cours « ${course.title} », ses leçons et documents associés ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/courses/${course.id}/`)
      setNotice('Le cours et son contenu associé ont été supprimés.')
      await loadData()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const removeMaterial = async (material) => {
    if (!window.confirm(`Supprimer le document « ${material.title} » ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/materials/${material.id}/`)
      setNotice('Le document a été supprimé.')
      await loadData()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const downloadMaterial = async (material) => {
    setError('')
    try {
      const { data } = await api.get(`/materials/${material.id}/download/`, { responseType: 'blob' })
      const url = URL.createObjectURL(data)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = material.file_name || material.title
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (downloadError) {
      setError(getErrorMessage(downloadError))
    }
  }

  const removeLesson = async (lesson) => {
    if (!window.confirm(`Supprimer la leçon « ${lesson.title} » ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/lessons/${lesson.id}/`)
      setNotice('La leçon a été supprimée.')
      await loadData()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const removeAnnouncement = async (announcement) => {
    if (!window.confirm(`Supprimer la publication « ${announcement.title} » ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/announcements/${announcement.id}/`)
      setNotice('La publication a été supprimée.')
      await loadData()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const togglePublication = async (item, kind) => {
    const endpoint = kind === 'course' ? `/courses/${item.id}/` : kind === 'announcement' ? `/announcements/${item.id}/` : `/lessons/${item.id}/`
    const current = item.status === 'published'
    setError('')
    setNotice('')
    try {
      await api.patch(endpoint, { status: current ? 'draft' : 'published' })
      setNotice(`${kind === 'course' ? 'Le cours' : kind === 'announcement' ? 'La publication' : 'La leçon'} a été ${current ? 'dépublié' : 'publié'}.`)
      await loadData()
    } catch (updateError) {
      setError(getErrorMessage(updateError))
    }
  }

  if (section === 'overview') {
    return (
      <section className="admin-dashboard admin-overview">
        <header className="admin-overview-hero">
          <div className="admin-overview-welcome">
            <span className="admin-overview-eyebrow"><Activity size={15} /> Vue d’ensemble</span>
            <h2>Bonjour, bienvenue dans votre espace admin</h2>
            <p>Suivez la vie de votre plateforme et accédez rapidement à ses indicateurs clés.</p>
          </div>
          {!loading && stats && (
            <div className="admin-overview-community">
              <span>Votre communauté</span>
              <div><strong>{stats.student_count}</strong><span>étudiants</span></div>
              <div><strong>{stats.teacher_count}</strong><span>professeurs</span></div>
            </div>
          )}
        </header>
        {error && <div className="error-message" role="alert">{error}</div>}
        {loading ? <p className="teacher-empty">Chargement des statistiques...</p> : stats && (
          <>
            {metricGroups.map(({ title, icon: Icon, className, keys }) => (
              <section className={`admin-metric-section ${className}`} key={title}>
                <div className="admin-metric-heading"><span><Icon size={18} /></span><h3>{title}</h3></div>
                <div className="admin-metric-grid">
                  {keys.map((key) => (
                    <article className="admin-metric-card" key={key}>
                      <span>{labels[key]}</span><strong>{stats[key] ?? 0}</strong>
                    </article>
                  ))}
                </div>
              </section>
            ))}
            <div className="teacher-content-columns">
              <section className="teacher-course-panel">
                <div className="teacher-panel-heading"><div><h3><Users size={19} /> Derniers comptes créés</h3></div></div>
                {stats.recent_users.length ? <ul className="teacher-item-list">
                  {stats.recent_users.map((user) => (
                    <li key={user.id}>
                      <div className="admin-recent-user">
                        <UserAvatar src={user.avatar_url} name={`${user.first_name} ${user.last_name}`} />
                        <div><strong>{user.first_name} {user.last_name}</strong><p>{user.email} · {user.role} · {user.is_active ? 'Actif' : 'Inactif'}</p></div>
                      </div>
                      <small>{new Date(user.created_at).toLocaleDateString('fr-FR')}</small>
                    </li>
                  ))}
                </ul> : <p className="teacher-no-items">Aucun compte enregistré.</p>}
              </section>
              <section className="teacher-course-panel">
                <div className="teacher-panel-heading"><div><h3><FileText size={19} /> Activité administrative récente</h3></div></div>
                {stats.recent_activity.length ? <ul className="teacher-item-list">
                  {stats.recent_activity.map((entry) => (
                    <li key={entry.id}>
                      <div><strong>{entry.description}</strong><p>{entry.actor__email || 'Compte administrateur'} · {entry.action}</p></div>
                      <small>{new Date(entry.created_at).toLocaleString('fr-FR')}</small>
                    </li>
                  ))}
                </ul> : <p className="teacher-no-items">Aucune activité journalisée pour le moment.</p>}
              </section>
            </div>
          </>
        )}
      </section>
    )
  }

  return (
    <section className="admin-dashboard">
      <div className="teacher-heading"><div><h2>{isDocuments ? 'Documents pédagogiques' : isLessons ? 'Supervision des leçons' : isAssignments ? 'Supervision des devoirs' : isAnnouncements ? 'Supervision des annonces' : 'Supervision des cours'}</h2><p>{isDocuments ? 'Consultez et retirez les documents publiés par les professeurs.' : isAssignments ? 'Consultez les devoirs et les volumes de remises sans modifier les évaluations.' : isAnnouncements ? 'Consultez et modérez les publications liées aux cours.' : 'Consultez et modérez les contenus pédagogiques de la plateforme.'}</p></div></div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      {isAnnouncements && <SocialFeed admin />}
      <div className="teacher-course-filters">
        <label className="user-search teacher-search"><Search size={17} /><input aria-label="Rechercher" placeholder="Rechercher dans la liste" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} /></label>
        <select aria-label="Filtrer par professeur" value={teacherFilter} onChange={(event) => { setTeacherFilter(event.target.value); setPage(1) }}><option value="">Tous les professeurs</option>{teacherOptions.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select>
        {!isDocuments && <select aria-label="Filtrer par filière" value={facultyFilter} onChange={(event) => { setFacultyFilter(event.target.value); setPage(1) }}><option value="">Toutes les filières</option>{facultyOptions.map((name) => <option key={name} value={name}>{name}</option>)}</select>}
        {!isDocuments && <select aria-label="Filtrer par statut" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1) }}><option value="">Tous les statuts</option><option value="published">Publiés</option><option value="draft">Brouillons</option></select>}
      </div>
      <div className="user-table-card">
        {loading ? <p className="user-table-empty">Chargement...</p> : filteredRows.length === 0 ? <p className="user-table-empty">Aucun résultat.</p> : (
          <div className="user-table-scroll">
            <table className="user-table">
              {isDocuments ? (
                <>
                  <thead><tr><th>Document</th><th>Cours / leçon</th><th>Professeur</th><th>Envoyé le</th><th>Actions</th></tr></thead>
                  <tbody>{visibleRows.map((material) => (
                    <tr key={material.id}>
                      <td data-label="Document"><strong>{material.title}</strong><br /><small>{material.file_name} · {Math.max(1, Math.round(material.file_size / 1024))} Ko</small></td>
                      <td data-label="Cours / leçon">{material.course_title}</td><td data-label="Professeur">{material.teacher_name}</td>
                      <td data-label="Envoyé le">{new Date(material.uploaded_at).toLocaleDateString('fr-FR')}</td>
                      <td data-label="Actions"><div className="user-row-actions"><button type="button" className="secondary-button teacher-small-button" onClick={() => downloadMaterial(material)}>Télécharger</button><button type="button" className="table-action danger" aria-label={`Supprimer ${material.title}`} onClick={() => removeMaterial(material)}><Trash2 size={16} /></button></div></td>
                    </tr>
                  ))}</tbody>
                </>
              ) : isLessons ? (
                <>
                  <thead><tr><th>Leçon</th><th>Cours</th><th>Professeur</th><th>Publication</th><th>Actions</th></tr></thead>
                  <tbody>{visibleRows.map((lesson) => (
                    <tr key={lesson.id}><td data-label="Leçon"><strong>{lesson.title}</strong><br /><small>Ordre {lesson.order + 1}</small></td><td data-label="Cours">{lesson.course_title}</td><td data-label="Professeur">{lesson.teacher_name}</td><td data-label="Publication">{lesson.published_at ? new Date(lesson.published_at).toLocaleDateString('fr-FR') : 'Brouillon'}</td>
                      <td data-label="Actions"><div className="user-row-actions"><button type="button" className="secondary-button teacher-small-button" onClick={() => togglePublication(lesson, 'lesson')}>{lesson.status === 'published' ? 'Dépublier' : 'Publier'}</button><button type="button" className="table-action danger" aria-label={`Supprimer ${lesson.title}`} onClick={() => removeLesson(lesson)}><Trash2 size={16} /></button></div></td>
                    </tr>
                  ))}</tbody>
                </>
              ) : isAssignments ? (
                <>
                  <thead><tr><th>Devoir</th><th>Cours</th><th>Professeur</th><th>Échéance</th><th>Remises</th><th>Statut</th></tr></thead>
                  <tbody>{visibleRows.map((assignment) => (
                    <tr key={assignment.id}><td data-label="Devoir"><strong>{assignment.title}</strong></td><td data-label="Cours">{assignment.course_title}</td><td data-label="Professeur">{assignment.teacher_name}</td><td data-label="Échéance">{assignment.due_at ? new Date(assignment.due_at).toLocaleString('fr-FR') : 'Aucune'}</td><td data-label="Remises">{assignment.submission_count} ({assignment.pending_count} à corriger)</td><td data-label="Statut">{assignment.is_published ? 'Publié' : 'Brouillon'}</td></tr>
                  ))}</tbody>
                </>
              ) : isAnnouncements ? (
                <>
                  <thead><tr><th>Publication</th><th>Cours</th><th>Filière</th><th>Professeur</th><th>Créée le</th><th>Statut</th><th>Actions</th></tr></thead>
                  <tbody>{visibleRows.map((announcement) => (
                    <tr key={announcement.id}>
                      <td data-label="Publication"><strong>{announcement.title}</strong><br /><small>{announcement.content}</small></td>
                      <td data-label="Cours">{announcement.course_title}</td><td data-label="Filière">{announcement.faculty_name}</td><td data-label="Professeur">{announcement.teacher_name}</td>
                      <td data-label="Créée le">{new Date(announcement.created_at).toLocaleDateString('fr-FR')}</td>
                      <td data-label="Statut">{announcement.status === 'published' ? 'Publié' : 'Brouillon'}</td>
                      <td data-label="Actions"><div className="user-row-actions"><button type="button" className="secondary-button teacher-small-button" onClick={() => togglePublication(announcement, 'announcement')}>{announcement.status === 'published' ? 'Dépublier' : 'Publier'}</button><button type="button" className="table-action danger" aria-label={`Supprimer ${announcement.title}`} onClick={() => removeAnnouncement(announcement)}><Trash2 size={16} /></button></div></td>
                    </tr>
                  ))}</tbody>
                </>
              ) : (
                <>
                  <thead><tr><th>Cours</th><th>Matière</th><th>Filière</th><th>Professeur</th><th>Leçons</th><th>Statut</th><th>Actions</th></tr></thead>
                  <tbody>{visibleRows.map((course) => (
                    <tr key={course.id}>
                      <td data-label="Cours"><strong>{course.title}</strong><br /><small>{course.published_at ? `Publié ${new Date(course.published_at).toLocaleDateString('fr-FR')}` : 'Non publié'}</small></td>
                      <td data-label="Matière">{course.subject_name}</td><td data-label="Filière">{course.faculty_name}</td><td data-label="Professeur">{course.teacher_name}</td>
                      <td data-label="Leçons">{course.lessons?.length || 0}</td><td data-label="Statut">{course.status === 'published' ? 'Publié' : 'Brouillon'}</td>
                      <td data-label="Actions"><div className="user-row-actions"><button type="button" className="secondary-button teacher-small-button" onClick={() => togglePublication(course, 'course')}>{course.status === 'published' ? 'Dépublier' : 'Publier'}</button><button type="button" className="table-action danger" aria-label={`Supprimer ${course.title}`} onClick={() => removeCourse(course)}><Trash2 size={16} /></button></div></td>
                    </tr>
                  ))}</tbody>
                </>
              )}
            </table>
          </div>
        )}
        {!loading && filteredRows.length > 0 && <Pagination page={safePage} pageSize={10} total={filteredRows.length} onPageChange={setPage} />}
      </div>
    </section>
  )
}

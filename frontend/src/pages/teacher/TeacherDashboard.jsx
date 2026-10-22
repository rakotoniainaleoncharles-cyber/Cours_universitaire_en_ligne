import { useCallback, useEffect, useState } from 'react'
import { BookOpen, Check, ClipboardCheck, FilePlus2, FileText, GraduationCap, Pencil, Plus, Search, Trash2, Upload, Users, X } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { downloadPrivateFile } from '../../utils/download'
import { useAutoRefresh } from '../../utils/dataSync'

const emptyCourse = { title: '', description: '', objectives: '', subject: '', status: 'draft' }
const emptyLesson = { title: '', description: '', content: '', order: 0, status: 'draft' }
const emptyMaterial = { title: '', description: '', file: null, lesson: '' }

function getErrorMessage(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const firstError = Object.values(data).flat().find((value) => typeof value === 'string')
    if (firstError) return firstError
  }
  return 'Une erreur est survenue. Vérifiez la connexion et les informations saisies.'
}

function makeSlug(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export default function TeacherDashboard({ section = 'dashboard' }) {
  const [courses, setCourses] = useState([])
  const [subjects, setSubjects] = useState([])
  const [subjectsLoading, setSubjectsLoading] = useState(true)
  const [subjectsError, setSubjectsError] = useState('')
  const [dashboard, setDashboard] = useState(null)
  const [selectedCourseId, setSelectedCourseId] = useState('')
  const [courseForm, setCourseForm] = useState(emptyCourse)
  const [lessonForm, setLessonForm] = useState(emptyLesson)
  const [materialForm, setMaterialForm] = useState(emptyMaterial)
  const [editingCourse, setEditingCourse] = useState(null)
  const [editingLesson, setEditingLesson] = useState(null)
  const [editingMaterial, setEditingMaterial] = useState(null)
  const [courseSearch, setCourseSearch] = useState('')
  const [courseStatusFilter, setCourseStatusFilter] = useState('all')
  const [courseOrdering, setCourseOrdering] = useState('-created_at')
  const [lessonSearch, setLessonSearch] = useState('')
  const [lessonStatusFilter, setLessonStatusFilter] = useState('all')
  const [lessonPage, setLessonPage] = useState(1)
  const [materialSearch, setMaterialSearch] = useState('')
  const [materialPage, setMaterialPage] = useState(1)
  const [showCourseForm, setShowCourseForm] = useState(false)
  const [showLessonForm, setShowLessonForm] = useState(false)
  const [showMaterialForm, setShowMaterialForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadDashboard = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const [coursesResponse, dashboardResponse] = await Promise.all([
        api.get('/courses/'),
        api.get('/teacher/dashboard/'),
      ])
      setCourses(coursesResponse.data)
      setDashboard(dashboardResponse.data)
      setSelectedCourseId((currentId) => (
        coursesResponse.data.some((course) => String(course.id) === String(currentId))
          ? currentId
          : String(coursesResponse.data[0]?.id || '')
      ))
    } catch (loadError) {
      setError(getErrorMessage(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  const loadSubjects = useCallback(async () => {
    setSubjectsLoading(true)
    setSubjectsError('')
    try {
      const { data } = await api.get('/teacher/subjects/')
      setSubjects(data)
      return data
    } catch (loadError) {
      setSubjectsError(getErrorMessage(loadError))
      setSubjects([])
      return []
    } finally {
      setSubjectsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])
  useAutoRefresh(() => loadDashboard({ silent: true }))

  const selectedCourse = courses.find((course) => String(course.id) === String(selectedCourseId))
  const visibleCourses = courses
    .filter((course) => {
      const query = courseSearch.trim().toLowerCase()
      return (!query || `${course.title} ${course.subject_name}`.toLowerCase().includes(query))
        && (courseStatusFilter === 'all' || course.status === courseStatusFilter)
    })
    .sort((left, right) => {
      if (courseOrdering === 'title') return left.title.localeCompare(right.title)
      if (courseOrdering === '-title') return right.title.localeCompare(left.title)
      return courseOrdering === 'created_at'
        ? new Date(left.created_at) - new Date(right.created_at)
        : new Date(right.created_at) - new Date(left.created_at)
    })
  const visibleLessons = (selectedCourse?.lessons || []).filter((lesson) => (
    (!lessonSearch || `${lesson.title} ${lesson.description}`.toLowerCase().includes(lessonSearch.toLowerCase()))
      && (lessonStatusFilter === 'all' || lesson.status === lessonStatusFilter)
  ))
  const visibleMaterials = (selectedCourse?.materials || []).filter((material) => (
    !materialSearch || `${material.title} ${material.description} ${material.file_name}`.toLowerCase().includes(materialSearch.toLowerCase())
  ))
  const safeLessonPage = Math.min(lessonPage, Math.max(1, Math.ceil(visibleLessons.length / 10)))
  const pageLessons = visibleLessons.slice((safeLessonPage - 1) * 10, safeLessonPage * 10)
  const safeMaterialPage = Math.min(materialPage, Math.max(1, Math.ceil(visibleMaterials.length / 10)))
  const pageMaterials = visibleMaterials.slice((safeMaterialPage - 1) * 10, safeMaterialPage * 10)

  if (section === 'dashboard') {
    return (
      <section className="teacher-dashboard">
        <div className="teacher-heading">
          <div>
            <h2>Tableau de bord professeur</h2>
            <p>Vos matières, cours, étudiants et activités récentes, actualisés depuis la base de données.</p>
          </div>
        </div>
        {error && <div className="error-message" role="alert">{error}</div>}
        {loading ? <p className="teacher-empty">Chargement de vos données...</p> : dashboard && (
          <>
            <div className="dashboard-grid teacher-stats">
              <article className="teacher-stat-card subjects">
                <span className="teacher-stat-icon"><GraduationCap size={20} /></span>
                <div><span className="teacher-stat-label">Matières attribuées</span><strong>{dashboard.subject_count}</strong></div>
              </article>
              <article className="teacher-stat-card courses">
                <span className="teacher-stat-icon"><BookOpen size={20} /></span>
                <div><span className="teacher-stat-label">Cours</span><strong>{dashboard.course_count}</strong></div>
              </article>
              <article className="teacher-stat-card lessons">
                <span className="teacher-stat-icon"><FileText size={20} /></span>
                <div><span className="teacher-stat-label">Leçons</span><strong>{dashboard.lesson_count}</strong></div>
              </article>
              <article className="teacher-stat-card students">
                <span className="teacher-stat-icon"><Users size={20} /></span>
                <div><span className="teacher-stat-label">Étudiants inscrits</span><strong>{dashboard.student_count}</strong></div>
              </article>
              <article className="teacher-stat-card materials">
                <span className="teacher-stat-icon"><FilePlus2 size={20} /></span>
                <div><span className="teacher-stat-label">Documents pédagogiques</span><strong>{dashboard.material_count}</strong></div>
              </article>
              <article className="teacher-stat-card assignments">
                <span className="teacher-stat-icon"><ClipboardCheck size={20} /></span>
                <div><span className="teacher-stat-label">Devoirs à corriger</span><strong>{dashboard.pending_submissions}</strong></div>
              </article>
            </div>
            <div className="teacher-content-columns">
              <section className="teacher-course-panel">
                <div className="teacher-panel-heading"><div><h3><BookOpen size={19} /> Derniers cours</h3></div></div>
                {dashboard.recent_courses.length ? (
                  <ul className="teacher-item-list">
                    {dashboard.recent_courses.map((course) => (
                      <li key={course.id}>
                        <div>
                          <strong>{course.title}</strong>
                          <p>{course.subject_name} · {course.status === 'published' ? 'Publié' : 'Brouillon'}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : <p className="teacher-no-items">Aucun cours créé.</p>}
              </section>
              <section className="teacher-course-panel">
                <div className="teacher-panel-heading"><div><h3><ClipboardCheck size={19} /> Dernières leçons</h3></div></div>
                {dashboard.recent_lessons.length ? (
                  <ul className="teacher-item-list">
                    {dashboard.recent_lessons.map((lesson) => (
                      <li key={lesson.id}>
                        <div><strong>{lesson.title}</strong><p>{lesson.course_title || courses.find((course) => course.id === lesson.course)?.title || 'Cours'} · {lesson.status === 'published' ? 'Publiée' : 'Brouillon'}</p></div>
                      </li>
                    ))}
                  </ul>
                ) : <p className="teacher-no-items">Aucune leçon créée.</p>}
              </section>
            </div>
          </>
        )}
      </section>
    )
  }

  const submitCourse = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const payload = {
        ...courseForm,
        subject: Number(courseForm.subject),
        slug: makeSlug(courseForm.title),
      }
      if (editingCourse) {
        await api.patch(`/courses/${editingCourse.id}/`, payload)
      } else {
        await api.post('/courses/', payload)
      }
      setCourseForm(emptyCourse)
      setEditingCourse(null)
      setShowCourseForm(false)
      setNotice(editingCourse ? 'Le cours a été modifié.' : 'Le cours a été créé.')
      await loadDashboard()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSaving(false)
    }
  }

  const openNewCourseForm = async () => {
    setEditingCourse(null)
    setCourseForm(emptyCourse)
    setShowCourseForm(true)
    const assignedSubjects = await loadSubjects()
    setCourseForm({ ...emptyCourse, subject: String(assignedSubjects[0]?.id || '') })
  }

  const submitLesson = async (event) => {
    event.preventDefault()
    if (!selectedCourse) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const payload = {
        ...lessonForm,
        order: Number(lessonForm.order),
      }
      if (editingLesson) {
        await api.patch(`/lessons/${editingLesson.id}/`, payload)
      } else {
        await api.post(`/courses/${selectedCourse.id}/lessons/`, payload)
      }
      setLessonForm(emptyLesson)
      setEditingLesson(null)
      setShowLessonForm(false)
      setNotice(editingLesson ? 'La leçon a été modifiée.' : 'La leçon a été ajoutée au cours.')
      await loadDashboard()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSaving(false)
    }
  }

  const submitMaterial = async (event) => {
    event.preventDefault()
    if (!selectedCourse || (!materialForm.file && !editingMaterial)) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const payload = new FormData()
      payload.append('title', materialForm.title)
      payload.append('description', materialForm.description)
      if (materialForm.file) payload.append('file', materialForm.file)
      if (materialForm.lesson) payload.append('lesson', materialForm.lesson)
      const endpoint = editingMaterial
        ? `/materials/${editingMaterial.id}/`
        : `/courses/${selectedCourse.id}/materials/`
      await api.request({
        method: editingMaterial ? 'PATCH' : 'POST',
        url: endpoint,
        data: payload,
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMaterialForm(emptyMaterial)
      setEditingMaterial(null)
      setShowMaterialForm(false)
      setNotice(editingMaterial ? 'Le document a été modifié.' : 'Le document a été téléversé.')
      await loadDashboard()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSaving(false)
    }
  }

  const deleteCourse = async (course) => {
    if (!window.confirm(`Supprimer le cours « ${course.title} » et son contenu ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/courses/${course.id}/`)
      setNotice('Le cours a été supprimé.')
      await loadDashboard()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const deleteLesson = async (lesson) => {
    if (!window.confirm(`Supprimer la leçon « ${lesson.title} » ?`)) return
    setError('')
    try {
      await api.delete(`/lessons/${lesson.id}/`)
      setNotice('La leçon a été supprimée.')
      await loadDashboard()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const deleteMaterial = async (material) => {
    if (!window.confirm(`Supprimer le document « ${material.title} » ?`)) return
    setError('')
    try {
      await api.delete(`/materials/${material.id}/`)
      setNotice('Le document a été supprimé.')
      await loadDashboard()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const openMaterial = async (material) => {
    setError('')
    try {
      await downloadPrivateFile(material.file_url, material.file_name || material.title)
    } catch (fileError) {
      setError(getErrorMessage(fileError))
    }
  }

  const beginCourseEdit = (course) => {
    setEditingCourse(course)
    setCourseForm({
      title: course.title,
      description: course.description,
      objectives: course.objectives || '',
      subject: String(course.subject),
      status: course.status,
    })
    setShowCourseForm(true)
    setError('')
  }

  const toggleCourseStatus = async (course) => {
    setError('')
    setNotice('')
    try {
      const status = course.status === 'published' ? 'draft' : 'published'
      await api.patch(`/courses/${course.id}/`, { status })
      setNotice(status === 'published' ? 'Le cours est publié.' : 'Le cours est enregistré comme brouillon.')
      await loadDashboard()
    } catch (statusError) {
      setError(getErrorMessage(statusError))
    }
  }

  const beginLessonEdit = (lesson) => {
    setEditingLesson(lesson)
    setLessonForm({
      title: lesson.title,
      description: lesson.description,
      content: lesson.content,
      order: lesson.order,
      status: lesson.status,
    })
    setShowLessonForm(true)
    setError('')
  }

  const beginMaterialEdit = (material) => {
    setEditingMaterial(material)
    setMaterialForm({ title: material.title, description: material.description, file: null, lesson: material.lesson ? String(material.lesson) : '' })
    setShowMaterialForm(true)
    setError('')
  }

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading">
        <div>
          <h2>Espace professeur</h2>
          <p>Préparez vos cours, publiez des leçons et partagez des documents avec vos étudiants.</p>
        </div>
        <button type="button" className="primary-button teacher-add-course" onClick={openNewCourseForm}>
          <Plus size={17} /> Nouveau cours
        </button>
      </div>

      <div className="dashboard-grid teacher-stats">
        <article className="teacher-stat-card courses">
          <span className="teacher-stat-icon"><BookOpen size={20} /></span>
          <div><span className="teacher-stat-label">Mes cours</span><strong>{courses.length}</strong></div>
        </article>
        <article className="teacher-stat-card lessons">
          <span className="teacher-stat-icon"><FileText size={20} /></span>
          <div><span className="teacher-stat-label">Leçons</span><strong>{dashboard?.lesson_count ?? 0}</strong></div>
        </article>
        <article className="teacher-stat-card materials">
          <span className="teacher-stat-icon"><FilePlus2 size={20} /></span>
          <div><span className="teacher-stat-label">Documents partagés</span><strong>{dashboard?.material_count ?? 0}</strong></div>
        </article>
      </div>

      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}

      {showCourseForm && (
        <form className="teacher-form-card" onSubmit={submitCourse}>
          <div className="teacher-form-heading">
            <div><h3>{editingCourse ? 'Modifier le cours' : 'Créer un cours'}</h3><p>Les matières créées par l’administration apparaissent ici après leur attribution à votre compte.</p></div>
            <button type="button" className="icon-button" aria-label="Fermer" onClick={() => { setShowCourseForm(false); setEditingCourse(null) }}><X size={18} /></button>
          </div>
          <div className="teacher-form-grid">
            <label className="input-group">
              <span>Titre</span>
              <input required maxLength={200} value={courseForm.title} onChange={(event) => setCourseForm({ ...courseForm, title: event.target.value })} />
            </label>
            <label className="input-group">
              <span>Matière</span>
              <select required value={courseForm.subject} disabled={subjectsLoading || Boolean(subjectsError)} onChange={(event) => setCourseForm({ ...courseForm, subject: event.target.value })}>
                <option value="">{subjectsLoading ? 'Chargement des matières...' : 'Choisir une matière'}</option>
                {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.code} — {subject.name}</option>)}
              </select>
            </label>
            <label className="input-group teacher-wide-field">
              <span>Description</span>
              <textarea required rows={3} value={courseForm.description} onChange={(event) => setCourseForm({ ...courseForm, description: event.target.value })} />
            </label>
            <label className="input-group teacher-wide-field">
              <span>Objectifs pédagogiques</span>
              <textarea rows={3} value={courseForm.objectives} onChange={(event) => setCourseForm({ ...courseForm, objectives: event.target.value })} />
            </label>
            <label className="teacher-checkbox">
              <input type="checkbox" checked={courseForm.status === 'published'} onChange={(event) => setCourseForm({ ...courseForm, status: event.target.checked ? 'published' : 'draft' })} />
              Publier le cours
            </label>
          </div>
          {subjectsError && <p className="error-message" role="alert">Impossible de charger les matières : {subjectsError}</p>}
          {!subjectsLoading && !subjectsError && subjects.length === 0 && <p className="teacher-hint">Aucune matière ne vous est attribuée. Demandez à l’administration de vous affecter une matière dans la gestion des matières.</p>}
          <div className="teacher-form-actions">
            <button type="button" className="secondary-button" onClick={() => { setShowCourseForm(false); setEditingCourse(null) }}>Annuler</button>
            <button type="submit" className="primary-button" disabled={saving || subjectsLoading || Boolean(subjectsError) || subjects.length === 0 || !courseForm.subject}>{saving ? 'Enregistrement...' : editingCourse ? 'Enregistrer le cours' : 'Créer le cours'}</button>
          </div>
        </form>
      )}

      <div className="teacher-course-panel">
        <div className="teacher-panel-heading">
          <div><h3><BookOpen size={19} /> Mes cours</h3><p>Sélectionnez un cours pour gérer son contenu.</p></div>
          <div className="teacher-course-filters">
            <label className="user-search"><Search size={16} /><input aria-label="Rechercher un cours" placeholder="Rechercher un cours" value={courseSearch} onChange={(event) => setCourseSearch(event.target.value)} /></label>
            <select aria-label="Filtrer par statut" value={courseStatusFilter} onChange={(event) => setCourseStatusFilter(event.target.value)}>
              <option value="all">Tous les statuts</option><option value="draft">Brouillons</option><option value="published">Publiés</option>
            </select>
            <select aria-label="Trier les cours" value={courseOrdering} onChange={(event) => setCourseOrdering(event.target.value)}>
              <option value="-created_at">Plus récents</option><option value="created_at">Plus anciens</option><option value="title">Titre A–Z</option><option value="-title">Titre Z–A</option>
            </select>
            <select aria-label="Sélectionner un cours" value={selectedCourseId} onChange={(event) => { setSelectedCourseId(event.target.value); setLessonPage(1); setMaterialPage(1) }}>
              {visibleCourses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
            </select>
          </div>
        </div>

        {loading ? (
          <p className="teacher-empty">Chargement des cours...</p>
        ) : courses.length === 0 ? (
          <div className="teacher-empty">
            <GraduationCap size={30} />
            <strong>Vous n’avez pas encore de cours.</strong>
            <span>Créez votre premier cours pour commencer à publier du contenu.</span>
          </div>
        ) : visibleCourses.length === 0 ? (
          <p className="teacher-empty">Aucun cours ne correspond aux filtres sélectionnés.</p>
        ) : selectedCourse ? (
          <>
            <div className="teacher-course-summary">
              <div>
                <span className="teacher-subject-label">{selectedCourse.subject_name || 'Matière'}</span>
                <h4>{selectedCourse.title}</h4>
                <p>{selectedCourse.description}</p>
                {selectedCourse.objectives && <p><strong>Objectifs :</strong> {selectedCourse.objectives}</p>}
                <span className={`role-badge role-${selectedCourse.status === 'published' ? 'teacher' : 'student'}`}>{selectedCourse.status === 'published' ? 'Publié' : 'Brouillon'}</span>
              </div>
              <div className="user-row-actions">
                <button type="button" className="table-action" aria-label="Modifier le cours" title="Modifier le cours" onClick={() => beginCourseEdit(selectedCourse)}><Pencil size={16} /></button>
                <button type="button" className="secondary-button teacher-small-button" onClick={() => toggleCourseStatus(selectedCourse)}>{selectedCourse.status === 'published' ? 'Dépublier' : 'Publier'}</button>
                <button type="button" className="table-action danger" aria-label={`Supprimer le cours ${selectedCourse.title}`} title="Supprimer le cours" onClick={() => deleteCourse(selectedCourse)}><Trash2 size={17} /></button>
              </div>
            </div>

            <div className="teacher-content-columns">
              <section className="teacher-content-section">
                <div className="teacher-section-heading">
                  <h4><BookOpen size={17} /> Leçons <span>{selectedCourse.lessons?.length || 0}</span></h4>
                  <button type="button" className="secondary-button teacher-small-button" onClick={() => {
                    setEditingLesson(null)
                    setLessonForm({ ...emptyLesson, order: selectedCourse.lessons?.length || 0 })
                    setShowLessonForm((shown) => !shown)
                  }}><Plus size={15} /> Ajouter</button>
                </div>
                <div className="teacher-section-filters">
                  <label className="user-search"><Search size={15} /><input aria-label="Rechercher une leçon" placeholder="Rechercher une leçon" value={lessonSearch} onChange={(event) => { setLessonSearch(event.target.value); setLessonPage(1) }} /></label>
                  <select aria-label="Filtrer les leçons" value={lessonStatusFilter} onChange={(event) => { setLessonStatusFilter(event.target.value); setLessonPage(1) }}><option value="all">Tous les statuts</option><option value="draft">Brouillons</option><option value="published">Publiées</option></select>
                </div>

                {showLessonForm && (
                  <form className="teacher-inline-form" onSubmit={submitLesson}>
                    <label className="input-group"><span>Titre</span><input required value={lessonForm.title} onChange={(event) => setLessonForm({ ...lessonForm, title: event.target.value })} /></label>
                    <label className="input-group"><span>Résumé</span><input value={lessonForm.description} onChange={(event) => setLessonForm({ ...lessonForm, description: event.target.value })} /></label>
                    <label className="input-group"><span>Contenu</span><textarea required rows={4} value={lessonForm.content} onChange={(event) => setLessonForm({ ...lessonForm, content: event.target.value })} /></label>
                    <label className="input-group"><span>Ordre d’affichage</span><input type="number" min="0" value={lessonForm.order} onChange={(event) => setLessonForm({ ...lessonForm, order: event.target.value })} /></label>
                    <label className="teacher-checkbox"><input type="checkbox" checked={lessonForm.status === 'published'} onChange={(event) => setLessonForm({ ...lessonForm, status: event.target.checked ? 'published' : 'draft' })} /> Publier la leçon</label>
                    <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Enregistrement...' : editingLesson ? 'Enregistrer la leçon' : 'Ajouter la leçon'}</button>
                  </form>
                )}

                {visibleLessons.length ? (
                  <ul className="teacher-item-list">
                    {pageLessons.map((lesson) => (
                      <li key={lesson.id}>
                        <div><strong>{lesson.order + 1}. {lesson.title}</strong><p>{lesson.description || lesson.content.slice(0, 120)} · {lesson.status === 'published' ? 'Publiée' : 'Brouillon'}</p></div>
                        <div className="user-row-actions">
                          <button type="button" className="table-action" aria-label={`Modifier la leçon ${lesson.title}`} onClick={() => beginLessonEdit(lesson)}><Pencil size={15} /></button>
                          <button type="button" className="table-action" aria-label={lesson.status === 'published' ? 'Dépublier la leçon' : 'Publier la leçon'} onClick={async () => {
                            try {
                              await api.patch(`/lessons/${lesson.id}/`, { status: lesson.status === 'published' ? 'draft' : 'published' })
                              setNotice(lesson.status === 'published' ? 'Leçon dépubliée.' : 'Leçon publiée.')
                              await loadDashboard()
                            } catch (publishError) { setError(getErrorMessage(publishError)) }
                          }}>{lesson.status === 'published' ? <X size={15} /> : <Check size={15} />}</button>
                          <button type="button" className="table-action danger" aria-label={`Supprimer la leçon ${lesson.title}`} onClick={() => deleteLesson(lesson)}><Trash2 size={15} /></button>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : <p className="teacher-no-items">Aucune leçon ne correspond aux filtres.</p>}
                {visibleLessons.length > 0 && <Pagination page={safeLessonPage} pageSize={10} total={visibleLessons.length} onPageChange={setLessonPage} />}
              </section>

              <section className="teacher-content-section">
                <div className="teacher-section-heading">
                  <h4><FileText size={17} /> Documents <span>{selectedCourse.materials?.length || 0}</span></h4>
                  <button type="button" className="secondary-button teacher-small-button" onClick={() => setShowMaterialForm((shown) => !shown)}><Upload size={15} /> Ajouter</button>
                </div>
                <label className="user-search teacher-section-search"><Search size={15} /><input aria-label="Rechercher un document" placeholder="Rechercher un document" value={materialSearch} onChange={(event) => { setMaterialSearch(event.target.value); setMaterialPage(1) }} /></label>

                {showMaterialForm && (
                  <form className="teacher-inline-form" onSubmit={submitMaterial}>
                    <label className="input-group"><span>Titre</span><input required value={materialForm.title} onChange={(event) => setMaterialForm({ ...materialForm, title: event.target.value })} /></label>
                    <label className="input-group"><span>Description (facultatif)</span><input value={materialForm.description} onChange={(event) => setMaterialForm({ ...materialForm, description: event.target.value })} /></label>
                    <label className="input-group"><span>{editingMaterial ? 'Remplacer le fichier (facultatif)' : 'Fichier (20 Mo maximum)'}</span><input type="file" required={!editingMaterial} accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.png,.jpg,.jpeg" onChange={(event) => setMaterialForm({ ...materialForm, file: event.target.files?.[0] || null })} /></label>
                    <label className="input-group"><span>Associer à une leçon (facultatif)</span><select value={materialForm.lesson || ''} onChange={(event) => setMaterialForm({ ...materialForm, lesson: event.target.value })}><option value="">Aucune leçon (document du cours)</option>{selectedCourse.lessons?.map((lesson) => <option key={lesson.id} value={lesson.id}>{lesson.title}</option>)}</select></label>
                    <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Enregistrement...' : editingMaterial ? 'Enregistrer le document' : 'Téléverser le document'}</button>
                  </form>
                )}

                {visibleMaterials.length ? (
                  <ul className="teacher-item-list">
                    {pageMaterials.map((material) => (
                      <li key={material.id}>
                        <div className="teacher-material-info">
                          <FilePlus2 size={17} />
                          <div><strong>{material.title}</strong><p>{material.description || material.file_name} · {material.file_size ? `${(material.file_size / 1024 / 1024).toFixed(2)} Mo` : ''} · {new Date(material.uploaded_at).toLocaleDateString('fr-FR')}</p></div>
                        </div>
                        <div className="teacher-material-actions">
                          {material.file_url && <button type="button" className="student-link-button" onClick={() => openMaterial(material)}>Ouvrir / télécharger</button>}
                          <button type="button" className="table-action" aria-label={`Modifier le document ${material.title}`} onClick={() => beginMaterialEdit(material)}><Pencil size={15} /></button>
                          <button type="button" className="table-action danger" aria-label={`Supprimer le document ${material.title}`} onClick={() => deleteMaterial(material)}><Trash2 size={15} /></button>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : <p className="teacher-no-items">Aucun document ne correspond aux filtres.</p>}
                {visibleMaterials.length > 0 && <Pagination page={safeMaterialPage} pageSize={10} total={visibleMaterials.length} onPageChange={setMaterialPage} />}
              </section>
            </div>
          </>
        ) : null}
      </div>
    </section>
  )
}

import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Download, Search } from 'lucide-react'
import api from '../../services/api'
import { downloadPrivateFile } from '../../utils/download'
import Pagination from '../../components/Pagination'
import { useAutoRefresh } from '../../utils/dataSync'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Une erreur est survenue.'
}

function asList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

export default function StudentCourses() {
  const [courses, setCourses] = useState([])
  const [subjects, setSubjects] = useState([])
  const [completedLessons, setCompletedLessons] = useState(new Set())
  const [search, setSearch] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [sort, setSort] = useState('recent')
  const [openCourse, setOpenCourse] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [courseResponse, subjectResponse, progressResponse] = await Promise.all([
      api.get('/courses/'),
      api.get('/student/subjects/'),
      api.get('/student/progress/'),
      ])
      setCourses(asList(courseResponse.data))
      setSubjects(asList(subjectResponse.data))
      setCompletedLessons(new Set(asList(progressResponse.data).filter((item) => item.completed).map((item) => item.lesson)))
      setError('')
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])
  useAutoRefresh(loadData)

  const visibleCourses = useMemo(() => courses.filter((course) => {
    const matchesSubject = !subjectId || String(course.subject) === subjectId
    const query = search.trim().toLocaleLowerCase()
    const matchesSearch = !query || [course.title, course.description, course.subject_name, course.faculty_name, course.level_name]
      .some((value) => (value || '').toLocaleLowerCase().includes(query))
    return matchesSubject && matchesSearch
  }).sort((first, second) => sort === 'title'
    ? first.title.localeCompare(second.title, 'fr')
    : new Date(second.created_at) - new Date(first.created_at)), [courses, search, subjectId, sort])
  const visibleSubjects = useMemo(() => subjects.filter((subject) => {
    const query = search.trim().toLocaleLowerCase()
    return !query || [subject.code, subject.name, subject.faculty, subject.level, subject.academic_year]
      .some((value) => (value || '').toLocaleLowerCase().includes(query))
  }), [subjects, search])
  const safePage = Math.min(page, Math.max(1, Math.ceil(visibleCourses.length / 10)))
  const pageCourses = visibleCourses.slice((safePage - 1) * 10, safePage * 10)

  const toggleLesson = async (lesson) => {
    const completed = !completedLessons.has(lesson.id)
    setBusyId(lesson.id)
    setError('')
    try {
      await api.post(`/student/lessons/${lesson.id}/progress/`, { completed })
      setCompletedLessons((current) => {
        const next = new Set(current)
        if (completed) next.add(lesson.id)
        else next.delete(lesson.id)
        return next
      })
    } catch (saveError) {
      setError(messageFrom(saveError))
    } finally {
      setBusyId(null)
    }
  }

  const download = async (material) => {
    setError('')
    try {
      await downloadPrivateFile(material.file_url, material.file_name || material.title)
    } catch (downloadError) {
      setError(messageFrom(downloadError))
    }
  }

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading"><div><h2>Mes matières et cours</h2><p>Consultez uniquement les contenus publiés dans vos matières actives.</p></div></div>
      <div className="teacher-course-filters student-course-filters">
        <label className="student-search"><Search size={17} /><input aria-label="Rechercher une matière ou un cours" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Rechercher une matière ou un cours" /></label>
        <select aria-label="Filtrer par matière" value={subjectId} onChange={(event) => { setSubjectId(event.target.value); setPage(1) }}>
          <option value="">Toutes les matières</option>
          {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.code} — {subject.name}</option>)}
        </select>
        <select aria-label="Trier les cours" value={sort} onChange={(event) => { setSort(event.target.value); setPage(1) }}>
          <option value="recent">Plus récents</option>
          <option value="title">Titre (A–Z)</option>
        </select>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {!loading && visibleSubjects.length > 0 && (
        <section className="student-subject-section">
          <div className="teacher-panel-heading"><h3>Mes matières inscrites</h3></div>
          <div className="teacher-subject-grid">
            {visibleSubjects.map((subject) => (
              <article className="teacher-subject-card" key={subject.id}>
                <div className="teacher-subject-card-head"><span>{subject.code}</span><span>{subject.academic_year}</span></div>
                <h3>{subject.name}</h3>
                <p>{subject.description || 'Matière attribuée par l’administration.'}</p>
                <dl><div><dt>Filière</dt><dd>{subject.faculty}</dd></div><div><dt>Niveau</dt><dd>{subject.level}</dd></div></dl>
                <footer><span>{subject.course_count} cours publiés</span></footer>
              </article>
            ))}
          </div>
        </section>
      )}
      {loading ? <p className="teacher-empty">Chargement de vos cours...</p> : visibleCourses.length === 0 ? (
        <div className="teacher-empty"><strong>Aucun cours publié ne correspond à votre recherche.</strong></div>
      ) : (
        <>
        <div className="student-course-list">
          {pageCourses.map((course) => (
            <article className="teacher-form-card student-course-card" key={course.id}>
              <header className="student-course-heading">
                <div><span>{course.subject_name} · {course.subject_code || ''}</span><h3>{course.title}</h3><p>{course.faculty_name} · {course.level_name}</p></div>
                <button type="button" className="secondary-button" onClick={() => setOpenCourse(openCourse === course.id ? null : course.id)}>
                  {openCourse === course.id ? 'Masquer le contenu' : 'Voir le contenu'}
                </button>
              </header>
              {openCourse === course.id && (
                <div className="student-course-content">
                  <p>{course.description}</p>
                  {course.objectives && <p><strong>Objectifs pédagogiques :</strong> {course.objectives}</p>}
                  <h4>Annonces</h4>
                  {course.announcements?.length ? course.announcements.map((announcement) => (
                    <article className="student-assignment-card" key={announcement.id}>
                      <div className="student-assignment-heading"><h5>{announcement.title}</h5><small>{announcement.published_at ? new Date(announcement.published_at).toLocaleString('fr-FR') : ''}</small></div>
                      <p>{announcement.content}</p>
                    </article>
                  )) : <p>Aucune annonce publiée pour ce cours.</p>}
                  <h4>Leçons</h4>
                  {course.lessons?.length ? course.lessons.map((lesson) => (
                    <section className="student-lesson" key={lesson.id}>
                      <div className="student-lesson-title"><div><h5>{lesson.order ? `${lesson.order}. ` : ''}{lesson.title}</h5><p>{lesson.description}</p></div>
                        <button type="button" className="secondary-button" disabled={busyId === lesson.id} onClick={() => toggleLesson(lesson)}>
                          <CheckCircle2 size={16} /> {completedLessons.has(lesson.id) ? 'Terminée' : 'Marquer terminée'}
                        </button>
                      </div>
                      <div className="student-lesson-body">{lesson.content}</div>
                      {course.materials?.filter((material) => material.lesson === lesson.id).map((material) => (
                        <button type="button" className="student-document-button" key={material.id} onClick={() => download(material)}>
                          <Download size={15} /> {material.title} · {material.file_name} · {Math.ceil(material.file_size / 1024)} Ko
                        </button>
                      ))}
                    </section>
                  )) : <p className="teacher-no-items">Aucune leçon publiée pour ce cours.</p>}
                  <h4>Documents du cours</h4>
                  {course.materials?.filter((material) => !material.lesson).length ? course.materials.filter((material) => !material.lesson).map((material) => (
                    <button type="button" className="student-document-button" key={material.id} onClick={() => download(material)}>
                      <Download size={15} /> {material.title} · {material.file_name} · {Math.ceil(material.file_size / 1024)} Ko
                    </button>
                  )) : <p className="teacher-no-items">Aucun document de cours publié.</p>}
                </div>
              )}
            </article>
          ))}
        </div>
        <Pagination page={safePage} pageSize={10} total={visibleCourses.length} onPageChange={setPage} />
        </>
      )}
    </section>
  )
}

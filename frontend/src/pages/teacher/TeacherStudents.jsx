import { useCallback, useEffect, useMemo, useState } from 'react'
import { Search, Users } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { useAutoRefresh } from '../../utils/dataSync'
import UserAvatar from '../../components/UserAvatar'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Impossible de charger les étudiants.'
}

export default function TeacherStudents() {
  const [students, setStudents] = useState([])
  const [subjects, setSubjects] = useState([])
  const [search, setSearch] = useState('')
  const [subjectFilter, setSubjectFilter] = useState('')
  const [facultyFilter, setFacultyFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [subjectResponse, studentResponse] = await Promise.all([
        api.get('/teacher/subjects/'),
        api.get('/teacher/students/'),
      ])
      setSubjects(subjectResponse.data)
      setStudents(studentResponse.data)
      setError('')
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])
  useAutoRefresh(loadData)

  const faculties = useMemo(() => [...new Set(subjects.map((subject) => subject.faculty_name))], [subjects])
  const levels = useMemo(() => [...new Set(subjects.map((subject) => subject.level_name))], [subjects])

  const filteredStudents = useMemo(() => {
    const query = search.trim().toLowerCase()
    return students.filter((student) => {
      const matchesQuery = !query || `${student.first_name} ${student.last_name} ${student.email} ${student.matricule || ''}`.toLowerCase().includes(query)
      const matchesSubject = !subjectFilter || student.subjects.some((subject) => String(subject.id) === subjectFilter)
      const matchesFaculty = !facultyFilter || student.subjects.some((subject) => subject.faculty === facultyFilter)
      const matchesLevel = !levelFilter || student.subjects.some((subject) => subject.level === levelFilter)
      return matchesQuery && matchesSubject && matchesFaculty && matchesLevel
    })
  }, [students, search, subjectFilter, facultyFilter, levelFilter])
  const pageStudents = filteredStudents.slice((page - 1) * 10, page * 10)

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading"><div><h2>Étudiants inscrits</h2><p>Consultation en lecture seule des étudiants inscrits à vos matières.</p></div></div>
      {error && <div className="error-message" role="alert">{error}</div>}
      <div className="teacher-student-filters">
        <label className="user-search">
          <Search size={17} />
          <input aria-label="Rechercher un étudiant" placeholder="Nom, prénom, matricule ou e-mail" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
        </label>
        <select aria-label="Filtrer par matière" value={subjectFilter} onChange={(event) => { setSubjectFilter(event.target.value); setPage(1) }}>
          <option value="">Toutes les matières</option>
          {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.code} — {subject.name}</option>)}
        </select>
        <select aria-label="Filtrer par filière" value={facultyFilter} onChange={(event) => { setFacultyFilter(event.target.value); setPage(1) }}>
          <option value="">Toutes les filières</option>
          {faculties.map((faculty) => <option key={faculty} value={faculty}>{faculty}</option>)}
        </select>
        <select aria-label="Filtrer par niveau" value={levelFilter} onChange={(event) => { setLevelFilter(event.target.value); setPage(1) }}>
          <option value="">Tous les niveaux</option>
          {levels.map((level) => <option key={level} value={level}>{level}</option>)}
        </select>
      </div>
      <div className="user-table-card">
        {loading ? <p className="user-table-empty">Chargement...</p> : filteredStudents.length === 0 ? (
          <div className="teacher-empty"><Users size={28} /><strong>Aucun étudiant inscrit ne correspond aux filtres.</strong></div>
        ) : (
          <div className="user-table-scroll">
            <table className="user-table">
              <thead><tr><th>Étudiant</th><th>Matricule</th><th>Adresse e-mail</th><th>Matières suivies</th></tr></thead>
              <tbody>
                {pageStudents.map((student) => (
                  <tr key={student.id}>
                    <td data-label="Étudiant"><div className="user-identity"><UserAvatar src={student.avatar_url} name={`${student.first_name} ${student.last_name}`} /><strong>{student.first_name} {student.last_name}</strong></div></td>
                    <td data-label="Matricule">{student.matricule || '—'}</td>
                    <td data-label="Adresse e-mail">{student.email}</td>
                    <td data-label="Matières suivies">{student.subjects.map((subject) => subject.code).join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && filteredStudents.length > 0 && <Pagination page={page} pageSize={10} total={filteredStudents.length} onPageChange={setPage} />}
      </div>
    </section>
  )
}

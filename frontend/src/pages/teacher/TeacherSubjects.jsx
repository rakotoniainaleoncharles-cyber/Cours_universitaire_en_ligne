import { useCallback, useEffect, useMemo, useState } from 'react'
import { BookOpen, Search, Users } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { useAutoRefresh } from '../../utils/dataSync'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Impossible de charger les matières.'
}

export default function TeacherSubjects() {
  const [subjects, setSubjects] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadSubjects = useCallback(async () => {
    try {
      const { data } = await api.get('/teacher/subjects/')
      setSubjects(data)
      setError('')
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadSubjects() }, [loadSubjects])
  useAutoRefresh(loadSubjects)

  const filteredSubjects = useMemo(() => {
    const query = search.trim().toLowerCase()
    return subjects.filter((subject) => !query || [
      subject.code,
      subject.name,
      subject.faculty_name,
      subject.level_name,
      subject.academic_year_name,
    ].some((value) => value?.toLowerCase().includes(query)))
  }, [subjects, search])
  const safePage = Math.min(page, Math.max(1, Math.ceil(filteredSubjects.length / 10)))
  const pageSubjects = filteredSubjects.slice((safePage - 1) * 10, safePage * 10)

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading">
        <div><h2>Mes matières</h2><p>Attributions définies par l’administration. Elles ne peuvent pas être modifiées depuis cet espace.</p></div>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      <label className="user-search teacher-search">
        <Search size={17} />
        <input aria-label="Rechercher une matière" placeholder="Rechercher par matière, filière ou niveau" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
      </label>
      {loading ? <p className="teacher-empty">Chargement des matières...</p> : filteredSubjects.length === 0 ? (
        <div className="teacher-empty"><BookOpen size={28} /><strong>Aucune matière trouvée.</strong></div>
      ) : (
        <div className="teacher-subject-grid">
          {pageSubjects.map((subject) => (
            <article className="teacher-subject-card" key={subject.id}>
              <div className="teacher-subject-card-head">
                <span>{subject.code}</span>
                <BookOpen size={19} />
              </div>
              <h3>{subject.name}</h3>
              <p>{subject.description || 'Aucune description enregistrée.'}</p>
              <dl>
                <div><dt>Filière</dt><dd>{subject.faculty_name}</dd></div>
                <div><dt>Niveau</dt><dd>{subject.level_name}</dd></div>
                <div><dt>Année académique</dt><dd>{subject.academic_year_name}</dd></div>
              </dl>
              <footer>
                <span><BookOpen size={15} /> {subject.course_count} cours</span>
                <span><Users size={15} /> {subject.student_count} étudiants</span>
              </footer>
            </article>
          ))}
        </div>
      )}
      {!loading && filteredSubjects.length > 0 && <Pagination page={safePage} pageSize={10} total={filteredSubjects.length} onPageChange={setPage} />}
    </section>
  )
}

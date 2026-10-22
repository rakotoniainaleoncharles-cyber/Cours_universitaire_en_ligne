import { useCallback, useEffect, useMemo, useState } from 'react'
import { Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { useAutoRefresh } from '../../utils/dataSync'

const resourceConfig = {
  faculties: { title: 'Filières', endpoint: '/faculties/', fields: ['name', 'code', 'description'] },
  levels: { title: 'Niveaux universitaires', endpoint: '/levels/', fields: ['name', 'code', 'faculty'] },
  years: { title: 'Années académiques', endpoint: '/academic-years/', fields: ['name', 'start_date', 'end_date', 'is_active'] },
  subjects: { title: 'Matières', endpoint: '/subjects/', fields: ['code', 'name', 'description', 'faculty', 'level', 'academic_year', 'teacher'] },
  enrollments: { title: 'Inscriptions', endpoint: '/enrollments/', fields: ['student', 'subject', 'academic_year', 'status'] },
}

const lookupEndpoints = {
  faculties: '/faculties/',
  levels: '/levels/',
  years: '/academic-years/',
  subjects: '/subjects/',
  teachers: '/users/?role=teacher',
  students: '/users/?role=student',
  enrollments: '/enrollments/',
  courses: '/courses/',
}

const lookupKeysBySection = {
  faculties: ['levels', 'subjects', 'enrollments'],
  levels: ['faculties', 'subjects', 'enrollments'],
  years: ['enrollments'],
  subjects: ['faculties', 'levels', 'years', 'teachers', 'enrollments', 'courses'],
  enrollments: ['faculties', 'levels', 'years', 'subjects', 'students'],
}

const emptyLookups = {
  faculties: [], levels: [], years: [], subjects: [], teachers: [], students: [], enrollments: [], courses: [],
}

const fieldLabels = {
  name: 'Nom', code: 'Code', description: 'Description', start_date: 'Date de début',
  end_date: 'Date de fin', faculty: 'Filière', level: 'Niveau', academic_year: 'Année académique',
  teacher: 'Professeur', student: 'Étudiant', subject: 'Matière',
  is_active: 'Année active', status: 'Statut de l’inscription',
}

function errorMessage(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const message = Object.values(data).flat().find((value) => typeof value === 'string')
    if (message) return message
  }
  return 'Une erreur est survenue lors de l’opération.'
}

export default function AdminAcademicManagement({ section = 'faculties' }) {
  const config = resourceConfig[section] || resourceConfig.faculties
  const [rows, setRows] = useState([])
  const [lookups, setLookups] = useState(emptyLookups)
  const [form, setForm] = useState({})
  const [studentSearch, setStudentSearch] = useState('')
  const [editing, setEditing] = useState(null)
  const [formOpen, setFormOpen] = useState(false)
  const [studentPickerOpen, setStudentPickerOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [facultyFilter, setFacultyFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState('')
  const [yearFilter, setYearFilter] = useState('')
  const [teacherFilter, setTeacherFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const lookupKeys = lookupKeysBySection[section] || lookupKeysBySection.faculties
      const [response, ...lookupResponses] = await Promise.all([
        api.get(config.endpoint),
        ...lookupKeys.map((key) => api.get(lookupEndpoints[key])),
      ])
      setRows(response.data)
      setLookups({
        ...emptyLookups,
        ...Object.fromEntries(lookupKeys.map((key, index) => [key, lookupResponses[index].data])),
      })
    } catch (loadError) {
      setError(errorMessage(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [config.endpoint, section])

  useEffect(() => { loadData() }, [loadData])
  useAutoRefresh(() => loadData({ silent: true }))

  const openForm = (row = null) => {
    setEditing(row)
    const initial = Object.fromEntries(config.fields.map((field) => [field, row?.[field] ?? '']))
    const selectedStudent = lookups.students.find((student) => String(student.id) === String(row?.student))
    setStudentSearch(selectedStudent ? studentLabel(selectedStudent) : '')
    setStudentPickerOpen(false)
    if (!row && section === 'enrollments') initial.status = 'active'
    if (!row && section === 'years') initial.is_active = false
    setForm(initial)
    setError('')
    setNotice('')
    setFormOpen(true)
  }

  const save = async (event) => {
    event.preventDefault()
    if (section === 'enrollments' && !form.student) {
      setError('Recherchez puis sélectionnez un étudiant dans la liste proposée.')
      return
    }
    setSaving(true)
    setError('')
    setNotice('')
    const payload = { ...form }
    for (const key of ['faculty', 'level', 'academic_year', 'teacher', 'student', 'subject']) {
      if (key in payload && payload[key] === '') payload[key] = null
    }
    try {
      if (editing) {
        await api.patch(`${config.endpoint}${editing.id}/`, payload)
        setNotice('Les modifications ont été enregistrées.')
      } else {
        await api.post(config.endpoint, payload)
        setNotice('L’élément a été créé.')
      }
      setFormOpen(false)
      setEditing(null)
      await loadData()
    } catch (saveError) {
      setError(errorMessage(saveError))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (row) => {
    const displayName = row.name || row.code || `${row.student_name} — ${row.subject_code}`
    if (!window.confirm(`Supprimer « ${displayName} » ? Les éléments qui en dépendent peuvent empêcher cette suppression.`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`${config.endpoint}${row.id}/`)
      setNotice('L’élément a été supprimé.')
      await loadData()
    } catch (deleteError) {
      setError(errorMessage(deleteError))
    }
  }

  const filteredRows = useMemo(() => rows.filter((row) => {
    const query = search.trim().toLocaleLowerCase()
    const text = Object.values(row).filter((value) => typeof value === 'string').join(' ').toLocaleLowerCase()
    return (!query || text.includes(query))
      && (!facultyFilter || String(row.faculty ?? row.faculty_id) === facultyFilter)
      && (!levelFilter || String(row.level ?? row.level_id) === levelFilter)
      && (!yearFilter || String(row.academic_year_id ?? row.academic_year) === yearFilter)
      && (!teacherFilter || String(row.teacher ?? '') === teacherFilter)
      && (!statusFilter || row.status === statusFilter)
  }), [rows, search, facultyFilter, levelFilter, yearFilter, teacherFilter, statusFilter])
  const safePage = Math.min(page, Math.max(1, Math.ceil(filteredRows.length / 10)))
  const pageRows = filteredRows.slice((safePage - 1) * 10, safePage * 10)

  const selectOptions = {
    faculty: lookups.faculties.map((item) => [item.id, `${item.code} — ${item.name}`]),
    level: lookups.levels.map((item) => [item.id, `${item.code} — ${item.name}`]),
    academic_year: lookups.years.map((item) => [item.id, item.name]),
    teacher: lookups.teachers.map((item) => [item.id, `${item.first_name} ${item.last_name} (${item.email})`]),
    student: lookups.students.map((item) => [item.id, `${item.first_name} ${item.last_name} (${item.email})`]),
    subject: lookups.subjects.map((item) => [item.id, `${item.code} — ${item.name}`]),
    status: [['active', 'Active'], ['inactive', 'Inactive']],
  }
  function studentLabel(student) {
    const fullName = `${student.first_name} ${student.last_name}`.trim()
    return [fullName, student.matricule, student.email].filter(Boolean).join(' — ')
  }

  const matchingStudents = lookups.students.filter((student) => {
    const query = studentSearch.trim().toLocaleLowerCase()
    return !query || studentLabel(student).toLocaleLowerCase().includes(query)
  })

  const display = (row) => {
    if (section === 'faculties') return [
      row.code, row.name, row.description,
      lookups.levels.filter((item) => item.faculty === row.id).length,
      lookups.subjects.filter((item) => item.faculty === row.id).length,
      new Set(lookups.enrollments.filter((item) => item.faculty_id === row.id).map((item) => item.student)).size,
      new Set(lookups.subjects.filter((item) => item.faculty === row.id && item.teacher).map((item) => item.teacher)).size,
    ]
    if (section === 'levels') return [
      row.code, row.name, lookups.faculties.find((item) => item.id === row.faculty)?.name || 'Non rattaché',
      lookups.subjects.filter((item) => item.level === row.id).length,
      new Set(lookups.enrollments.filter((item) => item.level_id === row.id).map((item) => item.student)).size,
    ]
    if (section === 'years') return [
      row.name, row.start_date, row.end_date, row.is_active ? 'Active' : 'Inactive',
      lookups.enrollments.filter((item) => item.academic_year === row.id).length,
    ]
    if (section === 'subjects') return [
      row.code, row.name, row.faculty_name, row.level_name, row.academic_year_name,
      row.teacher_name || 'Non attribué',
      lookups.courses.filter((item) => item.subject === row.id).length,
      lookups.enrollments.filter((item) => item.subject === row.id).length,
    ]
    return [row.student_name, row.student_matricule || '—', row.student_email, `${row.subject_code} — ${row.subject_name}`, row.faculty_name, row.level_name, row.academic_year_name, row.status === 'active' ? 'Active' : 'Inactive']
  }
  const columns = section === 'faculties' ? ['Code', 'Filière', 'Description', 'Niveaux', 'Matières', 'Étudiants inscrits', 'Professeurs affectés']
    : section === 'levels' ? ['Code', 'Niveau', 'Filière', 'Matières', 'Étudiants']
      : section === 'years' ? ['Année académique', 'Début', 'Fin', 'Statut', 'Inscriptions']
        : section === 'subjects' ? ['Code', 'Matière', 'Filière', 'Niveau', 'Année', 'Professeur', 'Cours', 'Inscriptions']
          : ['Étudiant', 'Matricule', 'E-mail', 'Matière', 'Filière', 'Niveau', 'Année', 'Statut']

  return (
    <section className="user-management">
      <div className="user-management-heading">
        <div><h2>Gestion : {config.title}</h2><p>Administrer la structure académique et les inscriptions.</p></div>
        {section !== 'enrollments' && <button type="button" className="primary-button user-add-button" onClick={() => openForm()}><Plus size={17} /> Ajouter</button>}
        {section === 'enrollments' && <button type="button" className="primary-button user-add-button" onClick={() => openForm()}><Plus size={17} /> Inscrire un étudiant</button>}
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}

      {formOpen && (
        <form className="user-form-card" onSubmit={save}>
          <div className="user-form-heading"><div><h3>{editing ? 'Modifier' : 'Ajouter'} : {config.title}</h3></div><button type="button" className="icon-button" onClick={() => setFormOpen(false)} aria-label="Fermer"><X size={18} /></button></div>
          <div className="user-form-grid">
            {config.fields.map((field) => {
              if (field === 'student') return (
                <label className="input-group" key={field}>
                  <span>{fieldLabels[field]}</span>
                  <div className="student-picker">
                    <input
                      type="search"
                      autoComplete="off"
                      required
                      aria-label="Rechercher un étudiant par nom, matricule ou e-mail"
                      aria-expanded={studentPickerOpen}
                      aria-controls="admin-student-options"
                      placeholder="Saisir un nom, matricule ou e-mail"
                      value={studentSearch}
                      onFocus={() => setStudentPickerOpen(true)}
                      onChange={(event) => {
                        setStudentSearch(event.target.value)
                        setStudentPickerOpen(true)
                        setForm((current) => ({ ...current, student: '' }))
                      }}
                    />
                    {studentPickerOpen && (
                      <div className="student-picker-options" id="admin-student-options" role="listbox">
                        {matchingStudents.length ? matchingStudents.slice(0, 20).map((student) => (
                          <button
                            type="button"
                            role="option"
                            aria-selected={String(form.student) === String(student.id)}
                            key={student.id}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => {
                              setStudentSearch(studentLabel(student))
                              setForm((current) => ({ ...current, student: String(student.id) }))
                              setStudentPickerOpen(false)
                            }}
                          >
                            <strong>{student.first_name} {student.last_name}</strong>
                            <span>{[student.matricule, student.email].filter(Boolean).join(' · ')}</span>
                          </button>
                        )) : <p>Aucun étudiant correspondant.</p>}
                      </div>
                    )}
                  </div>
                  <small>{form.student ? 'Étudiant sélectionné.' : 'Choisissez un résultat proposé pour valider la sélection.'}</small>
                </label>
              )
              const options = selectOptions[field]
              if (options) return (
                <label className="input-group" key={field}><span>{fieldLabels[field]}</span>
                  <select required={field !== 'teacher'} value={form[field] ?? ''} onChange={(event) => setForm({ ...form, [field]: event.target.value })}>
                    <option value="">{field === 'teacher' ? 'Non attribué' : 'Choisir...'}</option>
                    {options.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                  </select>
                  {section === 'subjects' && field === 'teacher' && <small>Attribuez le professeur responsable pour lui permettre de créer un cours associé à cette matière.</small>}
                </label>
              )
              return (
                <label className={`input-group ${field === 'description' ? 'user-password-field' : ''}`} key={field}><span>{fieldLabels[field]}</span>
                  {field === 'description'
                    ? <textarea rows={3} value={form[field] ?? ''} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />
                    : field === 'is_active'
                      ? <input type="checkbox" checked={Boolean(form[field])} onChange={(event) => setForm({ ...form, [field]: event.target.checked })} />
                    : <input required type={field.includes('_date') ? 'date' : 'text'} value={form[field] ?? ''} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />}
                </label>
              )
            })}
          </div>
          <div className="user-form-actions"><button type="button" className="secondary-button" onClick={() => setFormOpen(false)}>Annuler</button><button type="submit" className="primary-button" disabled={saving}>{saving ? 'Enregistrement...' : editing ? 'Enregistrer' : 'Créer'}</button></div>
        </form>
      )}

      <div className="user-table-card">
        <div className="user-table-toolbar">
          <label className="user-search"><Search size={17} /><input aria-label={`Rechercher dans ${config.title}`} placeholder="Rechercher" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} /></label>
          {(section === 'subjects' || section === 'enrollments') && <select aria-label="Filtrer par filière" value={facultyFilter} onChange={(event) => { setFacultyFilter(event.target.value); setPage(1) }}><option value="">Toutes les filières</option>{lookups.faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
          {(section === 'subjects' || section === 'enrollments') && <select aria-label="Filtrer par niveau" value={levelFilter} onChange={(event) => { setLevelFilter(event.target.value); setPage(1) }}><option value="">Tous les niveaux</option>{lookups.levels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
          {(section === 'subjects' || section === 'enrollments') && <select aria-label="Filtrer par année académique" value={yearFilter} onChange={(event) => { setYearFilter(event.target.value); setPage(1) }}><option value="">Toutes les années</option>{lookups.years.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
          {section === 'subjects' && <select aria-label="Filtrer par professeur" value={teacherFilter} onChange={(event) => { setTeacherFilter(event.target.value); setPage(1) }}><option value="">Tous les professeurs</option>{lookups.teachers.map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name}</option>)}</select>}
          {section === 'enrollments' && <select aria-label="Filtrer par statut" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1) }}><option value="">Tous les statuts</option><option value="active">Actives</option><option value="inactive">Inactives</option></select>}
        </div>
        {loading ? <p className="user-table-empty">Chargement...</p> : filteredRows.length === 0 ? <p className="user-table-empty">Aucun résultat.</p> : (
          <div className="user-table-scroll"><table className="user-table"><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}<th>Actions</th></tr></thead>
            <tbody>{pageRows.map((row) => <tr key={row.id}>{display(row).map((value, index) => <td data-label={columns[index]} key={`${row.id}-${index}`}>{value || '—'}</td>)}<td data-label="Actions"><div className="user-row-actions"><button type="button" className="table-action" aria-label="Modifier" onClick={() => openForm(row)}><Pencil size={15} /></button><button type="button" className="table-action danger" aria-label="Supprimer" onClick={() => remove(row)}><Trash2 size={15} /></button></div></td></tr>)}</tbody>
          </table></div>
        )}
        {!loading && filteredRows.length > 0 && <Pagination page={safePage} pageSize={10} total={filteredRows.length} onPageChange={setPage} />}
      </div>
    </section>
  )
}

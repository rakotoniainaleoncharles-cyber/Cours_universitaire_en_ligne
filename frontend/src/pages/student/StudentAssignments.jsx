import { useCallback, useEffect, useState } from 'react'
import { ClipboardCheck, Download, FileText, Upload, X } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { downloadPrivateFile, fetchPrivateFile } from '../../utils/download'
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

export default function StudentAssignments() {
  const [assignments, setAssignments] = useState([])
  const [submissions, setSubmissions] = useState({})
  const [files, setFiles] = useState({})
  const [referencePreview, setReferencePreview] = useState(null)
  const [comments, setComments] = useState({})
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('due')

  const loadAssignments = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/assignments/')
      const assignmentList = Array.isArray(data) ? data : data.results || []
      setAssignments(assignmentList)
      const submissionResponses = await Promise.all(
        assignmentList.map((assignment) => api.get(`/assignments/${assignment.id}/submissions/`)),
      )
      const nextSubmissions = {}
      submissionResponses.forEach((response, index) => {
        nextSubmissions[assignmentList[index].id] = response.data[0] || null
      })
      setSubmissions(nextSubmissions)
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAssignments()
  }, [loadAssignments])
  useAutoRefresh(() => loadAssignments({ silent: true }))
  useEffect(() => () => {
    if (referencePreview?.url) URL.revokeObjectURL(referencePreview.url)
  }, [referencePreview?.url])
  const filteredAssignments = assignments.filter((assignment) =>
    `${assignment.title} ${assignment.course_title} ${assignment.instructions}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()),
  ).sort((first, second) => {
    if (sort === 'title') return first.title.localeCompare(second.title, 'fr')
    if (!first.due_at) return 1
    if (!second.due_at) return -1
    return new Date(first.due_at) - new Date(second.due_at)
  })
  const safePage = Math.min(page, Math.max(1, Math.ceil(filteredAssignments.length / 10)))
  const pageAssignments = filteredAssignments.slice((safePage - 1) * 10, safePage * 10)

  const submitAssignment = async (assignment) => {
    const file = files[assignment.id]
    if (!file) {
      setError('Choisissez un fichier avant de remettre le devoir.')
      return
    }
    setSavingId(assignment.id)
    setError('')
    setNotice('')
    try {
      const data = new FormData()
      data.append('file', file)
      data.append('comment', comments[assignment.id] || '')
      await api.post(`/assignments/${assignment.id}/submissions/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setFiles((current) => ({ ...current, [assignment.id]: null }))
      setNotice(`Votre remise pour « ${assignment.title} » a été enregistrée.`)
      await loadAssignments()
    } catch (submitError) {
      setError(messageFrom(submitError))
    } finally {
      setSavingId(null)
    }
  }

  const download = async (url, name) => {
    setError('')
    try {
      await downloadPrivateFile(url, name)
    } catch (downloadError) {
      setError(messageFrom(downloadError))
    }
  }

  const openReference = async (assignment) => {
    setError('')
    setReferencePreview({ name: assignment.reference_file_name || `${assignment.title}-reference`, loading: true })
    try {
      const file = await fetchPrivateFile(assignment.reference_file_url)
      setReferencePreview({
        name: assignment.reference_file_name || `${assignment.title}-reference`,
        type: file.type,
        url: URL.createObjectURL(file),
      })
    } catch (fileError) {
      setReferencePreview(null)
      setError(messageFrom(fileError))
    }
  }

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading"><div><h2>Mes devoirs</h2><p>Consultez les consignes et remettez vos travaux avant la date limite.</p></div></div>
      {referencePreview && (
        <div className="private-file-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setReferencePreview(null)
        }}>
          <section className="private-file-dialog" role="dialog" aria-modal="true" aria-label={`Aperçu : ${referencePreview.name}`}>
            <header className="private-file-header">
              <div><FileText size={19} /><strong>{referencePreview.name}</strong></div>
              <div>
                {!referencePreview.loading && <a className="secondary-button private-file-download" href={referencePreview.url} download={referencePreview.name}><Download size={16} /> Télécharger</a>}
                <button type="button" className="icon-button" aria-label="Fermer l’aperçu" onClick={() => setReferencePreview(null)}><X size={18} /></button>
              </div>
            </header>
            <div className="private-file-preview">
              {referencePreview.loading ? <p className="teacher-empty">Chargement du fichier...</p>
                : referencePreview.type?.startsWith('image/') ? <img src={referencePreview.url} alt={referencePreview.name} />
                  : referencePreview.type === 'application/pdf' ? <iframe title={`Aperçu de ${referencePreview.name}`} src={referencePreview.url} />
                    : <div className="private-file-unavailable"><FileText size={28} /><strong>Aperçu indisponible dans le navigateur.</strong><span>Téléchargez le fichier pour l’ouvrir avec une application compatible.</span></div>}
            </div>
          </section>
        </div>
      )}
      <div className="teacher-course-filters student-course-filters">
        <input className="teacher-search" aria-label="Rechercher un devoir" placeholder="Rechercher un devoir" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
        <select aria-label="Trier les devoirs" value={sort} onChange={(event) => { setSort(event.target.value); setPage(1) }}>
          <option value="due">Date limite</option>
          <option value="title">Titre (A–Z)</option>
        </select>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      {loading ? <p className="teacher-empty">Chargement des devoirs...</p> : assignments.length === 0 ? (
        <div className="teacher-empty"><ClipboardCheck size={28} /><strong>Aucun devoir publié pour vos matières.</strong></div>
      ) : filteredAssignments.length === 0 ? (
        <div className="teacher-empty"><strong>Aucun devoir ne correspond à votre recherche.</strong></div>
      ) : (
        <>
        <div className="student-assignment-list student-assignment-grid">
          {pageAssignments.map((assignment) => {
            const submission = submissions[assignment.id]
            const expired = assignment.due_at && new Date(assignment.due_at) < new Date()
            const graded = Boolean(submission?.is_graded)
            return (
              <article className="student-assignment-card" key={assignment.id}>
                <div className="student-assignment-heading">
                  <div><span>{assignment.course_title || 'Devoir'}</span><h3>{assignment.title}</h3></div>
                  <span className={`role-badge ${graded ? 'role-teacher' : 'role-student'}`}>{graded ? 'Corrigé' : submission ? 'Remis' : 'À faire'}</span>
                </div>
                <p className="student-assignment-instructions">{assignment.instructions}</p>
                <p className="student-assignment-due">Date limite : {assignment.due_at ? new Date(assignment.due_at).toLocaleString('fr-FR') : 'Aucune date limite'}</p>
                {assignment.reference_file_url && (
                  <div className="student-reference-actions">
                    <button type="button" className="student-reference-link student-link-button" onClick={() => openReference(assignment)}><FileText size={15} /> Ouvrir le document</button>
                    <button type="button" className="student-reference-link student-link-button" onClick={() => download(assignment.reference_file_url, assignment.reference_file_name || `${assignment.title}-reference`)}><Download size={15} /> Télécharger</button>
                  </div>
                )}
                {submission && (
                  <div className="student-submission-result">
                    <p>Remis le {new Date(submission.submitted_at).toLocaleString('fr-FR')} · <button type="button" className="student-inline-link student-link-button" onClick={() => download(submission.file_url, `${assignment.title}-remise`)}>Télécharger ma remise</button></p>
                    {submission.grade !== null && submission.grade !== undefined && <strong>Note : {submission.grade} / 20</strong>}
                    {submission.feedback && <p>Commentaire du professeur : {submission.feedback}</p>}
                  </div>
                )}
                {!graded && !expired && (
                  <div className="student-submit-form">
                    <label className="input-group"><span>{submission ? 'Remplacer le fichier remis' : 'Fichier à remettre (20 Mo maximum)'}</span>
                      <input type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.png,.jpg,.jpeg" onChange={(event) => setFiles((current) => ({ ...current, [assignment.id]: event.target.files?.[0] || null }))} />
                    </label>
                    <label className="input-group"><span>Commentaire (facultatif)</span>
                      <textarea rows={2} value={comments[assignment.id] ?? submission?.comment ?? ''} onChange={(event) => setComments((current) => ({ ...current, [assignment.id]: event.target.value }))} />
                    </label>
                    <button type="button" className="primary-button" disabled={savingId === assignment.id} onClick={() => submitAssignment(assignment)}>
                      <Upload size={16} /> {savingId === assignment.id ? 'Envoi...' : submission ? 'Mettre à jour ma remise' : 'Remettre le devoir'}
                    </button>
                  </div>
                )}
                {expired && !graded && <p className="teacher-hint">La date limite est dépassée.</p>}
                {graded && <p className="teacher-hint">Ce devoir a été corrigé et ne peut plus être modifié.</p>}
              </article>
            )
          })}
        </div>
        <Pagination page={safePage} pageSize={10} total={filteredAssignments.length} onPageChange={setPage} />
        </>
      )}
    </section>
  )
}

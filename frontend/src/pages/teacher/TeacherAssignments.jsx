import { useCallback, useEffect, useState } from 'react'
import { Check, ClipboardCheck, Download, Eye, FileText, Pencil, Plus, Trash2, X } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { downloadPrivateFile, fetchPrivateFile } from '../../utils/download'
import { useAutoRefresh } from '../../utils/dataSync'

const initialForm = { course: '', title: '', instructions: '', due_at: '', is_published: false, reference_file: null }

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Une erreur est survenue. Vérifiez la connexion et les informations saisies.'
}

export default function TeacherAssignments() {
  const [courses, setCourses] = useState([])
  const [assignments, setAssignments] = useState([])
  const [selectedAssignmentId, setSelectedAssignmentId] = useState('')
  const [submissions, setSubmissions] = useState([])
  const [previewFile, setPreviewFile] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [form, setForm] = useState(initialForm)
  const [editing, setEditing] = useState(null)
  const [filter, setFilter] = useState('all')
  const [assignmentPage, setAssignmentPage] = useState(1)
  const [submissionPage, setSubmissionPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [gradingId, setGradingId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const [courseResponse, assignmentResponse] = await Promise.all([
        api.get('/courses/'),
        api.get('/assignments/'),
      ])
      setCourses(courseResponse.data)
      setAssignments(assignmentResponse.data)
      setSelectedAssignmentId((current) => (
        assignmentResponse.data.some((item) => String(item.id) === String(current))
          ? current
          : String(assignmentResponse.data[0]?.id || '')
      ))
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  const loadSubmissions = useCallback(async (assignmentId) => {
    if (!assignmentId) {
      setSubmissions([])
      return
    }
    try {
      const { data } = await api.get(`/assignments/${assignmentId}/submissions/`)
      setSubmissions(data)
    } catch (loadError) {
      setError(messageFrom(loadError))
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])
  useAutoRefresh(async () => {
    await loadData({ silent: true })
    if (selectedAssignmentId) await loadSubmissions(selectedAssignmentId)
  })

  useEffect(() => {
    loadSubmissions(selectedAssignmentId)
  }, [selectedAssignmentId, loadSubmissions])

  useEffect(() => () => {
    if (previewFile?.url) URL.revokeObjectURL(previewFile.url)
  }, [previewFile?.url])

  const filteredAssignments = assignments.filter((assignment) => (
    filter === 'all' || (filter === 'published' ? assignment.is_published : !assignment.is_published)
  ))
  const safeAssignmentPage = Math.min(assignmentPage, Math.max(1, Math.ceil(filteredAssignments.length / 10)))
  const pageAssignments = filteredAssignments.slice((safeAssignmentPage - 1) * 10, safeAssignmentPage * 10)
  const safeSubmissionPage = Math.min(submissionPage, Math.max(1, Math.ceil(submissions.length / 10)))
  const pageSubmissions = submissions.slice((safeSubmissionPage - 1) * 10, safeSubmissionPage * 10)
  const selectedAssignment = assignments.find((assignment) => String(assignment.id) === String(selectedAssignmentId))

  const openCreateForm = () => {
    setEditing(null)
    setForm({ ...initialForm, course: String(courses[0]?.id || '') })
    setError('')
    setNotice('')
    setShowForm(true)
  }

  const openEditForm = (assignment) => {
    setEditing(assignment)
    setForm({
      course: String(assignment.course),
      title: assignment.title,
      instructions: assignment.instructions,
      due_at: assignment.due_at ? new Date(assignment.due_at).toISOString().slice(0, 16) : '',
      is_published: assignment.is_published,
      reference_file: null,
    })
    setError('')
    setNotice('')
    setShowForm(true)
  }

  const saveAssignment = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const payload = new FormData()
      payload.append('course', form.course)
      payload.append('title', form.title)
      payload.append('instructions', form.instructions)
      payload.append('is_published', String(form.is_published))
      if (form.due_at) payload.append('due_at', new Date(form.due_at).toISOString())
      if (form.reference_file) payload.append('reference_file', form.reference_file)
      if (editing) {
        await api.patch(`/assignments/${editing.id}/`, payload, { headers: { 'Content-Type': 'multipart/form-data' } })
        setNotice('Le devoir a été modifié.')
      } else {
        await api.post('/assignments/', payload, { headers: { 'Content-Type': 'multipart/form-data' } })
        setNotice('Le devoir a été créé.')
      }
      setShowForm(false)
      setForm(initialForm)
      setEditing(null)
      await loadData()
    } catch (saveError) {
      setError(messageFrom(saveError))
    } finally {
      setSaving(false)
    }
  }

  const togglePublished = async (assignment) => {
    setError('')
    setNotice('')
    try {
      const { data } = await api.patch(`/assignments/${assignment.id}/`, { is_published: !assignment.is_published })
      setNotice(data.is_published ? 'Le devoir est publié.' : 'Le devoir est enregistré comme brouillon.')
      await loadData()
    } catch (updateError) {
      setError(messageFrom(updateError))
    }
  }

  const deleteAssignment = async (assignment) => {
    if (!window.confirm(`Supprimer le devoir « ${assignment.title} » et ses remises ?`)) return
    setError('')
    try {
      await api.delete(`/assignments/${assignment.id}/`)
      setNotice('Le devoir a été supprimé.')
      await loadData()
    } catch (deleteError) {
      setError(messageFrom(deleteError))
    }
  }

  const gradeSubmission = async (submission, event) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    setError('')
    setGradingId(submission.id)
    try {
      await api.patch(`/submissions/${submission.id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setNotice(`La remise de ${submission.student_name} a été corrigée.`)
      await loadSubmissions(selectedAssignmentId)
      await loadData()
    } catch (gradeError) {
      setError(messageFrom(gradeError))
    } finally {
      setGradingId(null)
    }
  }

  const viewSubmissionFile = async (submission) => {
    setError('')
    setPreviewLoading(true)
    setPreviewFile({ name: submission.file_name || 'Fichier remis', loading: true })
    try {
      const blob = await fetchPrivateFile(submission.file_url)
      setPreviewFile({
        name: submission.file_name || 'Fichier remis',
        type: blob.type,
        url: URL.createObjectURL(blob),
      })
    } catch (fileError) {
      setPreviewFile(null)
      setError(messageFrom(fileError))
    } finally {
      setPreviewLoading(false)
    }
  }

  const downloadSubmissionFile = async (submission) => {
    setError('')
    try {
      await downloadPrivateFile(submission.file_url, submission.file_name || `${submission.student_name}-remise`)
    } catch (fileError) {
      setError(messageFrom(fileError))
    }
  }

  const downloadCorrectedFile = async (submission) => {
    setError('')
    try {
      await downloadPrivateFile(submission.corrected_file_url, submission.corrected_file_name)
    } catch (fileError) {
      setError(messageFrom(fileError))
    }
  }

  const downloadReferenceFile = async (assignment) => {
    setError('')
    try {
      await downloadPrivateFile(assignment.reference_file_url, `${assignment.title}-reference`)
    } catch (fileError) {
      setError(messageFrom(fileError))
    }
  }

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading">
        <div><h2>Exercices et devoirs</h2><p>Créez des devoirs, suivez les remises et corrigez les travaux.</p></div>
        <button type="button" className="primary-button teacher-add-course" onClick={openCreateForm} disabled={courses.length === 0}><Plus size={17} /> Nouveau devoir</button>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      {previewFile && (
        <div className="private-file-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setPreviewFile(null)
        }}>
          <section className="private-file-dialog" role="dialog" aria-modal="true" aria-label={`Aperçu : ${previewFile.name}`}>
            <header className="private-file-header">
              <div><FileText size={19} /><strong>{previewFile.name}</strong></div>
              <div>
                {!previewFile.loading && <a className="secondary-button private-file-download" href={previewFile.url} download={previewFile.name}><Download size={16} /> Télécharger</a>}
                <button type="button" className="icon-button" aria-label="Fermer l’aperçu" onClick={() => setPreviewFile(null)}><X size={18} /></button>
              </div>
            </header>
            <div className="private-file-preview">
              {previewLoading || previewFile.loading ? <p className="teacher-empty">Chargement du fichier...</p>
                : previewFile.type?.startsWith('image/') ? <img src={previewFile.url} alt={previewFile.name} />
                  : previewFile.type === 'application/pdf' ? <iframe title={`Aperçu de ${previewFile.name}`} src={previewFile.url} />
                    : <div className="private-file-unavailable"><FileText size={28} /><strong>Aperçu indisponible dans le navigateur.</strong><span>Ce format peut être téléchargé et ouvert avec une application compatible.</span></div>}
            </div>
          </section>
        </div>
      )}
      {courses.length === 0 && !loading && <p className="teacher-hint">Créez d’abord un cours avant d’ajouter un devoir.</p>}

      {showForm && (
        <form className="teacher-form-card" onSubmit={saveAssignment}>
          <div className="teacher-form-heading">
            <div><h3>{editing ? 'Modifier le devoir' : 'Créer un devoir'}</h3><p>Un devoir publié est accessible aux étudiants inscrits à la matière.</p></div>
            <button type="button" className="icon-button" aria-label="Fermer le formulaire" onClick={() => setShowForm(false)}><X size={18} /></button>
          </div>
          <div className="teacher-form-grid">
            <label className="input-group"><span>Cours</span>
              <select required value={form.course} onChange={(event) => setForm({ ...form, course: event.target.value })}>
                {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
              </select>
            </label>
            <label className="input-group"><span>Titre</span><input required maxLength={200} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
            <label className="input-group"><span>Date limite (facultative)</span><input type="datetime-local" value={form.due_at} onChange={(event) => setForm({ ...form, due_at: event.target.value })} /></label>
            <label className="input-group"><span>Document de référence (facultatif)</span><input type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.png,.jpg,.jpeg" onChange={(event) => setForm({ ...form, reference_file: event.target.files?.[0] || null })} /></label>
            <label className="input-group teacher-wide-field"><span>Consignes</span><textarea required rows={5} value={form.instructions} onChange={(event) => setForm({ ...form, instructions: event.target.value })} /></label>
            <label className="teacher-checkbox"><input type="checkbox" checked={form.is_published} onChange={(event) => setForm({ ...form, is_published: event.target.checked })} /> Publier immédiatement</label>
          </div>
          {editing?.reference_file_url && !form.reference_file && <button type="button" className="student-inline-link student-link-button" onClick={() => downloadReferenceFile(editing)}>Télécharger le document de référence actuel</button>}
          <div className="teacher-form-actions">
            <button type="button" className="secondary-button" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Enregistrement...' : editing ? 'Enregistrer' : 'Créer le devoir'}</button>
          </div>
        </form>
      )}

      <div className="teacher-content-columns">
        <section className="teacher-course-panel">
          <div className="teacher-panel-heading">
            <div><h3><ClipboardCheck size={19} /> Liste des devoirs</h3></div>
            <select aria-label="Filtrer les devoirs" value={filter} onChange={(event) => { setFilter(event.target.value); setAssignmentPage(1) }}>
              <option value="all">Tous</option><option value="published">Publiés</option><option value="draft">Brouillons</option>
            </select>
          </div>
          {loading ? <p className="teacher-empty">Chargement...</p> : filteredAssignments.length === 0 ? <p className="teacher-no-items">Aucun devoir.</p> : (
            <ul className="teacher-item-list">
              {pageAssignments.map((assignment) => (
                <li key={assignment.id} className={`assignment-list-item ${String(assignment.id) === String(selectedAssignmentId) ? 'selected' : ''}`}>
                  <button type="button" className="assignment-select" onClick={() => { setSelectedAssignmentId(String(assignment.id)); setSubmissionPage(1) }}>
                    <strong>{assignment.title}</strong>
                    <small>{courses.find((course) => course.id === assignment.course)?.title || 'Cours'} · {assignment.is_published ? 'Publié' : 'Brouillon'}</small>
                    <small>{assignment.pending_count} remise(s) à corriger</small>
                  </button>
                  <div className="user-row-actions">
                    <button type="button" className="table-action" aria-label="Modifier le devoir" onClick={() => openEditForm(assignment)}><Pencil size={15} /></button>
                    <button type="button" className="table-action" aria-label={assignment.is_published ? 'Dépublier' : 'Publier'} title={assignment.is_published ? 'Dépublier' : 'Publier'} onClick={() => togglePublished(assignment)}>{assignment.is_published ? <X size={15} /> : <Check size={15} />}</button>
                    <button type="button" className="table-action danger" aria-label="Supprimer le devoir" onClick={() => deleteAssignment(assignment)}><Trash2 size={15} /></button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {!loading && filteredAssignments.length > 0 && <Pagination page={safeAssignmentPage} pageSize={10} total={filteredAssignments.length} onPageChange={setAssignmentPage} />}
        </section>

        <section className="teacher-course-panel">
          <div className="teacher-panel-heading"><div><h3>Remises à corriger</h3><p>{selectedAssignment?.title || 'Sélectionnez un devoir'}</p></div></div>
          {!selectedAssignmentId ? <p className="teacher-no-items">Aucun devoir sélectionné.</p> : submissions.length === 0 ? (
            <p className="teacher-no-items">Aucune remise reçue pour ce devoir.</p>
          ) : (
            <ul className="teacher-submission-list">
              {pageSubmissions.map((submission) => (
                <li key={submission.id}>
                  <div className="submission-heading">
                    <div><strong>{submission.student_name}</strong><small>{submission.student_email} · {new Date(submission.submitted_at).toLocaleString('fr-FR')}</small></div>
                    <div className="submission-file-actions">
                      <button type="button" className="secondary-button teacher-small-button" onClick={() => viewSubmissionFile(submission)}><Eye size={15} /> Voir le fichier</button>
                      <button type="button" className="secondary-button teacher-small-button" onClick={() => downloadSubmissionFile(submission)}><Download size={15} /> Télécharger</button>
                      {submission.corrected_file_url && <button type="button" className="secondary-button teacher-small-button" onClick={() => downloadCorrectedFile(submission)}><Download size={15} /> Fichier corrigé</button>}
                    </div>
                  </div>
                  {submission.comment && <p className="submission-comment">{submission.comment}</p>}
                  <form className="teacher-grade-form" onSubmit={(event) => gradeSubmission(submission, event)}>
                    <label className="input-group"><span>Note / 20</span><input name="grade" type="number" min="0" max="20" step="0.25" defaultValue={submission.grade ?? ''} /></label>
                    <label className="input-group"><span>Commentaire</span><textarea name="feedback" rows={2} defaultValue={submission.feedback} /></label>
                    <label className="input-group"><span>Fichier corrigé ou annoté (facultatif, 20 Mo maximum)</span><input name="corrected_file" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.png,.jpg,.jpeg" /></label>
                    <button type="submit" className="primary-button" disabled={gradingId === submission.id}>{gradingId === submission.id ? 'Enregistrement...' : 'Enregistrer la correction'}</button>
                  </form>
                </li>
              ))}
            </ul>
          )}
          {submissions.length > 0 && <Pagination page={safeSubmissionPage} pageSize={10} total={submissions.length} onPageChange={setSubmissionPage} />}
        </section>
      </div>
    </section>
  )
}

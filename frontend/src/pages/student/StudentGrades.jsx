import { useCallback, useEffect, useState } from 'react'
import { Award, ClipboardCheck, Download, Eye, FileText, X } from 'lucide-react'
import api from '../../services/api'
import { downloadPrivateFile, fetchPrivateFile } from '../../utils/download'
import { useAutoRefresh } from '../../utils/dataSync'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Une erreur est survenue lors du chargement des notes.'
}

export default function StudentGrades() {
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [previewFile, setPreviewFile] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  useEffect(() => () => {
    if (previewFile?.url) URL.revokeObjectURL(previewFile.url)
  }, [previewFile?.url])

  const loadGrades = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/student/graded-submissions/')
      setSubmissions(Array.isArray(data) ? data : data.results || [])
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadGrades()
  }, [loadGrades])
  useAutoRefresh(() => loadGrades({ silent: true }))

  const downloadSubmission = async (url, name) => {
    setDownloadError('')
    try {
      await downloadPrivateFile(url, name)
    } catch (downloadFailure) {
      setDownloadError(messageFrom(downloadFailure))
    }
  }

  const viewCorrectedFile = async (submission) => {
    setDownloadError('')
    setPreviewLoading(true)
    setPreviewFile({ name: submission.corrected_file_name || 'Fichier corrigé', loading: true })
    try {
      const blob = await fetchPrivateFile(submission.corrected_file_url)
      setPreviewFile({
        name: submission.corrected_file_name || 'Fichier corrigé',
        type: blob.type,
        url: URL.createObjectURL(blob),
      })
    } catch (previewError) {
      setPreviewFile(null)
      setDownloadError(messageFrom(previewError))
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading">
        <div>
          <h2>Mes notes et corrections</h2>
          <p>Retrouvez les notes et les commentaires enregistrés par vos professeurs.</p>
        </div>
      </div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {downloadError && <div className="error-message" role="alert">{downloadError}</div>}
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
      {loading ? <p className="teacher-empty">Chargement de vos notes...</p> : submissions.length === 0 ? (
        <div className="teacher-empty">
          <ClipboardCheck size={28} />
          <strong>Aucun devoir corrigé pour le moment.</strong>
          <span>Les devoirs apparaîtront ici dès que le professeur aura enregistré sa correction.</span>
        </div>
      ) : (
        <div className="student-assignment-list">
          {submissions.map((submission) => (
            <article className="student-assignment-card student-grade-card" key={submission.id}>
              <div className="student-assignment-heading">
                <div>
                  <span>{submission.course_title}</span>
                  <h3>{submission.assignment_title}</h3>
                </div>
                <span className="student-grade-score">
                  <Award size={17} />
                  {submission.grade !== null && submission.grade !== undefined ? `${submission.grade} / 20` : 'Corrigé'}
                </span>
              </div>
              <p className="student-grade-date">
                Corrigé le {new Date(submission.graded_at).toLocaleString('fr-FR')}
              </p>
              {submission.feedback ? (
                <div className="student-grade-feedback">
                  <strong>Commentaire du professeur</strong>
                  <p>{submission.feedback}</p>
                </div>
              ) : (
                <p className="student-grade-no-feedback">Aucun commentaire ajouté.</p>
              )}
              <button
                type="button"
                className="secondary-button student-grade-download"
                onClick={() => downloadSubmission(
                  submission.file_url,
                  submission.file_name || `${submission.assignment_title}-remise`,
                )}
              >
                <Download size={16} /> Télécharger ma copie remise
              </button>
              {submission.corrected_file_url && (
                <button
                  type="button"
                  className="primary-button student-grade-download"
                  onClick={() => viewCorrectedFile(submission)}
                >
                  <Eye size={16} /> Voir le devoir corrigé
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

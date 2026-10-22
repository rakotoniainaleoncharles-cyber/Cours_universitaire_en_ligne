import { useCallback, useEffect, useState } from 'react'
import { Activity, Clock3, FileText, Search, ShieldCheck, UserRound } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { useAutoRefresh } from '../../utils/dataSync'

const actionLabels = {
  create: 'Création',
  update: 'Modification',
  delete: 'Suppression',
  reset_password: 'Réinitialisation du mot de passe',
}

function getErrorMessage(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const message = Object.values(data).flat().find((value) => typeof value === 'string')
    if (message) return message
  }
  return 'Impossible de charger le journal administratif.'
}

export default function AdminAuditLog() {
  const [entries, setEntries] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadEntries = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/admin/audit-logs/', { params: search ? { search } : {} })
      setEntries(data)
    } catch (loadError) {
      setError(getErrorMessage(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [search])

  useEffect(() => { loadEntries() }, [loadEntries])
  useAutoRefresh(() => loadEntries({ silent: true }))

  const pageCount = Math.max(1, Math.ceil(entries.length / 10))
  const currentPage = Math.min(page, pageCount)
  const visibleEntries = entries.slice((currentPage - 1) * 10, currentPage * 10)

  return (
    <section className="user-management">
      <div className="user-management-heading"><div><h2>Journal administratif</h2><p>Historique en lecture seule des actions administratives importantes.</p></div></div>
      {error && <div className="error-message" role="alert">{error}</div>}
      <div className="audit-feed-toolbar">
        <label className="user-search audit-feed-search"><Search size={17} /><input aria-label="Rechercher dans le journal" placeholder="Rechercher une action ou une ressource" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} /></label>
      </div>
      {loading ? <p className="teacher-empty">Chargement du journal...</p> : entries.length === 0 ? (
        <div className="audit-feed-empty"><Activity size={25} /><strong>Aucune action journalisée.</strong><span>Les actions administratives apparaîtront ici.</span></div>
      ) : (
        <div className="audit-feed">
          {visibleEntries.map((entry) => (
            <article className="audit-post" key={entry.id}>
              <div className="audit-post-avatar"><UserRound size={20} /></div>
              <div className="audit-post-content">
                <header className="audit-post-header">
                  <div><strong>{entry.actor_email || 'Compte administrateur'}</strong><span>a effectué une action administrative</span></div>
                  <time dateTime={entry.created_at}><Clock3 size={14} />{new Date(entry.created_at).toLocaleString('fr-FR')}</time>
                </header>
                <p className="audit-post-description">{entry.description}</p>
                <footer className="audit-post-meta">
                  <span className={`audit-action-badge audit-action-${entry.action}`}><ShieldCheck size={14} />{actionLabels[entry.action] || entry.action}</span>
                  <span className="audit-resource"><FileText size={14} />{entry.resource_type}{entry.resource_id ? ` · ${entry.resource_id}` : ''}</span>
                </footer>
              </div>
            </article>
          ))}
        </div>
      )}
      {!loading && entries.length > 0 && <Pagination page={currentPage} pageSize={10} total={entries.length} onPageChange={setPage} />}
    </section>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { KeyRound, Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import api from '../../services/api'
import Pagination from '../../components/Pagination'
import { useAutoRefresh } from '../../utils/dataSync'
import UserAvatar from '../../components/UserAvatar'

const emptyForm = {
  email: '',
  first_name: '',
  last_name: '',
  matricule: '',
  phone: '',
  role: 'teacher',
  password: '',
}

const roleLabels = {
  admin: 'Administrateur',
  teacher: 'Professeur',
  student: 'Étudiant',
}

function getErrorMessage(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const firstError = Object.values(data).flat().find((value) => typeof value === 'string')
    if (firstError) return firstError
  }
  return 'Une erreur est survenue. Vérifiez la connexion et les informations saisies.'
}

export default function UserManagement() {
  const [users, setUsers] = useState([])
  const [studentSearch, setStudentSearch] = useState('')
  const [teacherSearch, setTeacherSearch] = useState('')
  const [studentStatusFilter, setStudentStatusFilter] = useState('all')
  const [teacherStatusFilter, setTeacherStatusFilter] = useState('all')
  const [adminStatusFilter, setAdminStatusFilter] = useState('all')
  const [studentPage, setStudentPage] = useState(1)
  const [teacherPage, setTeacherPage] = useState(1)
  const [adminPage, setAdminPage] = useState(1)
  const [resetTarget, setResetTarget] = useState(null)
  const [resetPassword, setResetPassword] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [editingUser, setEditingUser] = useState(null)
  const [formOpen, setFormOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadUsers = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/users/')
      setUsers(data)
    } catch (loadError) {
      setError(getErrorMessage(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])
  useAutoRefresh(() => loadUsers({ silent: true }))

  const resetForm = () => {
    setForm(emptyForm)
    setEditingUser(null)
    setFormOpen(false)
  }

  const startEditing = (user) => {
    setEditingUser(user)
    setForm({
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      matricule: user.matricule || '',
      phone: user.phone || '',
      role: user.role === 'admin' ? 'teacher' : user.role,
      password: '',
    })
    setError('')
    setNotice('')
    setFormOpen(true)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setNotice('')

    if (form.phone && !/^[0-9]{10}$/.test(form.phone)) {
      setError('Le numéro de téléphone doit contenir exactement 10 chiffres.')
      return
    }

    setSaving(true)
    const payload = { ...form }
    if (editingUser && !payload.password) delete payload.password

    try {
      if (editingUser) {
        await api.patch(`/users/${editingUser.id}/`, payload)
        setNotice('Le compte a été mis à jour.')
      } else {
        await api.post('/users/', payload)
        setNotice('Le compte a été créé.')
      }
      resetForm()
      await loadUsers()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (user) => {
    if (!window.confirm(`Supprimer le compte de ${user.first_name} ${user.last_name} (${user.email}) ?`)) return
    setError('')
    setNotice('')
    try {
      await api.delete(`/users/${user.id}/`)
      setNotice('Le compte a été supprimé.')
      await loadUsers()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const toggleActive = async (user) => {
    const action = user.is_active
      ? 'désactiver'
      : user.role === 'teacher' ? 'valider et activer' : 'activer'
    if (!window.confirm(`Confirmer la ${action} du compte ${user.email} ?`)) return
    setError('')
    setNotice('')
    try {
      await api.patch(`/users/${user.id}/`, { is_active: !user.is_active })
      setNotice(user.is_active
        ? 'Le compte a été désactivé.'
        : user.role === 'teacher' ? 'Le compte professeur a été validé et activé.' : 'Le compte a été activé.')
      await loadUsers()
    } catch (updateError) {
      setError(getErrorMessage(updateError))
    }
  }

  const submitResetPassword = async (event) => {
    event.preventDefault()
    if (!resetTarget) return
    setError('')
    setNotice('')
    try {
      await api.post(`/users/${resetTarget.id}/reset-password/`, { password: resetPassword })
      setNotice(`Le mot de passe de ${resetTarget.email} a été réinitialisé.`)
      setResetTarget(null)
      setResetPassword('')
    } catch (resetError) {
      setError(getErrorMessage(resetError))
    }
  }

  const filterUsers = (role, query, status) => users.filter((user) => {
    if (user.role !== role || (status !== 'all' && String(user.is_active) !== status)) return false
    const normalizedQuery = query.trim().toLowerCase()
    const searchable = `${user.first_name} ${user.last_name} ${user.email} ${user.matricule || ''} ${user.phone || ''}`.toLowerCase()
    return !normalizedQuery || searchable.includes(normalizedQuery)
  })
  const studentUsers = filterUsers('student', studentSearch, studentStatusFilter)
  const teacherUsers = filterUsers('teacher', teacherSearch, teacherStatusFilter)
  const adminUsers = filterUsers('admin', '', adminStatusFilter)
  const studentsCount = users.filter((user) => user.role === 'student').length
  const teachersCount = users.filter((user) => user.role === 'teacher').length

  const renderUserTable = ({ title, role, rows, search, setSearch, status, setStatus, page, setPage }) => {
    const safePage = Math.min(page, Math.max(1, Math.ceil(rows.length / 10)))
    const pageUsers = rows.slice((safePage - 1) * 10, safePage * 10)
    return (
      <section className="user-role-section" aria-labelledby={`user-role-${role}`}>
        <div className="user-role-heading">
          <div><h3 id={`user-role-${role}`}>{title}</h3><span>{rows.length} résultat{rows.length > 1 ? 's' : ''}</span></div>
        </div>
        <div className="user-table-card">
          <div className="user-table-toolbar user-admin-user-toolbar">
            {setSearch && (
              <label className="user-search admin-role-search">
                <Search size={17} />
                <input aria-label={`Rechercher un ${role === 'teacher' ? 'professeur' : 'étudiant'}`} placeholder={role === 'teacher' ? 'Rechercher un professeur par nom ou e-mail' : 'Rechercher un étudiant par nom, matricule ou e-mail'} value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
              </label>
            )}
            <select aria-label={`Filtrer les ${title.toLowerCase()} par statut`} value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}>
              <option value="all">Tous les statuts</option><option value="true">Actifs</option><option value="false">Inactifs</option>
            </select>
          </div>
          {loading ? (
            <p className="user-table-empty">Chargement des utilisateurs...</p>
          ) : rows.length === 0 ? (
            <p className="user-table-empty">Aucun {role === 'teacher' ? 'professeur' : role === 'student' ? 'étudiant' : 'administrateur'} ne correspond à cette recherche.</p>
          ) : (
            <div className="user-table-scroll">
              <table className="user-table">
                <thead><tr><th>Utilisateur</th><th>Matricule</th><th>Rôle</th><th>Adresse e-mail</th><th>Statut</th><th>Actions</th></tr></thead>
                <tbody>
                  {pageUsers.map((user) => (
                    <tr key={user.id}>
                      <td data-label="Utilisateur"><div className="user-identity"><UserAvatar src={user.avatar_url} name={`${user.first_name} ${user.last_name}`} /><strong>{user.first_name} {user.last_name}</strong></div></td>
                      <td data-label="Matricule">{user.matricule || '—'}</td>
                      <td data-label="Rôle"><span className={`role-badge role-${user.role}`}>{roleLabels[user.role] || user.role}</span></td>
                      <td data-label="Adresse e-mail">{user.email}</td>
                      <td data-label="Statut">{user.is_active ? 'Actif' : 'Inactif'}</td>
                      <td data-label="Actions">
                        <div className="user-row-actions">
                          <button type="button" className="table-action" onClick={() => startEditing(user)} aria-label={`Modifier ${user.email}`} title="Modifier"><Pencil size={16} /></button>
                          {user.role !== 'admin' && <button type="button" className="table-action" onClick={() => toggleActive(user)} aria-label={`${user.is_active ? 'Désactiver' : user.role === 'teacher' ? 'Valider et activer' : 'Activer'} ${user.email}`} title={user.is_active ? 'Désactiver' : user.role === 'teacher' ? 'Valider et activer' : 'Activer'}>{user.is_active ? '−' : '+'}</button>}
                          {user.role !== 'admin' && <button type="button" className="table-action" onClick={() => { setResetTarget(user); setResetPassword('') }} aria-label={`Réinitialiser le mot de passe de ${user.email}`} title="Réinitialiser le mot de passe"><KeyRound size={15} /></button>}
                          {user.role !== 'admin' && <button type="button" className="table-action danger" onClick={() => handleDelete(user)} aria-label={`Supprimer ${user.email}`} title="Supprimer"><Trash2 size={16} /></button>}
                          {user.role === 'admin' && <span className="admin-locked"><KeyRound size={15} /> Unique</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!loading && rows.length > 0 && <Pagination page={safePage} pageSize={10} total={rows.length} onPageChange={setPage} />}
        </div>
      </section>
    )
  }

  return (
    <section className="user-management">
      <div className="user-management-heading">
        <div>
          <h2>Gestion des utilisateurs</h2>
          <p>Créez et gérez les comptes des professeurs et des étudiants. Les demandes publiques de compte professeur doivent être activées ici avant la première connexion.</p>
        </div>
        <button
          type="button"
          className="primary-button user-add-button"
          onClick={() => {
            setEditingUser(null)
            setForm(emptyForm)
            setError('')
            setNotice('')
            setFormOpen(true)
          }}
        >
          <Plus size={17} /> Ajouter un utilisateur
        </button>
      </div>

      <div className="user-counts">
        <div className="user-count-card"><span>Étudiants</span><strong>{studentsCount}</strong></div>
        <div className="user-count-card"><span>Professeurs</span><strong>{teachersCount}</strong></div>
      </div>

      {error && <div className="error-message user-feedback" role="alert">{error}</div>}
      {notice && <div className="success-message user-feedback" role="status">{notice}</div>}

      {formOpen && (
        <form className="user-form-card" onSubmit={handleSubmit}>
          <div className="user-form-heading">
            <div>
              <h3>{editingUser ? 'Modifier le compte' : 'Créer un compte'}</h3>
              <p>Le compte administrateur unique ne peut pas être créé depuis cette page.</p>
            </div>
            <button type="button" className="icon-button" aria-label="Fermer le formulaire" onClick={resetForm}>
              <X size={18} />
            </button>
          </div>

          <div className="user-form-grid">
            <label className="input-group">
              <span>Prénom</span>
              <input required value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} />
            </label>
            <label className="input-group">
              <span>Nom</span>
              <input required value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} />
            </label>
            <label className="input-group">
              <span>Adresse e-mail</span>
              <input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            </label>
            <label className="input-group">
              <span>Matricule (facultatif)</span>
              <input maxLength={40} value={form.matricule} onChange={(event) => setForm({ ...form, matricule: event.target.value })} />
            </label>
            <label className="input-group">
              <span>Téléphone (facultatif)</span>
              <input
                type="tel"
                inputMode="numeric"
                maxLength={10}
                placeholder="+261 00 000 00"
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
              />
            </label>
            <label className="input-group">
              <span>Rôle</span>
              <select disabled={editingUser?.role === 'admin'} value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
                <option value="teacher">Professeur</option>
                <option value="student">Étudiant</option>
              </select>
            </label>
            <label className="input-group user-password-field">
              <span>{editingUser ? 'Nouveau mot de passe (facultatif)' : 'Mot de passe temporaire'}</span>
              <input
                type="password"
                minLength={8}
                required={!editingUser}
                autoComplete="new-password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
              />
            </label>
          </div>
          <div className="user-form-actions">
            <button type="button" className="secondary-button" onClick={resetForm}>Annuler</button>
            <button type="submit" className="primary-button" disabled={saving}>
              {saving ? 'Enregistrement...' : editingUser ? 'Enregistrer' : 'Créer le compte'}
            </button>
          </div>
        </form>
      )}

      {resetTarget && (
        <form className="user-form-card" onSubmit={submitResetPassword}>
          <div className="user-form-heading"><div><h3>Réinitialiser le mot de passe</h3><p>Compte : {resetTarget.email}. Le nouveau mot de passe ne sera jamais affiché après l’envoi.</p></div><button type="button" className="icon-button" aria-label="Fermer" onClick={() => { setResetTarget(null); setResetPassword('') }}><X size={18} /></button></div>
          <label className="input-group user-password-field"><span>Nouveau mot de passe temporaire</span><input type="password" minLength={8} required autoComplete="new-password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} /></label>
          <div className="user-form-actions"><button type="button" className="secondary-button" onClick={() => { setResetTarget(null); setResetPassword('') }}>Annuler</button><button type="submit" className="primary-button">Réinitialiser</button></div>
        </form>
      )}

      {renderUserTable({
        title: 'Étudiants',
        role: 'student',
        rows: studentUsers,
        search: studentSearch,
        setSearch: setStudentSearch,
        status: studentStatusFilter,
        setStatus: setStudentStatusFilter,
        page: studentPage,
        setPage: setStudentPage,
      })}
      {renderUserTable({
        title: 'Professeurs',
        role: 'teacher',
        rows: teacherUsers,
        search: teacherSearch,
        setSearch: setTeacherSearch,
        status: teacherStatusFilter,
        setStatus: setTeacherStatusFilter,
        page: teacherPage,
        setPage: setTeacherPage,
      })}
      {users.some((user) => user.role === 'admin') && renderUserTable({
        title: 'Administrateur',
        role: 'admin',
        rows: adminUsers,
        status: adminStatusFilter,
        setStatus: setAdminStatusFilter,
        page: adminPage,
        setPage: setAdminPage,
      })}
    </section>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Lock, Mail, UserPlus } from 'lucide-react'
import api, { saveAuthSession } from '../services/api'
import { useAuth } from '../context/AuthContext'
import SettingsButton from '../components/SettingsButton'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setUser } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [registration, setRegistration] = useState({ first_name: '', last_name: '', role: 'student', phone: '' })
  const [faculties, setFaculties] = useState([])
  const [subjects, setSubjects] = useState([])
  const [facultyId, setFacultyId] = useState('')
  const [selectedSubjectIds, setSelectedSubjectIds] = useState([])
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [isRegistering, setIsRegistering] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    if (!isRegistering) return undefined
    let active = true
    api.get('/faculties/')
      .then(({ data }) => {
        if (active) setFaculties(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (active) setError('Impossible de charger les filières. Réessayez dans quelques instants.')
      })
    return () => { active = false }
  }, [isRegistering])

  useEffect(() => {
    if (!isRegistering || registration.role !== 'student' || !facultyId) {
      setSubjects([])
      return undefined
    }
    let active = true
    setCatalogLoading(true)
    api.get('/subjects/', { params: { faculty: facultyId } })
      .then(({ data }) => {
        if (active) setSubjects(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (active) setError('Impossible de charger les matières de cette filière.')
      })
      .finally(() => {
        if (active) setCatalogLoading(false)
      })
    return () => { active = false }
  }, [facultyId, isRegistering, registration.role])

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setNotice('')

    const email = form.email.trim()
    const password = form.password
    if (isRegistering && !registration.first_name.trim()) {
      setError('Saisissez votre prénom pour créer le compte.')
      return
    }
    if (isRegistering && !registration.last_name.trim()) {
      setError('Saisissez votre nom pour créer le compte.')
      return
    }
    if (isRegistering && registration.role === 'student' && !registration.phone.trim()) {
      setError('Saisissez votre numéro de téléphone pour envoyer l’inscription.')
      return
    }
    if (isRegistering && registration.phone && !/^[0-9]{10}$/.test(registration.phone)) {
      setError('Le numéro de téléphone doit contenir exactement 10 chiffres.')
      return
    }
    if (isRegistering && registration.role === 'student' && !facultyId) {
      setError('Choisissez votre filière.')
      return
    }
    if (isRegistering && registration.role === 'student' && selectedSubjectIds.length === 0) {
      setError('Choisissez au moins une matière dans cette filière.')
      return
    }
    if (!email) {
      setError('Saisissez votre adresse e-mail.')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Saisissez une adresse e-mail valide.')
      return
    }
    if (!password) {
      setError('Saisissez votre mot de passe.')
      return
    }
    if (isRegistering && password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }

    setLoading(true)

    try {
      const { data } = await api.post(isRegistering ? '/auth/register/' : '/auth/login/', {
        email,
        password,
        ...(isRegistering ? {
          ...registration,
          ...(registration.role === 'student' ? {
            faculty: facultyId,
            subject_ids: selectedSubjectIds,
          } : {}),
        } : {}),
      })
      if (data.pending_approval) {
        setNotice(data.detail)
        setForm((current) => ({ ...current, password: '' }))
        setIsRegistering(false)
        return
      }
      saveAuthSession(data.access, data.refresh)
      setUser(data.user)
      const role = data.user.role
      navigate(role === 'admin' ? '/admin' : role === 'teacher' ? '/teacher' : '/student', { replace: true })
    } catch (err) {
      const response = err?.response?.data
      const detail = typeof response?.detail === 'string'
        ? response.detail
        : response && typeof response === 'object'
          ? Object.values(response).flat().find((value) => typeof value === 'string')
          : null
      setError(detail || (isRegistering ? "Impossible de créer le compte." : "Erreur d'authentification."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <SettingsButton className="login-settings-button" />
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-icon">U</div>
          <div>
            <h2>Université de Strasbourg</h2>
            <p>Portail académique</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form" noValidate>
          {isRegistering && (
            <>
              <div className="input-group">
                <label htmlFor="registration-role">Type de compte</label>
                <div className="input-wrap login-role-wrap">
                  <UserPlus size={16} />
                  <select
                    id="registration-role"
                    className="login-role-select"
                    value={registration.role}
                    onChange={(event) => {
                      setRegistration({ ...registration, role: event.target.value })
                      setFacultyId('')
                      setSelectedSubjectIds([])
                      setError('')
                    }}
                  >
                    <option value="student">Étudiant</option>
                    <option value="teacher">Professeur</option>
                  </select>
                </div>
              </div>
              <div className="input-group">
                <label htmlFor="first_name">Prénom</label>
                <div className="input-wrap">
                  <input id="first_name" name="first_name" value={registration.first_name} onChange={(event) => setRegistration({ ...registration, first_name: event.target.value })} autoComplete="given-name" required />
                </div>
              </div>
              <div className="input-group">
                <label htmlFor="last_name">Nom</label>
                <div className="input-wrap">
                  <input id="last_name" name="last_name" value={registration.last_name} onChange={(event) => setRegistration({ ...registration, last_name: event.target.value })} autoComplete="family-name" required />
                </div>
              </div>
              {registration.role === 'student' && (
                <>
                  <div className="input-group">
                    <label htmlFor="student-faculty">Filière</label>
                    <div className="input-wrap login-role-wrap">
                      <select
                        id="student-faculty"
                        className="login-role-select"
                        value={facultyId}
                        onChange={(event) => {
                          setFacultyId(event.target.value)
                          setSelectedSubjectIds([])
                          setError('')
                        }}
                        required
                      >
                        <option value="">Choisir une filière</option>
                        {faculties.map((faculty) => (
                          <option key={faculty.id} value={faculty.id}>{faculty.name} ({faculty.code})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {facultyId && (
                    <div className="input-group">
                      <label>Matières à suivre</label>
                      {catalogLoading ? <p className="auth-registration-note">Chargement des matières...</p> : subjects.length ? (
                        <div className="registration-subject-list">
                          {subjects.map((subject) => (
                            <label className="registration-subject-option" key={subject.id}>
                              <input
                                type="checkbox"
                                checked={selectedSubjectIds.includes(subject.id)}
                                onChange={(event) => setSelectedSubjectIds((current) => (
                                  event.target.checked
                                    ? [...current, subject.id]
                                    : current.filter((id) => id !== subject.id)
                                ))}
                              />
                              <span>
                                <strong>{subject.name}</strong>
                                <small>{subject.code} · {subject.level_name}</small>
                              </span>
                            </label>
                          ))}
                        </div>
                      ) : <p className="auth-registration-note">Aucune matière disponible pour cette filière et l’année universitaire active.</p>}
                    </div>
                  )}
                  <div className="input-group">
                    <label htmlFor="phone">Numéro de téléphone</label>
                    <div className="input-wrap">
                      <input
                        id="phone"
                        name="phone"
                        type="tel"
                        inputMode="numeric"
                        maxLength={10}
                        autoComplete="tel"
                        value={registration.phone}
                        onChange={(event) => setRegistration({ ...registration, phone: event.target.value })}
                        placeholder="+261 00 000 00"
                        required={registration.role === 'student'}
                      />
                    </div>
                  </div>
                </>
              )}
            </>
          )}
          <div className="input-group">
            <label htmlFor="email">Adresse e-mail</label>
            <div className="input-wrap">
              <Mail size={16} />
              <input id="email" type="email" name="email" value={form.email} onChange={handleChange} placeholder="prenom.nom@unistra.fr" autoComplete="email" required />
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="password">{isRegistering ? 'Créer un mot de passe' : 'Mot de passe'}</label>
            <div className="input-wrap">
              <Lock size={16} />
              <input id="password" type={showPassword ? 'text' : 'password'} name="password" value={form.password} onChange={handleChange} placeholder={isRegistering ? '8 caractères minimum' : 'Votre mot de passe'} autoComplete={isRegistering ? 'new-password' : 'current-password'} minLength={isRegistering ? 8 : undefined} required />
              <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error ? <div className="error-message" role="alert">{error}</div> : null}
          <button type="submit" className="primary-button" disabled={loading}>
            {loading ? (isRegistering ? 'Création du compte...' : 'Connexion...') : (isRegistering ? `Créer mon compte ${registration.role === 'teacher' ? 'professeur' : 'étudiant'}` : 'Se connecter')}
          </button>
        </form>
        {notice && <div className="success-message auth-notice" role="status">{notice}</div>}
        <p className="auth-switch">
          {isRegistering ? 'Vous avez déjà un compte ?' : 'Pas encore de compte ?'}
          {' '}
          <button type="button" onClick={() => { setIsRegistering(!isRegistering); setError(''); setNotice('') }}>
            {isRegistering ? 'Se connecter' : <><UserPlus size={15} /> Créer un compte</>}
          </button>
        </p>
        {isRegistering && (
          <p className="auth-registration-note">
            {registration.role === 'teacher'
              ? 'Les comptes professeur doivent être validés par l’administration avant de pouvoir se connecter.'
              : 'Choisissez une filière puis les matières souhaitées. Votre demande d’inscription et vos choix seront soumis à validation par l’administration.'}
          </p>
        )}
      </div>
    </div>
  )
}

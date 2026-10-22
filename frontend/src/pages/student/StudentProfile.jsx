import { useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import api from '../../services/api'
import { useAuth } from '../../context/AuthContext'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'Une erreur est survenue.'
}

export default function StudentProfile() {
  const { setUser } = useAuth()
  const [profile, setProfile] = useState(null)
  const [password, setPassword] = useState({ current_password: '', new_password: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let active = true
    api.get('/student/profile/')
      .then(({ data }) => { if (active) setProfile(data) })
      .catch((loadError) => { if (active) setError(messageFrom(loadError)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const saveProfile = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const { data } = await api.patch('/student/profile/', {
        first_name: profile.first_name,
        last_name: profile.last_name,
        email: profile.email,
      })
      setProfile(data)
      setUser(data)
      setNotice('Votre profil a été mis à jour.')
    } catch (saveError) {
      setError(messageFrom(saveError))
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const { data } = await api.post('/student/change-password/', password)
      setPassword({ current_password: '', new_password: '' })
      setNotice(data.detail)
    } catch (saveError) {
      setError(messageFrom(saveError))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="teacher-empty">Chargement du profil...</p>

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading"><div><h2>Mon profil étudiant</h2><p>Modifiez vos coordonnées ou changez votre mot de passe. Votre rôle et votre matricule restent protégés.</p></div></div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      {profile && (
        <div className="student-profile-grid">
          <form className="teacher-form-card" onSubmit={saveProfile}>
            <div className="teacher-panel-heading"><h3>Informations personnelles</h3></div>
            <label className="input-group"><span>Prénom</span><input required value={profile.first_name || ''} onChange={(event) => setProfile({ ...profile, first_name: event.target.value })} /></label>
            <label className="input-group"><span>Nom</span><input required value={profile.last_name || ''} onChange={(event) => setProfile({ ...profile, last_name: event.target.value })} /></label>
            <label className="input-group"><span>Adresse e-mail</span><input required type="email" value={profile.email || ''} onChange={(event) => setProfile({ ...profile, email: event.target.value })} /></label>
            <label className="input-group"><span>Matricule (lecture seule)</span><input value={profile.matricule || ''} readOnly /></label>
            <button type="submit" className="primary-button" disabled={saving}><Save size={16} /> Enregistrer le profil</button>
          </form>
          <form className="teacher-form-card" onSubmit={changePassword}>
            <div className="teacher-panel-heading"><h3>Sécurité</h3></div>
            <label className="input-group"><span>Mot de passe actuel</span><input required type="password" autoComplete="current-password" value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} /></label>
            <label className="input-group"><span>Nouveau mot de passe</span><input required type="password" minLength={8} autoComplete="new-password" value={password.new_password} onChange={(event) => setPassword({ ...password, new_password: event.target.value })} /></label>
            <button type="submit" className="primary-button" disabled={saving}><Save size={16} /> Changer le mot de passe</button>
          </form>
        </div>
      )}
    </section>
  )
}

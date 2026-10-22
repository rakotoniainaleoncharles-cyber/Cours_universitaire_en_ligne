import { useEffect, useState } from 'react'
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

export default function TeacherProfile() {
  const { setUser } = useAuth()
  const [profile, setProfile] = useState({ first_name: '', last_name: '', email: '' })
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    api.get('/teacher/profile/')
      .then(({ data }) => setProfile({ first_name: data.first_name, last_name: data.last_name, email: data.email }))
      .catch((loadError) => setError(messageFrom(loadError)))
      .finally(() => setLoading(false))
  }, [])

  const updateProfile = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const { data } = await api.patch('/teacher/profile/', profile)
      setProfile({ first_name: data.first_name, last_name: data.last_name, email: data.email })
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
      const { data } = await api.post('/teacher/change-password/', passwords)
      setPasswords({ current_password: '', new_password: '' })
      setNotice(data.detail)
    } catch (passwordError) {
      setError(messageFrom(passwordError))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="teacher-empty">Chargement du profil...</p>

  return (
    <section className="teacher-dashboard">
      <div className="teacher-heading"><div><h2>Mon profil</h2><p>Modifiez vos informations personnelles et sécurisez votre compte.</p></div></div>
      {error && <div className="error-message" role="alert">{error}</div>}
      {notice && <div className="success-message" role="status">{notice}</div>}
      <form className="teacher-form-card" onSubmit={updateProfile}>
        <div className="teacher-form-heading"><div><h3>Informations personnelles</h3><p>Votre rôle professeur et vos permissions sont gérés par l’administration.</p></div></div>
        <div className="teacher-form-grid">
          <label className="input-group"><span>Prénom</span><input required value={profile.first_name} onChange={(event) => setProfile({ ...profile, first_name: event.target.value })} /></label>
          <label className="input-group"><span>Nom</span><input required value={profile.last_name} onChange={(event) => setProfile({ ...profile, last_name: event.target.value })} /></label>
          <label className="input-group teacher-wide-field"><span>Adresse e-mail</span><input type="email" required value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} /></label>
        </div>
        <div className="teacher-form-actions"><button className="primary-button" type="submit" disabled={saving}>{saving ? 'Enregistrement...' : 'Enregistrer le profil'}</button></div>
      </form>
      <form className="teacher-form-card" onSubmit={changePassword}>
        <div className="teacher-form-heading"><div><h3>Changer le mot de passe</h3><p>Le mot de passe actuel est nécessaire pour confirmer le changement.</p></div></div>
        <div className="teacher-form-grid">
          <label className="input-group"><span>Mot de passe actuel</span><input type="password" autoComplete="current-password" required value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} /></label>
          <label className="input-group"><span>Nouveau mot de passe</span><input type="password" minLength={8} autoComplete="new-password" required value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} /></label>
        </div>
        <div className="teacher-form-actions"><button className="primary-button" type="submit" disabled={saving}>{saving ? 'Modification...' : 'Changer le mot de passe'}</button></div>
      </form>
    </section>
  )
}

import { useEffect, useState } from 'react'
import { Camera, Info, Moon, Settings, Sun, Upload, X } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import UserAvatar from './UserAvatar'

export default function SettingsButton({ className = '' }) {
  const { theme, setTheme } = useTheme()
  const { user, setUser } = useAuth()
  const [open, setOpen] = useState(false)
  const [draftTheme, setDraftTheme] = useState(theme)
  const [avatarFile, setAvatarFile] = useState(null)
  const [avatarPreview, setAvatarPreview] = useState('')
  const [avatarSaving, setAvatarSaving] = useState(false)
  const [avatarError, setAvatarError] = useState('')
  const [avatarNotice, setAvatarNotice] = useState('')

  const openSettings = () => {
    setDraftTheme(theme)
    setOpen(true)
  }

  const finishSettings = () => {
    setTheme(draftTheme)
    setOpen(false)
  }

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreview('')
      return undefined
    }
    const previewUrl = URL.createObjectURL(avatarFile)
    setAvatarPreview(previewUrl)
    return () => URL.revokeObjectURL(previewUrl)
  }, [avatarFile])

  const saveAvatar = async (event) => {
    event.preventDefault()
    if (!avatarFile) return
    setAvatarSaving(true)
    setAvatarError('')
    setAvatarNotice('')
    try {
      const formData = new FormData()
      formData.append('avatar', avatarFile)
      const { data } = await api.patch('/auth/profile/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setUser(data)
      setAvatarFile(null)
      setAvatarNotice('Votre photo de profil a été mise à jour.')
    } catch (error) {
      const data = error?.response?.data
      const message = typeof data?.detail === 'string'
        ? data.detail
        : data?.avatar?.[0] || 'Impossible de mettre à jour la photo. Vérifiez le format de l’image.'
      setAvatarError(message)
    } finally {
      setAvatarSaving(false)
    }
  }

  useEffect(() => {
    if (!open) return undefined
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [open])

  return (
    <>
      <button
        type="button"
        className={`settings-button ${className}`.trim()}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={openSettings}
      >
        <Settings size={17} /> <span>Paramètres</span>
      </button>
      {open && (
        <div className="settings-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setOpen(false)
        }}>
          <section className="settings-dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title">
            <header className="settings-dialog-header">
              <div><Settings size={20} /><h2 id="settings-title">Paramètres</h2></div>
              <button type="button" className="icon-button" aria-label="Fermer les paramètres" onClick={() => setOpen(false)}>
                <X size={18} />
              </button>
            </header>
            <div className="settings-dialog-content">
              {user && <section className="settings-section settings-profile" aria-labelledby="profile-photo-title">
                <div className="settings-profile-heading">
                  {avatarPreview
                    ? <span className="profile-avatar"><img src={avatarPreview} alt="Aperçu de votre photo de profil" /></span>
                    : <UserAvatar src={user?.avatar_url} name={`${user?.first_name || ''} ${user?.last_name || ''}`} />}
                  <div>
                    <h3 id="profile-photo-title">Photo de profil</h3>
                    <p>Elle sera visible aux utilisateurs dans les différentes interfaces.</p>
                  </div>
                </div>
                <form className="settings-avatar-form" onSubmit={saveAvatar}>
                  <label className="settings-avatar-picker">
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(event) => {
                        setAvatarFile(event.target.files?.[0] || null)
                        setAvatarError('')
                        setAvatarNotice('')
                      }}
                    />
                    <Camera size={16} /> Choisir une photo
                  </label>
                  <span className="settings-avatar-hint">JPEG, PNG ou WebP · aucune limite de taille de fichier</span>
                  {avatarError && <p className="error-message" role="alert">{avatarError}</p>}
                  {avatarNotice && <p className="success-message" role="status">{avatarNotice}</p>}
                  {avatarFile && (
                    <button type="submit" className="primary-button" disabled={avatarSaving}>
                      <Upload size={16} /> {avatarSaving ? 'Enregistrement...' : 'Enregistrer la photo'}
                    </button>
                  )}
                </form>
              </section>}
              <section className="settings-section" aria-labelledby="theme-setting-title">
                <div>
                  <h3 id="theme-setting-title">Apparence</h3>
                  <p>Choisissez le thème utilisé dans toutes les interfaces.</p>
                </div>
                <div className="theme-options" role="group" aria-label="Choisir le thème">
                  <button
                    type="button"
                    className={`theme-option ${draftTheme === 'light' ? 'selected' : ''}`}
                    aria-pressed={draftTheme === 'light'}
                    onClick={() => setDraftTheme('light')}
                  >
                    <Sun size={18} /> Clair
                  </button>
                  <button
                    type="button"
                    className={`theme-option ${draftTheme === 'dark' ? 'selected' : ''}`}
                    aria-pressed={draftTheme === 'dark'}
                    onClick={() => setDraftTheme('dark')}
                  >
                    <Moon size={18} /> Sombre
                  </button>
                </div>
              </section>
              <section className="settings-about" aria-labelledby="about-title">
                <div className="settings-about-icon"><Info size={20} /></div>
                <div>
                  <h3 id="about-title">À propos du logiciel</h3>
                  <p><strong>Portail académique universitaire</strong></p>
                  <p>Une plateforme pour gérer les cours, les matières, les leçons, les devoirs, les remises et le suivi des notes.</p>
                  <small>Version 1.0.0</small>
                </div>
              </section>
            </div>
            <footer className="settings-dialog-footer">
              <button type="button" className="primary-button" onClick={finishSettings}>Terminer</button>
            </footer>
          </section>
        </div>
      )}
    </>
  )
}

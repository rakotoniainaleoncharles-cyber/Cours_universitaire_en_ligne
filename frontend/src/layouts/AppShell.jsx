import { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { GraduationCap, LogOut, Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import SettingsButton from '../components/SettingsButton'
import UserAvatar from '../components/UserAvatar'
import { useAutoRefresh } from '../utils/dataSync'
import api from '../services/api'

const adminNavItems = [
  { label: 'Tableau de bord', path: '/admin' },
  { label: 'Utilisateurs', path: '/admin/users' },
  { label: 'Filières', path: '/admin/faculties' },
  { label: 'Niveaux', path: '/admin/levels' },
  { label: 'Années académiques', path: '/admin/academic-years' },
  { label: 'Matières / affectations', path: '/admin/subjects' },
  { label: 'Inscriptions', path: '/admin/enrollments' },
  { label: 'Cours', path: '/admin/courses' },
  { label: 'Leçons', path: '/admin/lessons' },
  { label: 'Documents', path: '/admin/documents' },
  { label: 'Devoirs', path: '/admin/assignments' },
  { label: 'Annonces', path: '/admin/announcements' },
  { label: 'Journal d’activité', path: '/admin/activity' },
]

const teacherNavItems = [
  { label: 'Tableau de bord', path: '/teacher' },
  { label: 'Mes cours', path: '/teacher/courses' },
  { label: 'Mes matières', path: '/teacher/subjects' },
  { label: 'Étudiants', path: '/teacher/students' },
  { label: 'Devoirs', path: '/teacher/assignments' },
  { label: 'Annonces', path: '/teacher/announcements' },
  { label: 'Mon profil', path: '/teacher/profile' },
]

const studentNavItems = [
  { label: 'Tableau de bord', path: '/student' },
  { label: 'Mes matières et cours', path: '/student/courses' },
  { label: 'Annonces', path: '/student/announcements' },
  { label: 'Devoirs', path: '/student/assignments' },
  { label: 'Notes et corrections', path: '/student/grades' },
  { label: 'Mon profil', path: '/student/profile' },
]

export default function AppShell({ role }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, setUser } = useAuth()
  const [navigationOpen, setNavigationOpen] = useState(false)

  const navItems = role === 'admin' ? adminNavItems : role === 'teacher' ? teacherNavItems : studentNavItems
  const homePath = role === 'admin' ? '/admin' : role === 'teacher' ? '/teacher' : '/student'
  const activePath = navItems.some((item) => item.path === location.pathname) ? location.pathname : homePath
  useAutoRefresh(async () => {
    const { data } = await api.get('/auth/me/')
    setUser(data)
  })

  const handleLogout = async () => {
    try {
      await logout()
    } catch {
      window.alert('La session locale est fermée, mais le serveur n’a pas pu révoquer le jeton. Réessayez si nécessaire.')
    }
    navigate('/login')
  }

  const navigateTo = (path) => {
    navigate(path)
    setNavigationOpen(false)
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${navigationOpen ? 'navigation-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark"><GraduationCap size={20} /></div>
          <div>
            <strong>Université</strong>
            <small>{role === 'admin' ? 'Administration' : role === 'teacher' ? 'Professeur' : 'Étudiant'}</small>
          </div>
          <button
            type="button"
            className="mobile-navigation-toggle"
            aria-label={navigationOpen ? 'Fermer la navigation' : 'Ouvrir la navigation'}
            aria-expanded={navigationOpen}
            aria-controls="app-navigation"
            onClick={() => setNavigationOpen((open) => !open)}
          >
            {navigationOpen ? <X size={20} /> : <Menu size={20} />}
            <span>Menu</span>
          </button>
        </div>
        <nav id="app-navigation" className="nav-menu">
          {navItems.map((item) => (
            <button
              key={item.path}
              type="button"
              className={`nav-link ${activePath === item.path ? 'active' : ''}`}
              onClick={() => navigateTo(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="mobile-navigation-account">
          <div className="navigation-profile">
            <UserAvatar src={user?.avatar_url} name={`${user?.first_name || ''} ${user?.last_name || ''}`} />
            <span>Bienvenue, {user?.first_name || 'Utilisateur'}</span>
          </div>
          <SettingsButton />
          <button type="button" className="logout-button" onClick={handleLogout}><LogOut size={16} /> Déconnexion</button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <div className="topbar-profile">
              <UserAvatar src={user?.avatar_url} name={`${user?.first_name || ''} ${user?.last_name || ''}`} />
              <h1>Bienvenue, {user?.first_name || 'Utilisateur'}</h1>
            </div>
          </div>
          <div className="topbar-actions">
            <span>{user?.email}</span>
            <SettingsButton />
            <button type="button" className="logout-button" onClick={handleLogout}><LogOut size={16} /> Déconnexion</button>
          </div>
        </header>

        <div className="content-area">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

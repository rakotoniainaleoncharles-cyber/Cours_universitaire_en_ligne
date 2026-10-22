import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import api, { clearAuthSession, getAuthSessionId } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState('')
  const authRequestVersion = useRef(0)

  const loadUser = useCallback(async () => {
    setAuthError('')
    const requestVersion = ++authRequestVersion.current
    const requestSessionId = getAuthSessionId()
    if (!sessionStorage.getItem('accessToken') && !sessionStorage.getItem('refreshToken')) {
      setUser(null)
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const { data } = await api.get('/auth/me/')
      if (requestVersion === authRequestVersion.current && requestSessionId === getAuthSessionId()) {
        setUser(data)
        setAuthError('')
      }
    } catch {
      if (requestVersion === authRequestVersion.current && requestSessionId === getAuthSessionId()) {
        if (!sessionStorage.getItem('accessToken') && !sessionStorage.getItem('refreshToken')) {
          setUser(null)
        } else {
          setAuthError('Impossible de vérifier votre session pour le moment. Votre connexion est conservée.')
        }
      }
    } finally {
      if (requestVersion === authRequestVersion.current) setLoading(false)
    }
  }, [])

  const updateUser = useCallback((nextUser) => {
    authRequestVersion.current += 1
    setUser(nextUser)
    setAuthError('')
  }, [])

  useEffect(() => {
    void loadUser()

    const handleSessionExpired = () => {
      authRequestVersion.current += 1
      setUser(null)
      setAuthError('')
      setLoading(false)
    }
    const handleVerificationFailure = () => {
      authRequestVersion.current += 1
      setAuthError('Impossible de vérifier votre session pour le moment. Votre connexion est conservée.')
      setLoading(false)
    }
    window.addEventListener('auth:session-expired', handleSessionExpired)
    window.addEventListener('auth:verification-failed', handleVerificationFailure)

    return () => {
      window.removeEventListener('auth:session-expired', handleSessionExpired)
      window.removeEventListener('auth:verification-failed', handleVerificationFailure)
    }
  }, [loadUser])

  const value = useMemo(() => ({
    user,
    isAuthenticated: !!user,
    loading,
    authError,
    setUser: updateUser,
    refreshUser: loadUser,
    logout: async () => {
      const sessionId = getAuthSessionId()
      try {
        if (sessionId && sessionStorage.getItem('refreshToken')) {
          await api.get('/auth/me/')
          if (sessionId === getAuthSessionId()) {
            const refreshToken = sessionStorage.getItem('refreshToken')
            if (refreshToken) await api.post('/auth/logout/', { refresh: refreshToken })
          }
        }
      } finally {
        if (sessionId && clearAuthSession(sessionId)) updateUser(null)
      }
    },
  }), [user, loading, authError, loadUser, updateUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

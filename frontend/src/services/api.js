import axios from 'axios'
import { notifyDataChanged } from '../utils/dataSync'

// Keep API requests on the frontend origin in development (Vite proxies /api).
// Set VITE_API_BASE_URL when the API is hosted at a separate origin.
const baseURL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const ACCESS_TOKEN_KEY = 'accessToken'
const REFRESH_TOKEN_KEY = 'refreshToken'
const AUTH_SESSION_KEY = 'authSessionId'

if (typeof window !== 'undefined') {
  const legacyAccessToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  const legacyRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!sessionStorage.getItem(ACCESS_TOKEN_KEY) && legacyAccessToken) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, legacyAccessToken)
    if (legacyRefreshToken) sessionStorage.setItem(REFRESH_TOKEN_KEY, legacyRefreshToken)
    sessionStorage.setItem(AUTH_SESSION_KEY, crypto.randomUUID())
  }
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

const refreshRequests = new Map()

export function getAuthSessionId() {
  return sessionStorage.getItem(AUTH_SESSION_KEY)
}

export function saveAuthSession(accessToken, refreshToken) {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  sessionStorage.setItem(AUTH_SESSION_KEY, crypto.randomUUID())
}

export function clearAuthSession(expectedSessionId = getAuthSessionId()) {
  if (!expectedSessionId && getAuthSessionId()) return false
  if (expectedSessionId && getAuthSessionId() !== expectedSessionId) return false
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(AUTH_SESSION_KEY)
  return true
}

function sessionChangedError() {
  const error = new Error('La session a changé pendant la requête.')
  error.sessionChanged = true
  return error
}

function expireSession(expectedSessionId) {
  if (!clearAuthSession(expectedSessionId)) return
  window.dispatchEvent(new Event('auth:session-expired'))
}

function reportVerificationFailure(expectedSessionId) {
  if (getAuthSessionId() === expectedSessionId) {
    window.dispatchEvent(new Event('auth:verification-failed'))
  }
}

async function requestRefreshedAccessToken(staleAccessToken, expectedSessionId) {
  const refresh = async () => {
    if (getAuthSessionId() !== expectedSessionId) throw sessionChangedError()
    const currentAccessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY)
    if (currentAccessToken && currentAccessToken !== staleAccessToken) {
      return currentAccessToken
    }

    const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY)
    if (!refreshToken) {
      const error = new Error('La session a expiré.')
      error.sessionExpired = true
      throw error
    }

    try {
      const { data } = await axios.post(`${baseURL}/auth/token/refresh/`, { refresh: refreshToken })
      if (getAuthSessionId() !== expectedSessionId) throw sessionChangedError()
      sessionStorage.setItem(ACCESS_TOKEN_KEY, data.access)
      if (data.refresh) sessionStorage.setItem(REFRESH_TOKEN_KEY, data.refresh)
      return data.access
    } catch (error) {
      if ([400, 401].includes(error.response?.status) && getAuthSessionId() === expectedSessionId) {
        for (let attempt = 0; attempt < 10; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 100))
          const refreshedAccessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY)
          if (refreshedAccessToken && refreshedAccessToken !== staleAccessToken) {
            return refreshedAccessToken
          }
        }
      }
      throw error
    }
  }

  if (typeof navigator !== 'undefined' && navigator.locks?.request) {
    return navigator.locks.request('university-auth-token-refresh', refresh)
  }
  return refresh()
}

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    config._accessToken = token
    config._authSessionId = getAuthSessionId()
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const method = response.config.method?.toLowerCase()
    if (['post', 'put', 'patch', 'delete'].includes(method)) notifyDataChanged()
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const requestUrl = originalRequest?.url || ''
    const isAuthEndpoint = ['/auth/login/', '/auth/logout/', '/auth/token/refresh/'].some((path) => requestUrl.includes(path))
    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry || isAuthEndpoint) {
      return Promise.reject(error)
    }
    if (!originalRequest._authSessionId || getAuthSessionId() !== originalRequest._authSessionId) {
      return Promise.reject(sessionChangedError())
    }

    originalRequest._retry = true
    let refreshRequest = refreshRequests.get(originalRequest._authSessionId)
    if (!refreshRequest) {
      refreshRequest = requestRefreshedAccessToken(originalRequest._accessToken, originalRequest._authSessionId)
        .catch((refreshError) => {
          if (refreshError.sessionChanged) {
            return Promise.reject(refreshError)
          }
          if (refreshError.sessionExpired || [400, 401].includes(refreshError.response?.status)) {
            expireSession(originalRequest._authSessionId)
          } else {
            reportVerificationFailure(originalRequest._authSessionId)
          }
          throw refreshError
        })
        .finally(() => {
          refreshRequests.delete(originalRequest._authSessionId)
        })
      refreshRequests.set(originalRequest._authSessionId, refreshRequest)
    }

    try {
      const accessToken = await refreshRequest
      originalRequest.headers.Authorization = `Bearer ${accessToken}`
      return await api(originalRequest)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  },
)

export default api

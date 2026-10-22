import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const ThemeContext = createContext(null)

function getStoredTheme() {
  return localStorage.getItem('university-portal-theme') === 'dark' ? 'dark' : 'light'
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getStoredTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('university-portal-theme', theme)
  }, [theme])

  const toggleTheme = useCallback((nextTheme) => {
    setTheme(nextTheme)
  }, [])

  const value = useMemo(() => ({ theme, setTheme: toggleTheme }), [theme, toggleTheme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme doit être utilisé dans ThemeProvider.')
  return context
}

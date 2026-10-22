import { useEffect, useRef } from 'react'

const DATA_CHANGED_EVENT = 'university:data-changed'
const DATA_CHANGED_KEY = 'university:data-changed-at'
const REFRESH_INTERVAL = 8000

let channel

function getChannel() {
  if (typeof BroadcastChannel === 'undefined') return null
  if (!channel) channel = new BroadcastChannel('university-data-sync')
  return channel
}

export function notifyDataChanged() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(DATA_CHANGED_EVENT))
  getChannel()?.postMessage({ type: DATA_CHANGED_EVENT })
  try {
    localStorage.setItem(DATA_CHANGED_KEY, String(Date.now()))
  } catch {
    // Cross-tab notifications are best-effort when browser storage is unavailable.
  }
}

export function useAutoRefresh(refresh, interval = REFRESH_INTERVAL) {
  const refreshRef = useRef(refresh)
  const runningRef = useRef(false)

  useEffect(() => {
    refreshRef.current = refresh
  }, [refresh])

  useEffect(() => {
    let debounceTimer
    const runRefresh = async () => {
      if (runningRef.current || document.visibilityState === 'hidden') return
      runningRef.current = true
      try {
        await refreshRef.current()
      } finally {
        runningRef.current = false
      }
    }
    const scheduleRefresh = () => {
      window.clearTimeout(debounceTimer)
      debounceTimer = window.setTimeout(runRefresh, 250)
    }
    const onStorage = (event) => {
      if (event.key === DATA_CHANGED_KEY) scheduleRefresh()
    }
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') scheduleRefresh()
    }
    const onChannelMessage = (event) => {
      if (event.data?.type === DATA_CHANGED_EVENT) scheduleRefresh()
    }
    const broadcastChannel = getChannel()
    const timer = window.setInterval(runRefresh, interval)
    window.addEventListener(DATA_CHANGED_EVENT, scheduleRefresh)
    window.addEventListener('storage', onStorage)
    document.addEventListener('visibilitychange', onVisibilityChange)
    broadcastChannel?.addEventListener('message', onChannelMessage)

    return () => {
      window.clearInterval(timer)
      window.clearTimeout(debounceTimer)
      window.removeEventListener(DATA_CHANGED_EVENT, scheduleRefresh)
      window.removeEventListener('storage', onStorage)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      broadcastChannel?.removeEventListener('message', onChannelMessage)
    }
  }, [interval])
}

import api from '../services/api'

export async function fetchPrivateFile(url) {
  const { data } = await api.get(url, { responseType: 'blob' })
  return data
}

export async function downloadPrivateFile(url, suggestedName = 'document') {
  const data = await fetchPrivateFile(url)
  const objectUrl = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = suggestedName
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

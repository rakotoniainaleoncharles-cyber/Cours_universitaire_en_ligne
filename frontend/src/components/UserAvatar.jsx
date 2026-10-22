import { useEffect, useState } from 'react'
import { UserRound } from 'lucide-react'
import api from '../services/api'

export default function UserAvatar({ src = '', name = '', className = '' }) {
  const [imageUrl, setImageUrl] = useState('')

  useEffect(() => {
    let active = true
    let objectUrl = ''
    if (!src) {
      setImageUrl('')
      return undefined
    }

    const apiPath = src.replace(/^\/api(?=\/)/, '')
    api.get(apiPath, { responseType: 'blob' })
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data)
        if (active) setImageUrl(objectUrl)
        else URL.revokeObjectURL(objectUrl)
      })
      .catch(() => {
        if (active) setImageUrl('')
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [src])

  return (
    <span className={`profile-avatar ${className}`.trim()}>
      {imageUrl ? <img src={imageUrl} alt={name ? `Photo de ${name}` : 'Photo de profil'} /> : (
        name ? <span aria-hidden="true">{name.trim().charAt(0).toUpperCase()}</span> : <UserRound size={18} aria-hidden="true" />
      )}
    </span>
  )
}

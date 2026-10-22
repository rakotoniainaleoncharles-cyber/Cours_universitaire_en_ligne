import { useCallback, useEffect, useRef, useState } from 'react'
import { BookOpen, GraduationCap, Heart, ImagePlus, MessageCircle, Send, Megaphone, X } from 'lucide-react'
import api from '../services/api'
import { useAutoRefresh } from '../utils/dataSync'
import UserAvatar from './UserAvatar'
import { useAuth } from '../context/AuthContext'

function messageFrom(error) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const value = Object.values(data).flat().find((item) => typeof item === 'string')
    if (value) return value
  }
  return 'La requête n’a pas abouti. Vérifiez la connexion et réessayez.'
}

const kindLabels = { admin: 'Administration', teacher: 'Professeur', course: 'Cours', subject: 'Matière' }

export default function SocialFeed({ admin = false }) {
  const { user } = useAuth()
  const isAdmin = admin || user?.role === 'admin'
  const canCreatePost = isAdmin || user?.role === 'teacher'
  const [posts, setPosts] = useState([])
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [mediaFile, setMediaFile] = useState(null)
  const [mediaPreview, setMediaPreview] = useState('')
  const [postMedia, setPostMedia] = useState({})
  const [mediaError, setMediaError] = useState('')
  const [loadingVideoId, setLoadingVideoId] = useState(null)
  const mediaObjectUrls = useRef(new Map())
  const [comments, setComments] = useState({})
  const [replies, setReplies] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadPosts = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/social-posts/')
      setPosts(data)
    } catch (loadError) {
      setError(messageFrom(loadError))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPosts()
  }, [loadPosts])
  useAutoRefresh(() => loadPosts({ silent: true }))

  useEffect(() => {
    if (!mediaFile) {
      setMediaPreview('')
      return undefined
    }
    const previewUrl = URL.createObjectURL(mediaFile)
    setMediaPreview(previewUrl)
    return () => URL.revokeObjectURL(previewUrl)
  }, [mediaFile])

  useEffect(() => {
    let active = true
    setMediaError('')
    const loadPostMedia = async () => {
      const entries = await Promise.all(posts.filter((post) => (
        post.image_url && !mediaObjectUrls.current.has(post.id)
      )).map(async (post) => {
        try {
          const apiPath = post.image_url.replace(/^\/api(?=\/)/, '')
          const { data } = await api.get(apiPath, { responseType: 'blob' })
          const url = URL.createObjectURL(data)
          if (!active) {
            URL.revokeObjectURL(url)
            return [post.id, '']
          }
          mediaObjectUrls.current.set(post.id, url)
          return [post.id, { url, type: 'image' }]
        } catch (loadError) {
          if (active) setMediaError(`Impossible de charger un média de publication. ${messageFrom(loadError)}`)
          return [post.id, null]
        }
      }))
      if (active) setPostMedia((current) => ({
        ...current,
        ...Object.fromEntries(entries.filter(([, media]) => media)),
      }))
    }
    loadPostMedia()
    return () => {
      active = false
    }
  }, [posts])

  useEffect(() => () => {
    mediaObjectUrls.current.forEach((url) => URL.revokeObjectURL(url))
    mediaObjectUrls.current.clear()
  }, [])

  const createPost = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const formData = new FormData()
      formData.append('title', title)
      formData.append('content', content)
      if (mediaFile) {
        const isVideo = mediaFile.type.startsWith('video/') || /\.(mp4|webm)$/i.test(mediaFile.name)
        formData.append(isVideo ? 'video' : 'image', mediaFile)
      }
      await api.post('/social-posts/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setTitle('')
      setContent('')
      setMediaFile(null)
      setNotice('La publication a été partagée avec les professeurs et les étudiants.')
      await loadPosts()
    } catch (saveError) {
      setError(messageFrom(saveError))
    } finally {
      setSaving(false)
    }
  }

  const loadVideo = async (post) => {
    setLoadingVideoId(post.id)
    setMediaError('')
    try {
      const apiPath = post.video_url.replace(/^\/api(?=\/)/, '')
      const { data } = await api.get(apiPath, { responseType: 'blob' })
      const url = URL.createObjectURL(data)
      mediaObjectUrls.current.set(post.id, url)
      setPostMedia((current) => ({ ...current, [post.id]: { url, type: 'video' } }))
    } catch (loadError) {
      setMediaError(`Impossible de charger la vidéo. ${messageFrom(loadError)}`)
    } finally {
      setLoadingVideoId(null)
    }
  }

  const toggleLike = async (post) => {
    setError('')
    try {
      const { data } = await api.post(`/social-posts/${post.id}/like/`)
      setPosts((current) => current.map((item) => item.id === data.id ? data : item))
    } catch (likeError) {
      setError(messageFrom(likeError))
    }
  }

  const addComment = async (event, post) => {
    event.preventDefault()
    const comment = (comments[post.id] || '').trim()
    if (!comment) return
    setError('')
    try {
      const { data } = await api.post(`/social-posts/${post.id}/comments/`, { content: comment })
      setComments((current) => ({ ...current, [post.id]: '' }))
      setPosts((current) => current.map((item) => (
        item.id === post.id ? { ...item, comments: [...item.comments, data] } : item
      )))
    } catch (commentError) {
      setError(messageFrom(commentError))
    }
  }

  const addReply = async (event, post, comment) => {
    event.preventDefault()
    const content = (replies[comment.id] || '').trim()
    if (!content) return
    setError('')
    try {
      const { data } = await api.post(
        `/social-posts/${post.id}/comments/${comment.id}/replies/`,
        { content },
      )
      setReplies((current) => ({ ...current, [comment.id]: '' }))
      setPosts((current) => current.map((item) => item.id === post.id ? {
        ...item,
        comments: item.comments.map((entry) => (
          entry.id === comment.id ? { ...entry, replies: [...entry.replies, data] } : entry
        )),
      } : item))
    } catch (replyError) {
      setError(messageFrom(replyError))
    }
  }

  return (
    <section className="social-feed" aria-label="Fil d’actualités">
      <header className="social-feed-heading">
        <span><Megaphone size={18} /></span>
        <div><h3>{isAdmin ? 'Publications et actualités' : 'Actualités de l’université'}</h3>
          <p>Les nouvelles partagées avec les professeurs et les étudiants.</p></div>
      </header>

      {canCreatePost && (
        <form className="social-compose" onSubmit={createPost}>
          <label className="input-group"><span>Titre de la publication</span>
            <input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex. Information importante" />
          </label>
          <label className="input-group"><span>Votre actualité</span>
            <textarea required rows={4} value={content} onChange={(event) => setContent(event.target.value)} placeholder="Partagez une nouvelle avec les professeurs et les étudiants..." />
          </label>
          <label className="social-image-picker">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,.mp4,.webm"
              onChange={(event) => setMediaFile(event.target.files?.[0] || null)}
            />
            <ImagePlus size={17} /> Ajouter une image (5 Mo) ou une vidéo MP4/WebM (50 Mo)
          </label>
          {mediaPreview && mediaFile?.type.startsWith('image/') && (
            <div className="social-image-preview">
              <img src={mediaPreview} alt="Aperçu de l’image de la publication" />
              <button type="button" className="icon-button" aria-label="Retirer le média" onClick={() => setMediaFile(null)}><X size={16} /></button>
            </div>
          )}
          {mediaPreview && mediaFile?.type.startsWith('video/') && (
            <div className="social-image-preview">
              <video src={mediaPreview} controls preload="metadata" aria-label="Aperçu de la vidéo" />
              <button type="button" className="icon-button" aria-label="Retirer la vidéo" onClick={() => setMediaFile(null)}><X size={16} /></button>
            </div>
          )}
          <div className="social-compose-actions">
            {notice && <span role="status">{notice}</span>}
            <button type="submit" className="primary-button" disabled={saving}><Send size={16} /> {saving ? 'Publication...' : 'Publier'}</button>
          </div>
        </form>
      )}

      {error && <div className="error-message" role="alert">{error}</div>}
      {mediaError && <div className="error-message" role="alert">{mediaError}</div>}
      {loading ? <p className="teacher-empty">Chargement des actualités...</p> : posts.length ? (
        <div className="social-post-list">
          {posts.map((post) => (
            <article className="social-post" key={post.id}>
              <header className="social-post-header">
                <UserAvatar className="social-post-avatar" src={post.author_avatar_url} name={post.author_name || 'Administration'} />
                <div><strong>{post.author_name}</strong><small>{new Date(post.created_at).toLocaleString('fr-FR')}</small></div>
                <span className={`social-post-kind ${post.kind}`}>{kindLabels[post.kind] || 'Actualité'}</span>
              </header>
              <div className="social-post-body">
                <h4>{post.title}</h4>
                {(post.course_title || post.subject_name) && (
                  <p className="social-post-context">
                    {post.course_title && <span><BookOpen size={14} /> {post.course_title}</span>}
                    {post.subject_name && <span><GraduationCap size={14} /> {post.subject_name}</span>}
                  </p>
                )}
                <p className="social-post-content">{post.content}</p>
                {post.image_url && postMedia[post.id]?.type === 'image' && (
                  <img className="social-post-image" src={postMedia[post.id].url} alt={post.title} loading="lazy" />
                )}
                {post.video_url && postMedia[post.id]?.type === 'video' ? (
                  <video className="social-post-image" src={postMedia[post.id].url} controls preload="metadata" aria-label={post.title} />
                ) : post.video_url && (
                  <button type="button" className="social-video-load" disabled={loadingVideoId === post.id} onClick={() => loadVideo(post)}>
                    {loadingVideoId === post.id ? 'Chargement de la vidéo...' : 'Charger et lire la vidéo'}
                  </button>
                )}
              </div>
              <footer className="social-post-actions">
                <button type="button" className={post.liked_by_me ? 'liked' : ''} onClick={() => toggleLike(post)} aria-pressed={post.liked_by_me}>
                  <Heart size={17} fill={post.liked_by_me ? 'currentColor' : 'none'} /> J’aime <span>{post.like_count}</span>
                </button>
                <span><MessageCircle size={17} /> {post.comments.reduce((count, comment) => count + 1 + (comment.replies?.length || 0), 0)} commentaire(s)</span>
              </footer>
              {post.comments.length > 0 && (
                <ul className="social-comment-list">
                  {post.comments.map((comment) => (
                    <li key={comment.id}>
                      <span className="social-comment-author"><UserAvatar src={comment.author_avatar_url} name={comment.author_name} /><strong>{comment.author_name}</strong></span>
                      <span>{comment.content}</span>
                      <small>{new Date(comment.created_at).toLocaleString('fr-FR')}</small>
                      {comment.replies?.map((reply) => (
                        <div className="social-comment-reply" key={reply.id}>
                          <span className="social-comment-author"><UserAvatar src={reply.author_avatar_url} name={reply.author_name} /><strong>{reply.author_name}</strong></span>
                          <span>{reply.content}</span>
                          <small>{new Date(reply.created_at).toLocaleString('fr-FR')}</small>
                        </div>
                      ))}
                      {isAdmin && (
                        <form className="social-comment-form social-reply-form" onSubmit={(event) => addReply(event, post, comment)}>
                          <input
                            aria-label={`Répondre au commentaire de ${comment.author_name}`}
                            maxLength={2000}
                            placeholder="Répondre à ce commentaire..."
                            value={replies[comment.id] || ''}
                            onChange={(event) => setReplies((current) => ({ ...current, [comment.id]: event.target.value }))}
                          />
                          <button type="submit" className="secondary-button" disabled={!(replies[comment.id] || '').trim()}><Send size={15} /><span>Répondre</span></button>
                        </form>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <form className="social-comment-form" onSubmit={(event) => addComment(event, post)}>
                <input
                  aria-label={`Commenter ${post.title}`}
                  maxLength={2000}
                  placeholder="Écrire un commentaire..."
                  value={comments[post.id] || ''}
                  onChange={(event) => setComments((current) => ({ ...current, [post.id]: event.target.value }))}
                />
                <button type="submit" className="secondary-button" disabled={!(comments[post.id] || '').trim()}><Send size={15} /><span>Commenter</span></button>
              </form>
            </article>
          ))}
        </div>
      ) : <p className="teacher-no-items">Aucune actualité pour le moment.</p>}
    </section>
  )
}

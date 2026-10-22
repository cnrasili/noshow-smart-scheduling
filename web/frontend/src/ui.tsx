import { useEffect, type ReactNode } from 'react'
import { usePageTitle } from './title'

export interface NoticeState {
  kind: 'success' | 'error'
  text: string
}

const SUCCESS_VISIBLE_MS = 4000

export function Notice({ notice, onClose }: { notice: NoticeState | null; onClose: () => void }) {
  // Success messages fade on their own; errors stay until closed
  useEffect(() => {
    if (notice?.kind !== 'success') return
    const timer = setTimeout(onClose, SUCCESS_VISIBLE_MS)
    return () => clearTimeout(timer)
  }, [notice, onClose])

  if (!notice) return null
  return (
    <div
      className={`notice notice-${notice.kind}`}
      role={notice.kind === 'error' ? 'alert' : 'status'}
    >
      <span>{notice.text}</span>
      <button type="button" className="notice-close" onClick={onClose} aria-label="Kapat">
        ×
      </button>
    </div>
  )
}

/** Page heading in the main area; also names the browser tab. */
export function PageTop({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: ReactNode
}) {
  usePageTitle(title)
  return (
    <div className="top">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children}
    </div>
  )
}

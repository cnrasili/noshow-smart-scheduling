import { useEffect, type ReactNode } from 'react'

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

export type Tone = 'neutral' | 'info' | 'ok' | 'warn' | 'miss'

export function Status({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`status status-${tone}`}>{children}</span>
}

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {children}
    </div>
  )
}

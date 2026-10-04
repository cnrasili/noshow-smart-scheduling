import { useEffect } from 'react'

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

export function AttendanceBadge({ attended }: { attended: boolean | null }) {
  if (attended === true) return <span className="badge badge-ok">Geldi</span>
  if (attended === false) return <span className="badge badge-miss">Gelmedi</span>
  return <span className="badge">İşaretlenmedi</span>
}

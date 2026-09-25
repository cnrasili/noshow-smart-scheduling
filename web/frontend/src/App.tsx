import { useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Status = 'checking' | 'ok' | 'unreachable'

function App() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    // Backend health check
    fetch(`${API_URL}/health`)
      .then((res) => setStatus(res.ok ? 'ok' : 'unreachable'))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <main className="app">
      <h1>Outpatient Appointment System</h1>
      <p>
        Backend status: <span className={`status status-${status}`}>{status}</span>
      </p>
    </main>
  )
}

export default App

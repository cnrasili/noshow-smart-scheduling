import { useOutletContext } from 'react-router'
import type { Me } from '../../types'

/** "Giriş yapan" box at the top of the patient's side panel. */
export function PatientWho() {
  const me = useOutletContext<Me>()
  return (
    <p className="who">
      Giriş yapan
      <b>{me.name}</b>
    </p>
  )
}

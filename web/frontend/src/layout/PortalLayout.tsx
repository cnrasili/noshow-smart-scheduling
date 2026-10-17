import { NavLink, Outlet } from 'react-router'
import { DEPARTMENT_NAME, INSTITUTION_NAME } from '../config'
import { PATHS } from '../routes'
import type { Me, Role } from '../types'

const PORTAL: Record<Role, { name: string; menu: { to: string; label: string }[] }> = {
  patient: {
    name: 'Hasta portalı',
    menu: [
      { to: PATHS.booking, label: 'Randevu al' },
      { to: PATHS.appointments, label: 'Randevularım' },
    ],
  },
  department: {
    name: 'Departman paneli',
    menu: [
      { to: PATHS.panel, label: 'Bugünkü program' },
      { to: PATHS.schedule, label: 'Çalışma takvimi' },
    ],
  },
}

/** Name shown for the signed-in account: the patient number, or the department. */
const displayName = (me: Me) => (me.role === 'department' ? DEPARTMENT_NAME : me.name)

/**
 * Frame of the patient portal and the department panel: a ribbon with the account, the menu
 * rail, and the page, which fills the main area and the side panel.
 */
export function PortalLayout({ me, onSignOut }: { me: Me; onSignOut: () => void }) {
  const portal = PORTAL[me.role]
  return (
    <div className="portal" data-role={me.role}>
      <div className="ribbon">
        <span>{INSTITUTION_NAME} randevu sistemi</span>
        <span>
          Giriş: <b>{displayName(me)}</b>{' '}
          <button type="button" onClick={onSignOut}>
            Çıkış
          </button>
        </span>
      </div>
      <div className="shell">
        <nav className="rail" aria-label="Menü">
          <div className="brand">
            {INSTITUTION_NAME}
            <small>{portal.name}</small>
          </div>
          {portal.menu.map((item) => (
            <NavLink key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <Outlet context={me} />
      </div>
    </div>
  )
}

import { NavLink } from 'react-router-dom'
import { IconChart, IconTicket } from './Icons'
import { Logo } from './ui'

const liens = [
  { to: '/', label: 'Billets', icon: IconTicket },
  { to: '/admin', label: 'Tableau de bord', icon: IconChart },
]

export default function Navbar() {
  return (
    <header className="no-print sticky top-0 z-40 border-b border-line/70 bg-ink/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <NavLink to="/" aria-label="Accueil">
          <Logo />
        </NavLink>
        <nav className="flex gap-1">
          {liens.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? 'bg-gold/10 text-gold-light' : 'text-muted hover:bg-surface-2 hover:text-cream'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}

import { useEffect, useState } from 'react'
import { api, staffCode } from '../lib/api'
import { IconLock, IconLogout } from './Icons'
import { btn, input, Spinner } from './ui'

/** Réserve une page au personnel (code d'accès vérifié par le backend). */
export default function StaffGate({ titre, children }) {
  const [code, setCode] = useState(staffCode.get)
  const [saisie, setSaisie] = useState('')
  const [erreur, setErreur] = useState('')
  const [chargement, setChargement] = useState(false)

  useEffect(() => {
    const sync = () => setCode(staffCode.get())
    window.addEventListener('staff:change', sync)
    return () => window.removeEventListener('staff:change', sync)
  }, [])

  async function connecter(e) {
    e.preventDefault()
    setChargement(true)
    setErreur('')
    try {
      await api.login(saisie)
      staffCode.set(saisie)
    } catch (err) {
      setErreur(err.status === 401 ? 'Code incorrect.' : err.message)
    } finally {
      setChargement(false)
    }
  }

  if (code) {
    return (
      <>
        {children}
        <div className="no-print mx-auto max-w-6xl px-4 pb-8 text-right">
          <button onClick={() => staffCode.set('')} className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-cream">
            <IconLogout className="h-3.5 w-3.5" /> Verrouiller l'accès
          </button>
        </div>
      </>
    )
  }

  return (
    <main className="grid min-h-[75vh] place-items-center px-4">
      <form onSubmit={connecter} className="w-full max-w-sm animate-fade-in rounded-2xl border border-line bg-surface p-7 text-center">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-full border border-gold/30 bg-gold/10 text-gold">
          <IconLock />
        </span>
        <h1 className="mt-4 font-display text-2xl font-bold">{titre}</h1>
        <p className="mt-1 text-sm text-muted">Espace réservé à l'équipe de l'événement.</p>
        <input
          type="password"
          autoFocus
          value={saisie}
          onChange={(e) => setSaisie(e.target.value)}
          placeholder="Code d'accès"
          className={`${input} mt-6 text-center tracking-[0.3em]`}
        />
        {erreur && <p className="mt-3 text-sm text-red-400">{erreur}</p>}
        <button disabled={!saisie || chargement} className={`${btn.gold} mt-4 w-full`}>
          {chargement ? <Spinner className="h-5 w-5" /> : 'Déverrouiller'}
        </button>
      </form>
    </main>
  )
}

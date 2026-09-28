import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconScan, IconSearch } from '../components/Icons'
import PaiementsAVerifier from '../components/PaiementsAVerifier'
import { btn, ErrorState, PageLoader, input } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateCourte, dateEvenement, formatPrix, numeroFormat } from '../lib/format'

const FILTRES = [
  { id: 'tous', label: 'Tous' },
  { id: 'vendu', label: 'Vendus' },
  { id: 'utilise', label: 'Scannés' },
  { id: 'disponible', label: 'Disponibles' },
]

const BADGE = {
  disponible: 'border-line text-muted',
  vendu: 'border-gold/40 text-gold-light',
  utilise: 'border-emerald-500/40 text-emerald-300',
}
const LIBELLE = { disponible: 'Disponible', vendu: 'Vendu', utilise: 'Scanné' }

function Stat({ label, valeur, detail, accent = 'text-cream' }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5">
      <p className="text-xs font-medium uppercase tracking-[0.15em] text-muted">{label}</p>
      <p className={`mt-2 font-display text-4xl font-bold tabular-nums ${accent}`}>{valeur}</p>
      {detail && <p className="mt-1 text-xs text-muted">{detail}</p>}
    </div>
  )
}

export default function Admin() {
  const [filtre, setFiltre] = useState('tous')
  const [recherche, setRecherche] = useState('')
  const [q, setQ] = useState('')
  const [copie, setCopie] = useState(false)

  // Recherche envoyée au serveur après une courte pause de frappe
  useEffect(() => {
    const t = setTimeout(() => setQ(recherche.trim()), 300)
    return () => clearTimeout(t)
  }, [recherche])

  const stats = usePolling(api.stats, [], 4000)
  const liste = usePolling(() => api.tickets(filtre, q), [filtre, q], 4000)

  if (stats.error && !stats.data) return <ErrorState message={stats.error.message} />
  if (!stats.data) return <PageLoader />

  const { evenement: ev, stats: s } = stats.data
  const tickets = liste.data?.tickets ?? []
  const pct = (n) => `${(n / s.total) * 100}%`

  // Lien du scanner à transmettre aux contrôleurs (sur le réseau local, remplacer localhost par l'IP du PC)
  const lienScan = `${window.location.origin}/scan`
  async function copierLienScan() {
    try {
      await navigator.clipboard.writeText(lienScan)
      setCopie(true)
      setTimeout(() => setCopie(false), 2000)
    } catch {
      prompt('Lien du scanner :', lienScan)
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gold">Tableau de bord</p>
          <h1 className="mt-1 font-display text-3xl font-bold">{ev.artiste}</h1>
          <p className="text-sm text-muted">{dateEvenement(ev.date).longue} · {ev.lieu}, {ev.ville}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={copierLienScan} className={`${btn.ghost} py-2 text-sm`}><IconScan className="h-4 w-4" /> {copie ? 'Lien copié' : 'Copier le lien du scanner'}</button>
          <a href="/django-admin/" target="_blank" rel="noreferrer" className={`${btn.ghost} py-2 text-sm`}>Admin Django</a>
        </div>
      </div>

      <PaiementsAVerifier onChange={() => { stats.reload(); liste.reload() }} />

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Capacité" valeur={s.total} />
        <Stat label="Vendus" valeur={s.vendus} detail={`Recette : ${formatPrix(s.recette)}`} accent="text-gold-light" />
        <Stat label="Entrées" valeur={s.scannes} detail={s.vendus ? `${Math.round((s.scannes / s.vendus) * 100)} % des billets vendus` : null} accent="text-emerald-300" />
        <Stat label="Restants" valeur={s.restants} detail={`${Math.round((s.restants / s.total) * 100)} % de la jauge`} />
      </div>

      <div className="mt-4 rounded-2xl border border-line bg-surface p-5">
        <div className="flex justify-between text-sm">
          <span className="font-medium">Remplissage</span>
          <span className="tabular-nums text-muted">{Math.round((s.vendus / s.total) * 100)} % vendus</span>
        </div>
        <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-line">
          <div className="bg-emerald-400 transition-all duration-700" style={{ width: pct(s.scannes) }} />
          <div className="bg-gradient-gold transition-all duration-700" style={{ width: pct(s.vendus - s.scannes) }} />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-emerald-400" />Entrés ({s.scannes})</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-gold" />Vendus, pas encore entrés ({s.vendus - s.scannes})</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-line ring-1 ring-muted/40" />Disponibles ({s.restants})</span>
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
          <div className="flex flex-wrap gap-1 rounded-xl bg-ink p-1">
            {FILTRES.map((f) => (
              <button
                key={f.id}
                onClick={() => setFiltre(f.id)}
                className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${filtre === f.id ? 'bg-gold/15 text-gold-light' : 'text-muted hover:text-cream'}`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <label className="relative w-full sm:w-72">
            <IconSearch className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="Nom, téléphone ou n°" className={`${input} py-2.5 pl-10 text-sm`} />
          </label>
        </div>

        <div className="max-h-[60vh] overflow-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="sticky top-0 bg-surface-2 text-[11px] uppercase tracking-[0.15em] text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">N°</th>
                <th className="px-4 py-3 font-medium">Acheteur</th>
                <th className="px-4 py-3 font-medium">Statut</th>
                <th className="px-4 py-3 font-medium">Achat</th>
                <th className="px-4 py-3 font-medium">Entrée</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line/70">
              {tickets.map((t) => (
                <tr key={t.id} className="transition hover:bg-surface-2/60">
                  <td className="px-4 py-3 font-mono text-cream/80">{numeroFormat(t.numero, s.total)}</td>
                  <td className="px-4 py-3">
                    {t.acheteur_nom ? (
                      <>
                        <p className="font-medium">{t.acheteur_nom}</p>
                        <p className="text-xs text-muted">{t.acheteur_tel}</p>
                      </>
                    ) : (
                      <span className="text-muted/50">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${BADGE[t.statut]}`}>{LIBELLE[t.statut]}</span>
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">{dateCourte(t.date_achat)}</td>
                  <td className="px-4 py-3 tabular-nums text-muted">{dateCourte(t.date_scan)}</td>
                  <td className="px-4 py-3 text-right">
                    {t.statut !== 'disponible' && (
                      <Link to={`/billet/${t.id}`} className="text-xs font-semibold text-gold hover:text-gold-light">Voir le billet</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {liste.data && tickets.length === 0 && <p className="p-10 text-center text-sm text-muted">Aucun billet.</p>}
        </div>
        <p className="border-t border-line px-4 py-2.5 text-xs text-muted">{tickets.length} billet(s)</p>
      </div>
    </main>
  )
}

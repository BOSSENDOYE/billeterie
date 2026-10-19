import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconScan, IconSearch } from '../components/Icons'
import PaiementsAVerifier from '../components/PaiementsAVerifier'
import VenteGuichet from '../components/VenteGuichet'
import BilletsPapier from '../components/BilletsPapier'
import { btn, ErrorState, Logo, PageLoader, input } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateCourte, dateEvenement, formatPrix } from '../lib/format'
import { typeBillet } from '../lib/typesBillet'

const FILTRES = [
  { id: 'tous', label: 'Tous' },
  { id: 'vendu', label: 'Vendus' },
  { id: 'utilise', label: 'Scannés' },
  { id: 'disponible', label: 'Disponibles' },
]

const FILTRES_TYPE = [
  { id: 'tous', label: 'Tous types' },
  { id: 'prevente', label: 'Prévente' },
  { id: 'jour_j', label: 'Jour J' },
]

const BADGE = {
  disponible: 'border-line text-muted',
  vendu: 'border-gold/40 text-gold-light',
  utilise: 'border-emerald-500/40 text-emerald-300',
}
const LIBELLE = { disponible: 'Disponible', vendu: 'Vendu', utilise: 'Scanné' }

/** Remplissage d'une série (prévente ou Jour J). */
function Serie({ type, serie }) {
  const th = typeBillet(type)
  const pct = (n) => `${(n / serie.total) * 100}%`
  return (
    <div className={`rounded-2xl border bg-surface p-5 ${th.bordure}`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold tracking-[0.2em] ${th.badge}`}>{th.bandeau}</span>
        <span className="text-sm text-muted">{formatPrix(serie.prix)}</span>
      </div>
      <p className="mt-3 font-display text-3xl font-bold tabular-nums">
        {serie.vendus}<span className="text-lg text-muted"> / {serie.total} {serie.physiques > 0 ? 'imprimés' : 'vendus'}</span>
      </p>
      <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-line">
        <div className="bg-emerald-400 transition-all duration-700" style={{ width: pct(serie.scannes) }} />
        <div className={`transition-all duration-700 ${type === 'jour_j' ? 'bg-gradient-ruby' : 'bg-gradient-gold'}`} style={{ width: pct(serie.vendus - serie.scannes) }} />
      </div>
      <div className="mt-3 flex flex-wrap justify-between gap-2 text-xs text-muted">
        <span>{serie.scannes} entrés · {serie.restants} restants</span>
        <span className={th.accentClair}>{formatPrix(serie.recette)}</span>
      </div>
    </div>
  )
}

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
  const [filtreType, setFiltreType] = useState('tous')
  const [recherche, setRecherche] = useState('')
  const [q, setQ] = useState('')
  const [copie, setCopie] = useState(false)

  // Recherche envoyée au serveur après une courte pause de frappe
  useEffect(() => {
    const t = setTimeout(() => setQ(recherche.trim()), 300)
    return () => clearTimeout(t)
  }, [recherche])

  const stats = usePolling(api.stats, [], 4000)
  const liste = usePolling(() => api.tickets(filtre, q, filtreType), [filtre, q, filtreType], 4000)

  if (stats.error && !stats.data) return <ErrorState message={stats.error.message} />
  if (!stats.data) return <PageLoader />

  const { evenement: ev, stats: s } = stats.data
  const tickets = liste.data?.tickets ?? []

  async function reinitialiser(t) {
    const effet = t.physique
      ? 'Le billet papier redevient valide (son entrée est annulée).'
      : "Le billet redevient disponible à la vente : l'acheteur ne pourra plus l'utiliser."
    if (!confirm(`Réinitialiser le billet ${t.code} (${t.acheteur_nom ?? ''}) ?\n\n${effet}`)) return
    try {
      await api.reinitialiserTicket(t.id)
      stats.reload()
      liste.reload()
    } catch (e) {
      alert(e.message)
    }
  }

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
    <main className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-6 border-b border-line pb-4">
        <Logo />
      </div>
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
        <Stat label="Capacité" valeur={s.total} detail={`${ev.quota_prevente} prévente + ${ev.quota_jour_j} Jour J`} />
        <Stat label="Vendus" valeur={s.vendus} detail={`Recette : ${formatPrix(s.recette)}`} accent="text-gold-light" />
        <Stat label="Entrées" valeur={s.scannes} detail={s.vendus ? `${Math.round((s.scannes / s.vendus) * 100)} % des billets vendus` : null} accent="text-emerald-300" />
        <Stat label="Restants" valeur={s.restants} detail={`${Math.round((s.restants / s.total) * 100)} % de la jauge`} />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {s.par_type && ['prevente', 'jour_j'].map((t) => <Serie key={t} type={t} serie={s.par_type[t]} />)}
      </div>

      {s.par_type && (
        <>
          <BilletsPapier type="prevente" evenement={ev} serie={s.par_type.prevente} onChange={() => { stats.reload(); liste.reload() }} />
          <BilletsPapier type="jour_j" evenement={ev} serie={s.par_type.jour_j} onChange={() => { stats.reload(); liste.reload() }} />
        </>
      )}

      <VenteGuichet evenement={ev} stats={s} onVente={() => { stats.reload(); liste.reload() }} />

      <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
          <div className="flex flex-wrap gap-2">
          <div className="flex flex-wrap gap-1 rounded-xl bg-ink p-1">
            {FILTRES_TYPE.map((f) => (
              <button
                key={f.id}
                onClick={() => setFiltreType(f.id)}
                className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${filtreType === f.id ? 'bg-gold/15 text-gold-light' : 'text-muted hover:text-cream'}`}
              >
                {f.label}
              </button>
            ))}
          </div>
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
                  <td className={`px-4 py-3 font-mono ${typeBillet(t.type).accentClair}`}>{t.code}</td>
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
                      <span className="flex justify-end gap-3">
                        <Link to={`/billet/${t.id}`} state={{ depuisAdmin: true }} className="text-xs font-semibold text-gold hover:text-gold-light">Voir</Link>
                        <button onClick={() => reinitialiser(t)} className="text-xs font-semibold text-muted hover:text-amber-300">Réinitialiser</button>
                      </span>
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

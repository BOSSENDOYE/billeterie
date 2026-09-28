import { Link, useLocation, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import ArtistePhoto from '../components/ArtistePhoto'
import { IconCheck, IconDownload } from '../components/Icons'
import { btn, ErrorState, PageLoader } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateCourte, dateEvenement, formatPrix, numeroFormat } from '../lib/format'

function Champ({ label, children, className = '' }) {
  return (
    <div className={`min-w-0 ${className}`}>
      <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-gold/80 sm:text-[10px]">{label}</p>
      <p className="truncate text-xs font-semibold text-cream sm:text-sm">{children}</p>
    </div>
  )
}

export default function Billet() {
  const { id } = useParams()
  const { state } = useLocation()
  // Rafraîchi pour afficher « Utilisé » dès que le billet est scanné à l'entrée
  const { data, error } = usePolling(() => api.ticket(id), [id], 5000)

  if (error && !data) {
    return <ErrorState message={error.status === 404 ? 'Billet introuvable.' : error.message} action={<Link to="/" className={btn.ghost}>Retour à la billetterie</Link>} />
  }
  if (!data) return <PageLoader />

  const { ticket, evenement: ev } = data
  const d = dateEvenement(ev.date)
  const utilise = ticket.statut === 'utilise'

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
      {state?.nouveau && (
        <div className="no-print mb-6 flex animate-fade-in items-center gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-emerald-500 text-ink"><IconCheck className="h-5 w-5" /></span>
          <div>
            <p className="font-semibold text-emerald-300">Paiement confirmé</p>
            <p className="text-sm text-cream/75">Conservez ce billet et présentez le QR code à l'entrée.</p>
          </div>
        </div>
      )}

      {/* Billet horizontal : partie principale + souche QR */}
      <article className="print-ticket relative flex animate-pop overflow-hidden rounded-2xl bg-gradient-gold p-px shadow-2xl shadow-gold/10 sm:rounded-3xl">
        <div className="flex w-full overflow-hidden rounded-[15px] bg-ink sm:rounded-[23px]">
          <div className="relative min-h-56 flex-1 overflow-hidden sm:min-h-80">
            <ArtistePhoto src={ev.image} alt={ev.artiste} />
            <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/80 to-ink/20" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink/90 via-transparent to-transparent" />
            {!utilise && (
              <div className="pointer-events-none absolute inset-y-0 w-1/3 animate-shine bg-gradient-to-r from-transparent via-gold-light/10 to-transparent" />
            )}

            <div className="relative flex h-full flex-col justify-between gap-4 p-4 sm:p-7">
              <p className="text-[9px] font-semibold uppercase tracking-[0.3em] text-gold sm:text-[11px]">E-billet · Entrée générale</p>

              <div>
                <h1 className="font-display text-2xl font-extrabold leading-none sm:text-5xl">
                  <span className="text-gradient-gold">{ev.artiste}</span>
                </h1>
                <p className="mt-1.5 text-xs text-cream/70 sm:text-sm">{ev.lieu} — {ev.ville}</p>
              </div>

              <div className="flex items-center gap-3 sm:gap-4">
                <div className="rounded-lg border border-gold/50 bg-ink/60 px-2.5 py-1.5 text-center leading-none backdrop-blur sm:rounded-xl sm:px-4 sm:py-2.5">
                  <p className="font-display text-xl font-bold text-gold-light sm:text-3xl">{d.jour}</p>
                  <p className="mt-0.5 text-[9px] font-bold tracking-widest text-cream sm:text-xs">{d.mois}</p>
                  <p className="text-[9px] text-muted sm:text-[10px]">{d.annee}</p>
                </div>
                <div className="grid flex-1 grid-cols-2 gap-x-3 gap-y-2">
                  <Champ label="Titulaire" className="col-span-2">{ticket.acheteur_nom}</Champ>
                  <Champ label="Heure">{d.heure}</Champ>
                  <Champ label="Prix">{formatPrix(ev.prix)}</Champ>
                </div>
              </div>
            </div>
          </div>

          {/* Perforation */}
          <div className="relative w-0">
            <div className="absolute -left-3 -top-3 h-6 w-6 rounded-full bg-ink ring-1 ring-gold/60" />
            <div className="absolute -bottom-3 -left-3 h-6 w-6 rounded-full bg-ink ring-1 ring-gold/60" />
            <div className="absolute inset-y-5 left-0 border-l border-dashed border-gold/40" />
          </div>

          {/* Souche */}
          <div className="flex w-32 shrink-0 flex-col items-center justify-center gap-2.5 bg-surface p-3 sm:w-56 sm:gap-4 sm:p-6">
            <div className="text-center">
              <p className="text-[9px] uppercase tracking-[0.2em] text-muted sm:text-[10px]">Billet N°</p>
              <p className="font-mono text-sm font-bold text-gold-light sm:text-lg">{numeroFormat(ticket.numero, ev.capacite)}</p>
            </div>
            <div className="relative w-full rounded-lg bg-white p-1.5 sm:rounded-xl sm:p-2.5">
              <QRCodeSVG value={ticket.qr} size={200} level="M" fgColor="#0A0A0B" className={`h-auto w-full ${utilise ? 'opacity-20' : ''}`} />
              {utilise && (
                <span className="absolute inset-0 grid place-items-center">
                  <span className="-rotate-12 rounded border-2 border-red-600 bg-white/80 px-1.5 text-[11px] font-black tracking-wider text-red-600 sm:border-[3px] sm:px-2 sm:text-base">UTILISÉ</span>
                </span>
              )}
            </div>
            {utilise ? (
              <span className="flex items-center gap-1.5 text-[10px] font-semibold text-red-400 sm:text-xs"><span className="h-1.5 w-1.5 rounded-full bg-red-500" />Utilisé</span>
            ) : (
              <span className="flex items-center gap-1.5 text-[10px] font-semibold text-emerald-400 sm:text-xs"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />Valide</span>
            )}
          </div>
        </div>
      </article>

      <dl className="mt-5 grid grid-cols-2 gap-4 rounded-2xl border border-line bg-surface p-5 text-sm sm:grid-cols-4">
        <div><dt className="text-xs text-muted">Téléphone</dt><dd className="mt-0.5 font-medium">+221 {ticket.acheteur_tel}</dd></div>
        <div><dt className="text-xs text-muted">Acheté le</dt><dd className="mt-0.5 font-medium">{dateCourte(ticket.date_achat)}</dd></div>
        <div><dt className="text-xs text-muted">Scanné le</dt><dd className="mt-0.5 font-medium">{dateCourte(ticket.date_scan)}</dd></div>
        <div><dt className="text-xs text-muted">Date</dt><dd className="mt-0.5 font-medium">{d.longue}</dd></div>
        <p className="col-span-full truncate font-mono text-[10px] text-muted/50">Réf. {ticket.id}</p>
      </dl>

      <div className="no-print mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
        <button onClick={() => window.print()} className={btn.gold}>
          <IconDownload /> Télécharger / imprimer le billet
        </button>
        <Link to="/" className={btn.ghost}>Acheter un autre billet</Link>
      </div>
    </main>
  )
}

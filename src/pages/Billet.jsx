import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import ArtistePhoto from '../components/ArtistePhoto'
import { IconCheck, IconDownload, IconQr } from '../components/Icons'
import { btn, ErrorState, PageLoader, Spinner } from '../components/ui'
import { enregistrerImageBillet, genererImageBillet } from '../lib/billetImage'
import { memoriserBillet } from '../lib/mesBillets'
import { api, usePolling } from '../lib/api'
import { dateCourte, dateEvenement, formatPrix } from '../lib/format'
import { typeBillet } from '../lib/typesBillet'

function Champ({ label, children, className = '', couleur = 'text-gold/80', tronquer = true }) {
  return (
    <div className={`min-w-0 ${className}`}>
      <p className={`text-[9px] font-semibold uppercase tracking-[0.2em] sm:text-[10px] ${couleur}`}>{label}</p>
      <p className={`text-xs font-semibold text-cream sm:text-sm ${tronquer ? 'truncate' : 'leading-tight'}`}>{children}</p>
    </div>
  )
}

/** QR en plein écran sur fond blanc : grand et contrasté pour le scanner de l'entrée. */
function QrPleinEcran({ ticket, onFermer }) {
  const th = typeBillet(ticket.type)
  const fermerRef = useRef(onFermer)
  fermerRef.current = onFermer
  useEffect(() => {
    let verrou
    navigator.wakeLock?.request('screen').then((v) => (verrou = v), () => {})
    const echap = (e) => e.key === 'Escape' && fermerRef.current()
    window.addEventListener('keydown', echap)
    return () => {
      verrou?.release().catch(() => {})
      window.removeEventListener('keydown', echap)
    }
  }, [])

  return (
    <button onClick={onFermer} className="fixed inset-0 z-[70] flex animate-fade-in flex-col items-center justify-center bg-white p-4 text-center text-ink">
      {/* Type de billet bien visible pour le contrôleur */}
      <span className={`absolute inset-x-0 top-0 block py-3 text-2xl font-black tracking-[0.3em] ${th.pleinEcran}`}>{th.bandeau}</span>
      <QRCodeSVG value={ticket.qr} size={512} level="M" marginSize={4} fgColor="#000000" bgColor="#FFFFFF" className="h-auto w-[min(92vw,70vh)]" />
      <span className="mt-4 block text-lg font-bold">{ticket.acheteur_nom}</span>
      <span className="block font-mono text-sm text-neutral-600">Billet N° {ticket.code}</span>
      <span className="mt-6 block max-w-xs text-sm text-neutral-500">Montez la luminosité de l'écran au maximum. Touchez pour fermer.</span>
    </button>
  )
}

export default function Billet() {
  const { id } = useParams()
  const { state } = useLocation()
  // Rafraîchi pour afficher « Utilisé » dès que le billet est scanné à l'entrée
  const { data, error } = usePolling(() => api.ticket(id), [id], 5000)
  const billetRef = useRef(null)
  const [enregistrement, setEnregistrement] = useState(false)
  const [message, setMessage] = useState(null)
  const [qrGrand, setQrGrand] = useState(false)
  const imageRef = useRef(null) // image du billet préparée à l'avance

  // Prépare l'image dès l'affichage (après l'animation d'entrée) et à chaque changement de statut
  const statut = data?.ticket.statut

  // Retient le billet sur ce téléphone (« Mes billets »), sauf s'il est ouvert depuis le tableau de bord
  useEffect(() => {
    if (data && !state?.depuisAdmin) memoriserBillet(data.ticket, data.evenement)
  }, [data, state])
  useEffect(() => {
    if (!statut) return
    imageRef.current = null
    let annule = false
    const t = setTimeout(async () => {
      try {
        const blob = await genererImageBillet(billetRef.current)
        if (!annule) imageRef.current = blob
      } catch {
        /* sera regénérée au clic */
      }
    }, 900)
    return () => {
      annule = true
      clearTimeout(t)
    }
  }, [statut])

  if (error && !data) {
    return <ErrorState message={error.status === 404 ? 'Billet introuvable.' : error.message} action={<Link to="/" className={btn.ghost}>Retour à la billetterie</Link>} />
  }
  if (!data) return <PageLoader />

  const { ticket, evenement: ev } = data
  const d = dateEvenement(ev.date)
  const utilise = ticket.statut === 'utilise'
  const th = typeBillet(ticket.type)

  const fermerQr = () => setQrGrand(false)

  async function enregistrer() {
    setMessage(null)
    const nom = `billet-${ticket.code.split('/')[0].toLowerCase()}-${ev.artiste.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.png`
    try {
      let blob = imageRef.current
      if (!blob) {
        setEnregistrement(true)
        blob = imageRef.current = await genererImageBillet(billetRef.current)
      }
      const r = await enregistrerImageBillet(blob, nom)
      if (r === 'telecharge') setMessage({ ok: true, texte: 'Billet téléchargé. Sur Android, il apparaît dans la Galerie (dossier Téléchargements).' })
    } catch (e) {
      setMessage({ ok: false, texte: e.message })
    } finally {
      setEnregistrement(false)
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
      {qrGrand && <QrPleinEcran ticket={ticket} onFermer={fermerQr} />}
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
      <article ref={billetRef} className={`print-ticket relative flex animate-pop overflow-hidden rounded-2xl p-px shadow-2xl sm:rounded-3xl ${th.cadre}`}>
        <div className="flex w-full overflow-hidden rounded-[15px] bg-ink sm:rounded-[23px]">
          <div className="relative min-h-56 min-w-0 flex-1 overflow-hidden sm:min-h-80">
            <ArtistePhoto src={ev.image} alt={ev.artiste} />
            <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/80 to-ink/20" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink/90 via-transparent to-transparent" />
            {th.teinte && <div className={`absolute inset-0 ${th.teinte}`} />}
            {!utilise && (
              <div className={`pointer-events-none absolute inset-y-0 w-1/3 animate-shine bg-gradient-to-r from-transparent ${th.reflet} to-transparent`} />
            )}

            <div className="relative flex h-full flex-col justify-between gap-4 p-4 sm:p-7">
              <p className={`text-[9px] font-semibold uppercase tracking-[0.3em] sm:text-[11px] ${th.accent}`}>E-billet · {th.label}</p>

              <div>
                <h1 className="break-words font-display text-[1.6rem] font-extrabold leading-[0.95] sm:text-5xl">
                  <span className={th.titre}>{ev.artiste}</span>
                </h1>
                <p className="mt-1.5 text-xs text-cream/70 sm:text-sm">{ev.lieu} — {ev.ville}</p>
              </div>

              <div className="flex items-center gap-3 sm:gap-4">
                <div className={`rounded-lg border bg-ink/60 ${th.bordure} px-2.5 py-1.5 text-center leading-none backdrop-blur sm:rounded-xl sm:px-4 sm:py-2.5`}>
                  <p className={`font-display text-xl font-bold sm:text-3xl ${th.accentClair}`}>{d.jour}</p>
                  <p className="mt-0.5 text-[9px] font-bold tracking-widest text-cream sm:text-xs">{d.mois}</p>
                  <p className="text-[9px] text-muted sm:text-[10px]">{d.annee}</p>
                </div>
                <div className="grid flex-1 grid-cols-2 gap-x-3 gap-y-2">
                  <Champ label="Titulaire" className="col-span-2" couleur={th.champ}>{ticket.acheteur_nom}</Champ>
                  <Champ label="Heure" couleur={th.champ}>{d.heure}</Champ>
                  <Champ label="Prix" couleur={th.champ} tronquer={false}>{formatPrix(ticket.prix)}</Champ>
                </div>
              </div>
            </div>
          </div>

          {/* Perforation */}
          <div className="relative w-0">
            <div className={`absolute -left-3 -top-3 h-6 w-6 rounded-full bg-ink ring-1 ${th.anneau}`} />
            <div className={`absolute -bottom-3 -left-3 h-6 w-6 rounded-full bg-ink ring-1 ${th.anneau}`} />
            <div className={`absolute inset-y-5 left-0 border-l border-dashed ${th.pointilles}`} />
          </div>

          {/* Souche */}
          <div className="relative flex w-32 shrink-0 flex-col items-center justify-center gap-2.5 bg-surface p-3 pt-9 sm:w-56 sm:gap-4 sm:p-6 sm:pt-14">
            <span className={`absolute inset-x-0 top-0 py-1.5 text-center text-[11px] font-black tracking-[0.25em] sm:py-2.5 sm:text-base ${th.ruban}`}>{th.bandeau}</span>
            <div className="text-center">
              <p className="text-[9px] uppercase tracking-[0.2em] text-muted sm:text-[10px]">Billet N°</p>
              <p className={`font-mono text-sm font-bold sm:text-lg ${th.accentClair}`}>{ticket.code}</p>
            </div>
            <div
              role="button"
              tabIndex={0}
              onClick={() => !utilise && setQrGrand(true)}
              onKeyDown={(e) => e.key === 'Enter' && !utilise && setQrGrand(true)}
              aria-label="Afficher le QR code en grand"
              className={`relative w-full rounded-lg bg-white p-0.5 sm:rounded-xl sm:p-1.5 ${utilise ? '' : 'cursor-zoom-in'}`}
            >
              <QRCodeSVG value={ticket.qr} size={200} level="M" marginSize={2} fgColor="#000000" bgColor="#FFFFFF" className={`h-auto w-full ${utilise ? 'opacity-20' : ''}`} />
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

      {!utilise && (
        <button onClick={() => setQrGrand(true)} className={`${btn.gold} no-print mt-5 w-full py-4 text-base`}>
          <IconQr /> Afficher mon QR code à l'entrée
        </button>
      )}

      <div className="no-print mt-3 grid gap-3 sm:grid-cols-[1fr_auto]">
        <button onClick={enregistrer} disabled={enregistrement} className={utilise ? btn.gold : btn.ghost}>
          {enregistrement ? <Spinner className="h-5 w-5 border-ink/25 border-t-ink" /> : <IconDownload />}
          Enregistrer le billet dans mes photos
        </button>
        <Link to="/" className={btn.ghost}>Acheter un autre billet</Link>
      </div>
      <p className="no-print mt-3 text-center text-xs text-muted">
        Sur iPhone, choisissez « Enregistrer l'image » dans le menu qui s'ouvre : le billet arrive dans la Pellicule.
      </p>
      {message && (
        <p className={`no-print mt-3 animate-fade-in text-center text-sm ${message.ok ? 'text-emerald-300' : 'text-red-400'}`}>{message.texte}</p>
      )}
    </main>
  )
}

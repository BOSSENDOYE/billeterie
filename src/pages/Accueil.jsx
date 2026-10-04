import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ArtistePhoto from '../components/ArtistePhoto'
import { IconBolt, IconCalendar, IconClock, IconPin, IconQr, IconShield } from '../components/Icons'
import { btn, ErrorState, input, PageLoader, Spinner } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateEvenement, formatPrix } from '../lib/format'
import { PAIEMENT_EN_COURS_KEY } from './Paiement'
import { useMesBillets } from '../lib/mesBillets'

const GARANTIES = [
  { icon: IconShield, titre: 'Paiement sécurisé', texte: 'Réglez avec Wave, sans frais ni carte bancaire.' },
  { icon: IconQr, titre: 'Billet infalsifiable', texte: 'Chaque QR code est signé et ne fonctionne qu’une seule fois.' },
  { icon: IconBolt, titre: 'Réception immédiate', texte: 'Votre e-billet s’affiche dès le paiement confirmé.' },
]

function Meta({ icon: Icon, children }) {
  return (
    <span className="flex items-center gap-2 text-sm text-cream/85 sm:text-base">
      <Icon className="h-4 w-4 shrink-0 text-gold sm:h-5 sm:w-5" />
      {children}
    </span>
  )
}

export default function Accueil() {
  const { data, error, reload } = usePolling(api.evenement, [], 8000)
  const navigate = useNavigate()
  const [nom, setNom] = useState('')
  const [tel, setTel] = useState('')
  const [erreur, setErreur] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const mesBillets = useMesBillets()
  const [enCours] = useState(() => {
    try {
      return localStorage.getItem(PAIEMENT_EN_COURS_KEY)
    } catch {
      return null
    }
  })

  if (error && !data) return <ErrorState message={error.message} action={<button onClick={reload} className={btn.ghost}>Réessayer</button>} />
  if (!data) return <PageLoader />

  const ev = data.evenement
  const d = dateEvenement(ev.date)
  // Tarif en cours : prévente jusqu'à la veille du concert, puis Jour J
  const tarif = data.tarif ?? { type: 'prevente', prix: ev.prix, restants: data.restants }
  const enPrevente = tarif.type === 'prevente'
  const quota = enPrevente ? ev.quota_prevente : ev.quota_jour_j
  const restants = tarif.restants
  const pctVendus = ((quota - restants) / quota) * 100
  const complet = restants === 0
  const finPrevente = ev.fin_prevente && dateEvenement(new Date(new Date(ev.fin_prevente).getTime() - 60000).toISOString())

  async function payer(e) {
    e.preventDefault()
    if (nom.trim().length < 2) return setErreur('Veuillez saisir votre nom complet.')
    if (tel.replace(/\D/g, '').length !== 9) return setErreur('Le numéro doit comporter 9 chiffres.')
    setErreur('')
    setEnvoi(true)
    try {
      const { paiement } = await api.creerPaiement(nom.trim(), tel)
      if (data.paiement_simule) {
        // Mode démonstration : le paiement Wave est considéré comme effectué
        await new Promise((r) => setTimeout(r, 1500))
        const { paiement: confirme } = await api.simulerPaiement(paiement.reference)
        return navigate(`/billet/${confirme.ticket_id}`, { state: { nouveau: true } })
      }
      navigate(`/paiement/${paiement.reference}`)
    } catch (err) {
      setErreur(err.message)
      setEnvoi(false)
    }
  }

  return (
    <main>
      {/* Hero */}
      <section className="relative isolate overflow-hidden border-b border-line/60">
        <ArtistePhoto src={ev.image} alt={ev.artiste} className="-z-10 brightness-110" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-t from-ink via-ink/30 to-transparent" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-ink/75 via-ink/20 to-transparent" />

        <div className="mx-auto max-w-6xl px-4 pb-14 pt-20 sm:pb-20 sm:pt-32">
          <p className="animate-fade-in text-xs font-semibold uppercase tracking-[0.35em] text-gold">Concert live · {ev.ville}</p>
          <h1 className="mt-4 max-w-3xl animate-fade-in font-display text-5xl font-extrabold leading-[0.95] sm:text-7xl">
            <span className="text-gradient-gold">{ev.artiste}</span>
          </h1>
          <div className="mt-8 flex animate-fade-in flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-x-8">
            <Meta icon={IconCalendar}>{d.longue}</Meta>
            <Meta icon={IconClock}>{d.heure}</Meta>
            <Meta icon={IconPin}>{ev.lieu}, {ev.ville}</Meta>
          </div>
        </div>
      </section>

      {mesBillets.length > 0 && (
        <div className="mx-auto max-w-6xl px-4 pt-6">
          <Link to="/mes-billets" className="flex animate-fade-in items-center justify-between gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm transition hover:bg-emerald-500/15">
            <span>
              Vous avez <strong>{mesBillets.length} billet{mesBillets.length > 1 ? 's' : ''}</strong> sur ce téléphone
            </span>
            <span className="font-semibold text-emerald-300">Mes billets →</span>
          </Link>
        </div>
      )}

      {enCours && (
        <div className="mx-auto max-w-6xl px-4 pt-6">
          <Link to={`/paiement/${enCours}`} className="flex animate-fade-in items-center justify-between gap-3 rounded-xl border border-gold/40 bg-gold/10 px-4 py-3 text-sm transition hover:bg-gold/15">
            <span>Vous avez un paiement en cours <span className="font-mono text-gold-light">{enCours}</span></span>
            <span className="font-semibold text-gold-light">Reprendre →</span>
          </Link>
        </div>
      )}

      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 lg:grid-cols-[1fr_420px] lg:py-14">
        {/* Informations */}
        <section className="order-2 space-y-8 lg:order-1">
          <div>
            <h2 className="font-display text-2xl font-bold">L'événement</h2>
            <p className="mt-3 max-w-prose leading-relaxed text-muted">
              {ev.artiste} investit le {ev.lieu.toLowerCase()} de {ev.ville} pour une soirée unique.
              {ev.capacite} places : {ev.quota_prevente} en prévente à {formatPrix(ev.prix_prevente)}, puis {ev.quota_jour_j} le jour J
              à {formatPrix(ev.prix_jour_j)}. Placement libre. Le billet est nominatif :
              présentez votre QR code à l'entrée, depuis votre téléphone ou imprimé.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {GARANTIES.map(({ icon: Icon, titre, texte }) => (
              <div key={titre} className="rounded-2xl border border-line bg-surface p-5">
                <Icon className="h-6 w-6 text-gold" />
                <p className="mt-3 font-semibold">{titre}</p>
                <p className="mt-1 text-sm text-muted">{texte}</p>
              </div>
            ))}
          </div>

          <div>
            <h2 className="font-display text-2xl font-bold">Comment ça marche</h2>
            <ol className="mt-4 grid gap-4 sm:grid-cols-3">
              {['Renseignez votre nom et votre numéro Wave', 'Validez le paiement sur Wave', 'Recevez votre billet avec son QR code'].map((etape, i) => (
                <li key={etape} className="flex gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-gold/40 font-display font-bold text-gold">{i + 1}</span>
                  <span className="pt-1 text-sm text-cream/85">{etape}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Achat */}
        <aside className="order-1 lg:order-2 lg:-mt-32">
          <div className="sticky top-24 animate-fade-in rounded-2xl border border-gold/25 bg-surface/95 p-6 shadow-2xl shadow-black/60 backdrop-blur sm:p-7">
            {/* Deux tarifs : celui en cours est mis en avant */}
            <div className="grid grid-cols-2 gap-3">
              <div className={`rounded-xl border p-3 ${enPrevente ? 'border-gold bg-gold/10' : 'border-line opacity-50'}`}>
                <p className="text-[11px] font-bold tracking-[0.2em] text-gold">PRÉVENTE</p>
                <p className="mt-1 font-display text-2xl font-bold text-gold-light">{formatPrix(ev.prix_prevente)}</p>
                <p className="mt-0.5 text-[11px] text-muted">
                  {enPrevente ? (finPrevente ? `Jusqu'au ${finPrevente.jour} ${finPrevente.mois.toLowerCase()} 23h59` : 'En cours') : 'Terminée'}
                </p>
              </div>
              <div className={`rounded-xl border p-3 ${enPrevente ? 'border-line' : 'border-ruby bg-ruby/10'}`}>
                <p className="text-[11px] font-bold tracking-[0.2em] text-ruby-light">JOUR J</p>
                <p className={`mt-1 font-display text-2xl font-bold ${enPrevente ? 'text-cream/70' : 'text-ruby-light'}`}>{formatPrix(ev.prix_jour_j)}</p>
                <p className="mt-0.5 text-[11px] text-muted">{enPrevente ? 'Le jour du concert' : 'En cours'}</p>
              </div>
            </div>

            <div className="mt-5">
              <div className="flex justify-between text-xs">
                <span className="text-muted">Places {enPrevente ? 'prévente' : 'Jour J'} restantes</span>
                <span className="font-semibold tabular-nums">
                  <span className={restants < 30 ? 'text-red-400' : 'text-gold-light'}>{restants}</span>
                  <span className="text-muted"> / {quota}</span>
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
                <div className={`h-full rounded-full transition-all duration-700 ${enPrevente ? 'bg-gradient-gold' : 'bg-gradient-ruby'}`} style={{ width: `${pctVendus}%` }} />
              </div>
            </div>

            {data.vente_en_ligne === false ? (
              <div className="mt-6 rounded-xl border border-ruby/50 bg-ruby/10 p-5 text-center">
                <p className="font-display text-xl font-bold text-ruby-light">Prévente terminée</p>
                <p className="mt-2 text-sm text-cream/85">
                  Billets Jour J à <strong>{formatPrix(ev.prix_jour_j)}</strong>, en vente sur place le jour du concert.
                </p>
                <p className="mt-3 text-xs text-muted">Vous avez déjà un billet ? Retrouvez-le dans « Mes billets ».</p>
              </div>
            ) : (
            <form onSubmit={payer} className="mt-6 space-y-4">
              <label className="block">
                <span className="text-sm font-medium text-cream/90">Nom complet</span>
                <input value={nom} onChange={(e) => setNom(e.target.value)} autoComplete="name" placeholder="Prénom Nom" className={`${input} mt-1.5`} />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-cream/90">Numéro Wave</span>
                <div className="mt-1.5 flex">
                  <span className="grid place-items-center rounded-l-xl border border-r-0 border-line bg-surface-2 px-3.5 text-sm text-muted">+221</span>
                  <input value={tel} onChange={(e) => setTel(e.target.value)} inputMode="tel" autoComplete="tel-national" placeholder="77 123 45 67" className={`${input} rounded-l-none`} />
                </div>
              </label>
              {erreur && <p className="animate-fade-in text-sm text-red-400">{erreur}</p>}

              <button disabled={complet || envoi} className="flex w-full items-center justify-center gap-2 rounded-xl bg-wave py-4 font-bold text-wave-dark transition hover:brightness-105 active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-40">
                {envoi ? <Spinner className="h-5 w-5 border-wave-dark/25 border-t-wave-dark" /> : complet ? (enPrevente ? 'Prévente épuisée' : 'Complet') : <>Payer {formatPrix(tarif.prix)} avec <span className="font-extrabold tracking-tight">Wave</span></>}
              </button>
              {envoi && data.paiement_simule && <p className="animate-fade-in text-center text-sm text-wave">Paiement Wave en cours…</p>}
              <p className="text-center text-xs text-muted">Billet nominatif, non remboursable.</p>
              {data.paiement_simule && (
                <p className="rounded-lg border border-gold/30 bg-gold/5 px-3 py-2 text-center text-xs text-gold-light">
                  Mode démonstration : le paiement est validé automatiquement, aucun débit Wave.
                </p>
              )}
            </form>
            )}
          </div>
        </aside>
      </div>
    </main>
  )
}

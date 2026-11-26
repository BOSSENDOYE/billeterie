import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { IconAlert, IconCheck } from '../components/Icons'
import { btn, ErrorState, PageLoader, Spinner } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { formatPrix } from '../lib/format'
import { typeBillet } from '../lib/typesBillet'

// Dernier paiement en cours, pour pouvoir le reprendre depuis l'accueil après être passé par l'app Wave
export const PAIEMENT_EN_COURS_KEY = 'billetterie_paiement_en_cours'
const memoriser = (ref) => {
  try {
    ref ? localStorage.setItem(PAIEMENT_EN_COURS_KEY, ref) : localStorage.removeItem(PAIEMENT_EN_COURS_KEY)
  } catch {
    /* stockage indisponible */
  }
}

function WaveMark({ className = 'h-5 w-5' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
      <path d="M3 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0" />
    </svg>
  )
}

function Etape({ n, titre, fait, children }) {
  return (
    <li className="relative flex gap-4">
      <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full border font-display font-bold ${fait ? 'border-emerald-400 bg-emerald-400 text-ink' : 'border-gold/50 text-gold'}`}>
        {fait ? <IconCheck className="h-4 w-4" /> : n}
      </span>
      <div className="min-w-0 flex-1 pb-2">
        <p className="pt-1 font-semibold">{titre}</p>
        <div className="mt-3">{children}</div>
      </div>
    </li>
  )
}

export default function Paiement() {
  const { reference } = useParams()
  const navigate = useNavigate()
  const { data, error, reload } = usePolling(() => api.paiement(reference), [reference], 4000)
  const { state } = useLocation()
  const [ouvert, setOuvert] = useState(Boolean(state?.waveOuvert))
  const [erreur, setErreur] = useState('')
  const [envoi, setEnvoi] = useState(false)

  const p = data?.paiement

  useEffect(() => {
    if (!p) return
    if (p.statut === 'reussi') {
      memoriser(null)
      navigate(`/billet/${p.ticket_id}`, { replace: true, state: { nouveau: true } })
    } else if (p.statut === 'echoue') memoriser(null)
    else memoriser(p.reference)
  }, [p, navigate])

  if (error && !data) {
    return <ErrorState message={error.status === 404 ? 'Paiement introuvable.' : error.message} action={<Link to="/" className={btn.ghost}>Retour à la billetterie</Link>} />
  }
  if (!p) return <PageLoader />

  const ev = data.evenement

  async function declarer(e) {
    e.preventDefault()
    setErreur('')
    setEnvoi(true)
    try {
      await api.declarerPaiement(reference)
      await reload()
    } catch (err) {
      setErreur(err.message)
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <div className="animate-fade-in rounded-2xl border border-line bg-surface p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4 border-b border-line pb-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gold">Paiement</p>
            <h1 className="mt-1 font-display text-2xl font-bold">{ev.artiste}</h1>
            <p className="text-sm text-muted">Billet {typeBillet(p.type).label} · {p.nom}</p>
          </div>
          <div className="text-right">
            <p className="font-display text-2xl font-bold text-gold-light">{formatPrix(p.montant)}</p>
            <p className="font-mono text-xs text-muted">{p.reference}</p>
          </div>
        </div>

        {p.statut === 'en_attente' && p.automatique && (
          <div className="mt-6 space-y-4">
            <a
              href={p.wave_url}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-wave py-4 font-bold text-wave-dark transition hover:brightness-105 active:scale-[.98]"
            >
              <WaveMark /> Payer {formatPrix(p.montant)} avec Wave
            </a>
            <div className="flex items-center gap-3 rounded-xl border border-line bg-ink/60 px-4 py-3 text-sm text-muted">
              <Spinner className="h-5 w-5 shrink-0" />
              <p>En attente de la confirmation de Wave. Votre billet s'affichera automatiquement sur cette page dès le paiement effectué.</p>
            </div>
          </div>
        )}

        {p.statut === 'en_attente' && !p.automatique && (
          <ol className="mt-6 space-y-6">
            <Etape n="1" titre={`Payez ${formatPrix(p.montant)} avec Wave`} fait={ouvert}>
              <a
                href={p.wave_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => {
                  setOuvert(true)
                  // Mode démonstration : pas de redirection vers Wave, le paiement est validé directement
                  if (p.simule) {
                    e.preventDefault()
                    api.simulerPaiement(p.reference).then(reload, (err) => setErreur(err.message))
                  }
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-wave py-4 font-bold text-wave-dark transition hover:brightness-105 active:scale-[.98]"
              >
                <WaveMark /> Payer avec Wave
              </a>
              <p className="mt-2 text-xs text-muted">
                Le paiement s'ouvre dans Wave. Vérifiez que le montant est bien de <strong className="text-cream">{formatPrix(p.montant)}</strong>,
                puis revenez sur cette page.
              </p>
            </Etape>

            <Etape n="2" titre="Confirmez votre paiement">
              <form onSubmit={declarer} className="space-y-3">
                <p className="text-sm text-muted">
                  Une fois le paiement effectué dans Wave, cliquez ci-dessous. Utilisez le numéro Wave
                  <span className="text-cream"> +221 {p.telephone}</span> : il permet de retrouver votre paiement.
                </p>
                {erreur && <p className="text-sm text-red-400">{erreur}</p>}
                <button disabled={envoi} className={`${btn.gold} w-full`}>
                  {envoi ? <Spinner className="h-5 w-5 border-ink/25 border-t-ink" /> : "J'ai payé"}
                </button>
              </form>
            </Etape>
          </ol>
        )}

        {p.statut === 'a_verifier' && (
          <div className="mt-8 flex flex-col items-center text-center">
            <Spinner className="h-12 w-12" />
            <p className="mt-5 font-display text-xl font-bold">Vérification du paiement</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              L'organisateur vérifie la réception de votre paiement Wave ({formatPrix(p.montant)} depuis le +221 {p.telephone}).
              Votre billet s'affichera automatiquement sur cette page dès la confirmation.
            </p>
            <p className="mt-6 rounded-xl border border-line bg-ink/60 px-4 py-3 text-xs text-muted">
              Vous pouvez fermer cette page : revenez sur le site, votre paiement <span className="font-mono text-gold-light">{p.reference}</span> vous sera proposé.
            </p>
          </div>
        )}

        {p.statut === 'echoue' && (
          <div className="mt-8 flex flex-col items-center text-center">
            <span className="grid h-14 w-14 place-items-center rounded-full border border-red-500/30 bg-red-500/10 text-red-400">
              <IconAlert className="h-6 w-6" />
            </span>
            <p className="mt-4 font-display text-xl font-bold">Paiement non confirmé</p>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Nous n'avons pas retrouvé ce paiement dans Wave. Si vous avez bien été débité, contactez l'organisateur
              en indiquant la référence <span className="font-mono text-cream">{p.reference}</span>.
            </p>
            <Link to="/" className={`${btn.ghost} mt-6`}>Retour à la billetterie</Link>
          </div>
        )}
      </div>
    </main>
  )
}

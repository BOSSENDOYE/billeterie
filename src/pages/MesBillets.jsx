import { Link } from 'react-router-dom'
import { IconTicket, IconX } from '../components/Icons'
import { btn, Spinner } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateEvenement, numeroFormat } from '../lib/format'
import { typeBillet } from '../lib/typesBillet'
import { oublierBillet, useMesBillets } from '../lib/mesBillets'

const STATUT = {
  vendu: { texte: 'Valide', classe: 'text-emerald-400', point: 'bg-emerald-400 animate-pulse' },
  utilise: { texte: 'Utilisé', classe: 'text-red-400', point: 'bg-red-500' },
}

function CarteBillet({ billet }) {
  // Statut à jour depuis le serveur (valide / déjà utilisé)
  const { data, error } = usePolling(() => api.ticket(billet.id), [billet.id], 15000)
  const statut = STATUT[data?.ticket.statut]
  const d = dateEvenement(billet.date)
  const th = typeBillet(billet.type ?? data?.ticket.type)
  // Les billets mémorisés avant l'arrivée des deux séries n'ont pas de code : on le reconstitue
  const code = data?.ticket.code ?? billet.code ?? numeroFormat(billet.numero, billet.capacite)

  function retirer(e) {
    e.preventDefault()
    if (confirm(`Retirer le billet N° ${code} de ce téléphone ?\nLe billet reste valide : vous pourrez le rouvrir avec son lien.`)) {
      oublierBillet(billet.id)
    }
  }

  return (
    <li>
      <Link
        to={`/billet/${billet.id}`}
        className={`flex items-center gap-4 rounded-2xl border bg-surface p-4 transition active:scale-[.99] ${th.bordure}`}
      >
        <div className={`rounded-xl border px-3 py-2 text-center leading-none ${th.bordure}`}>
          <p className={`font-display text-2xl font-bold ${th.accentClair}`}>{d.jour}</p>
          <p className="mt-0.5 text-[10px] font-bold tracking-widest">{d.mois}</p>
        </div>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2">
            <span className="truncate font-display text-lg font-bold">{billet.artiste}</span>
            <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wider ${th.badge}`}>{th.bandeau}</span>
          </p>
          <p className="truncate text-sm text-muted">{billet.nom} · N° {code}</p>
          <p className="mt-1 flex items-center gap-1.5 text-xs font-semibold">
            {statut ? (
              <span className={`flex items-center gap-1.5 ${statut.classe}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${statut.point}`} />
                {statut.texte}
              </span>
            ) : error ? (
              <span className="text-muted">Statut indisponible</span>
            ) : (
              <Spinner className="h-3 w-3" />
            )}
          </p>
        </div>
        <button onClick={retirer} aria-label="Retirer de ce téléphone" className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-cream">
          <IconX className="h-4 w-4" />
        </button>
      </Link>
    </li>
  )
}

export default function MesBillets() {
  const billets = useMesBillets()

  return (
    <main className="mx-auto max-w-lg px-4 py-8">
      <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gold">Mon espace</p>
      <h1 className="mt-1 font-display text-3xl font-bold">Mes billets</h1>
      <p className="mt-2 text-sm text-muted">Les billets achetés sur ce téléphone sont retrouvés automatiquement ici.</p>

      {billets.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-line bg-surface p-8 text-center">
          <IconTicket className="mx-auto h-10 w-10 text-muted" />
          <p className="mt-4 font-semibold">Aucun billet sur ce téléphone</p>
          <p className="mt-1 text-sm text-muted">
            Si vous avez acheté votre billet sur un autre téléphone, ouvrez ce site depuis celui-ci.
            En cas de problème, contactez l'organisateur avec votre nom et votre numéro Wave.
          </p>
          <Link to="/" className={`${btn.gold} mt-6`}>Acheter un billet</Link>
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {billets.map((b) => (
            <CarteBillet key={b.id} billet={b} />
          ))}
        </ul>
      )}

      <p className="mt-8 text-center text-xs text-muted">
        Astuce : sur la page du billet, « Enregistrer le billet dans mes photos » en garde aussi une copie dans votre galerie.
      </p>
    </main>
  )
}

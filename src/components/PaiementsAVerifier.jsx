import { useState } from 'react'
import { api, usePolling } from '../lib/api'
import { dateCourte, formatPrix } from '../lib/format'
import { IconCheck, IconX } from './Icons'
import { Spinner } from './ui'

/**
 * Paiements déclarés par les acheteurs (numéro Wave, montant), à rapprocher
 * de l'historique Wave Business avant d'émettre le billet.
 */
export default function PaiementsAVerifier({ onChange }) {
  const { data, reload } = usePolling(() => api.paiements('a_verifier'), [], 5000)
  const [enCours, setEnCours] = useState(null)
  const [erreur, setErreur] = useState('')

  async function traiter(p, action) {
    if (action === 'rejeter' && !confirm(`Rejeter le paiement de ${p.nom} (+221 ${p.telephone}) ? Aucun billet ne sera émis.`)) return
    setEnCours(p.reference)
    setErreur('')
    try {
      await (action === 'valider' ? api.validerPaiement(p.reference) : api.rejeterPaiement(p.reference))
      await reload()
      onChange?.()
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnCours(null)
    }
  }

  const paiements = data?.paiements ?? []

  return (
    <section className={`mt-6 overflow-hidden rounded-2xl border bg-surface ${paiements.length ? 'border-gold/40' : 'border-line'}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line p-4">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold">Paiements à vérifier</h2>
          {paiements.length > 0 && (
            <span className="rounded-full bg-gold px-2 py-0.5 text-xs font-bold text-ink tabular-nums">{paiements.length}</span>
          )}
        </div>
        <p className="text-xs text-muted">Retrouvez chaque paiement (numéro, montant) dans votre app Wave Business avant de confirmer.</p>
      </div>

      {erreur && <p className="border-b border-line bg-red-500/10 px-4 py-2 text-sm text-red-300">{erreur}</p>}

      {!data ? (
        <div className="grid place-items-center p-8"><Spinner /></div>
      ) : paiements.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted">Aucun paiement en attente de vérification.</p>
      ) : (
        <ul className="divide-y divide-line/70">
          {paiements.map((p) => (
            <li key={p.reference} className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-4">
              <div className="min-w-40 flex-1">
                <p className="font-medium">
                  {p.nom}{' '}
                  <span className={`ml-1 rounded-full border px-2 py-0.5 align-middle text-[10px] font-bold tracking-wider ${p.type === 'jour_j' ? 'border-ruby/60 text-ruby-light' : 'border-gold/50 text-gold-light'}`}>
                    {p.type === 'jour_j' ? 'JOUR J' : 'PRÉVENTE'}
                  </span>
                </p>
                <p className="text-xs text-muted">Déclaré payé le {dateCourte(p.declare_le)} · {p.reference}</p>
              </div>
              <div className="min-w-44">
                <p className="text-[11px] uppercase tracking-wider text-muted">Numéro Wave</p>
                <p className="select-all font-mono text-sm text-gold-light">+221 {p.telephone}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider text-muted">Montant attendu</p>
                <p className="text-sm font-semibold">{formatPrix(p.montant)}</p>
              </div>
              <div className="flex gap-2">
                <button
                  disabled={enCours === p.reference}
                  onClick={() => traiter(p, 'valider')}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3.5 py-2 text-sm font-semibold text-ink transition hover:bg-emerald-400 disabled:opacity-50"
                >
                  {enCours === p.reference ? <Spinner className="h-4 w-4 border-ink/30 border-t-ink" /> : <IconCheck className="h-4 w-4" />} Confirmer
                </button>
                <button
                  disabled={enCours === p.reference}
                  onClick={() => traiter(p, 'rejeter')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/40 px-3.5 py-2 text-sm font-semibold text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
                >
                  <IconX className="h-4 w-4" /> Rejeter
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

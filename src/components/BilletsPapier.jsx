import { useState } from 'react'
import { api } from '../lib/api'
import { formatPrix } from '../lib/format'
import { IconDownload } from './Icons'
import { btn, Spinner } from './ui'

/** Impression des billets Jour J (vendus en papier, sur place). */
export default function BilletsPapier({ evenement: ev, serie, onImpression }) {
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState('')
  const dejaImprimes = serie.physiques > 0

  async function telecharger() {
    const message = dejaImprimes
      ? 'Télécharger à nouveau le PDF des billets Jour J ? (mêmes billets, mêmes QR codes)'
      : `Émettre les ${ev.quota_jour_j} billets Jour J en papier ?\n\nIls deviennent valides tout de suite : gardez-les en lieu sûr jusqu'à leur vente.`
    if (!confirm(message)) return
    setEnvoi(true)
    setErreur('')
    try {
      await api.billetsPapierPdf()
      onImpression?.()
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <section className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-ruby/40 bg-surface p-5">
      <div className="max-w-xl">
        <h2 className="font-semibold">Billets Jour J à imprimer</h2>
        <p className="mt-1 text-sm text-muted">
          PDF de {ev.quota_jour_j} billets ({formatPrix(ev.prix_jour_j)}), 10 par page A4 avec traits de coupe. Chaque billet a son QR
          code unique : il ne permet qu'une seule entrée.
          {dejaImprimes && <span className="text-ruby-light"> {serie.physiques} billets déjà émis — {serie.scannes} entrés.</span>}
        </p>
        {erreur && <p className="mt-2 text-sm text-red-400">{erreur}</p>}
      </div>
      <button onClick={telecharger} disabled={envoi} className={`${btn.ghost} border-ruby/60 text-ruby-light`}>
        {envoi ? <Spinner className="h-5 w-5" /> : <IconDownload />}
        {dejaImprimes ? 'Retélécharger le PDF' : 'Télécharger les billets (PDF)'}
      </button>
    </section>
  )
}

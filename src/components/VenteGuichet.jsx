import { useState } from 'react'
import { Link } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '../lib/api'
import { formatPrix } from '../lib/format'
import { typeBillet } from '../lib/typesBillet'
import { IconCheck } from './Icons'
import { btn, input, Spinner } from './ui'

/**
 * Vente sur place (guichet) : l'équipe encaisse puis émet le billet immédiatement.
 * Par défaut le billet est marqué « entré » : l'acheteur passe directement.
 */
export default function VenteGuichet({ evenement: ev, stats, onVente }) {
  const tarifDuJour = ev.fin_prevente && new Date() >= new Date(ev.fin_prevente) ? 'jour_j' : 'prevente'
  const [type, setType] = useState(tarifDuJour)
  const [nom, setNom] = useState('')
  const [tel, setTel] = useState('')
  const [entree, setEntree] = useState(true)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState('')
  const [vendu, setVendu] = useState(null)

  const restants = stats.par_type?.[type]?.restants ?? 0
  const prix = type === 'jour_j' ? ev.prix_jour_j : ev.prix_prevente

  async function vendre(e) {
    e.preventDefault()
    if (!confirm(`Encaisser ${formatPrix(prix)} et émettre un billet ${typeBillet(type).label} ?`)) return
    setEnvoi(true)
    setErreur('')
    try {
      const { ticket } = await api.venteGuichet({ type, nom: nom.trim(), telephone: tel, entree_immediate: entree })
      setVendu(ticket)
      setNom('')
      setTel('')
      onVente?.()
    } catch (err) {
      setErreur(err.message)
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <section className="mt-6 rounded-2xl border border-line bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line p-4">
        <h2 className="font-semibold">Vente au guichet</h2>
        <p className="text-xs text-muted">Encaissez d'abord (espèces ou Wave), puis émettez le billet.</p>
      </div>

      <div className="grid gap-6 p-4 lg:grid-cols-[1fr_auto]">
        <form onSubmit={vendre} className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            {['prevente', 'jour_j'].map((t) => {
              const th = typeBillet(t)
              const actif = type === t
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={`rounded-xl border p-3 text-left transition ${actif ? th.badge : 'border-line text-muted hover:text-cream'}`}
                >
                  <span className="block text-xs font-bold tracking-[0.2em]">{th.bandeau}</span>
                  <span className="block font-display text-xl font-bold">{formatPrix(t === 'jour_j' ? ev.prix_jour_j : ev.prix_prevente)}</span>
                  <span className="block text-[11px]">{stats.par_type?.[t]?.restants ?? '—'} restants</span>
                </button>
              )
            })}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom (facultatif)" className={`${input} py-3 text-sm`} />
            <input value={tel} onChange={(e) => setTel(e.target.value)} inputMode="tel" placeholder="Téléphone (facultatif)" className={`${input} py-3 text-sm`} />
          </div>
          <label className="flex items-center gap-2 text-sm text-cream/85">
            <input type="checkbox" checked={entree} onChange={(e) => setEntree(e.target.checked)} className="h-4 w-4 accent-[#D4AF37]" />
            L'acheteur entre maintenant (billet marqué « entré »)
          </label>
          {erreur && <p className="text-sm text-red-400">{erreur}</p>}
          <button disabled={envoi || restants === 0} className={`${btn.gold} w-full`}>
            {envoi ? <Spinner className="h-5 w-5 border-ink/25 border-t-ink" /> : restants === 0 ? 'Série épuisée' : `Émettre un billet ${typeBillet(type).label} · ${formatPrix(prix)}`}
          </button>
        </form>

        {vendu && (
          <div className={`animate-fade-in rounded-xl border p-4 text-center lg:w-64 ${typeBillet(vendu.type).bordure}`}>
            <p className="flex items-center justify-center gap-1.5 text-sm font-semibold text-emerald-300">
              <IconCheck className="h-4 w-4" /> Billet émis
            </p>
            <p className={`mt-1 font-mono text-lg font-bold ${typeBillet(vendu.type).accentClair}`}>{vendu.code}</p>
            <div className="mx-auto mt-3 w-40 rounded-lg bg-white p-1.5">
              <QRCodeSVG value={vendu.qr} size={160} level="M" marginSize={2} className="h-auto w-full" />
            </div>
            <p className="mt-2 text-xs text-muted">{vendu.statut === 'utilise' ? 'Entrée enregistrée.' : "L'acheteur peut photographier ce QR."}</p>
            <Link to={`/billet/${vendu.id}`} state={{ depuisAdmin: true }} className="mt-2 inline-block text-xs font-semibold text-gold hover:text-gold-light">
              Voir le billet
            </Link>
          </div>
        )}
      </div>
    </section>
  )
}

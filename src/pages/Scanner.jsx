import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import { IconAlert, IconCamera, IconCheck, IconX } from '../components/Icons'
import { btn, Logo, Spinner } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateCourte, heure, numeroFormat } from '../lib/format'

const RESULTATS = {
  valide: { bg: 'bg-emerald-600', dot: 'bg-emerald-500', Icon: IconCheck, titre: 'BILLET VALIDE', court: 'Valide' },
  utilise: { bg: 'bg-red-700', dot: 'bg-orange-500', Icon: IconAlert, titre: 'DÉJÀ UTILISÉ', court: 'Déjà utilisé' },
  invalide: { bg: 'bg-red-700', dot: 'bg-red-500', Icon: IconX, titre: 'BILLET INVALIDE', court: 'Invalide' },
}

function Resultat({ res, onNext }) {
  const { bg, Icon, titre } = RESULTATS[res.resultat]
  return (
    <div className={`fixed inset-0 z-50 flex animate-fade-in flex-col items-center justify-center p-6 text-center text-white ${bg}`}>
      <div className="grid h-32 w-32 animate-pop place-items-center rounded-full bg-white/15 ring-8 ring-white/10">
        <Icon className="h-20 w-20" strokeWidth="2.5" />
      </div>
      <h2 className="mt-8 text-3xl font-black tracking-tight sm:text-5xl">{titre}</h2>
      {res.ticket && (
        <div className="mt-4 space-y-1">
          <p className="text-2xl font-bold">{res.ticket.acheteur_nom}</p>
          <p className="font-mono text-lg text-white/85">Billet N° {numeroFormat(res.ticket.numero)}</p>
          {res.resultat === 'utilise' && (
            <p className="mt-4 rounded-xl bg-black/25 px-4 py-2.5">
              Premier passage : <strong>{dateCourte(res.ticket.date_scan)}</strong>
            </p>
          )}
        </div>
      )}
      {res.raison && <p className="mt-3 text-lg text-white/85">{res.raison}</p>}
      <button onClick={onNext} autoFocus className="mt-12 w-full max-w-xs rounded-2xl bg-white py-4 text-lg font-bold text-ink shadow-xl active:scale-[.98]">
        Scanner le suivant
      </button>
    </div>
  )
}

export default function Scanner() {
  const stats = usePolling(api.stats, [], 5000)
  const historique = usePolling(api.scans, [], 5000)
  const [actif, setActif] = useState(false)
  const [erreurCam, setErreurCam] = useState('')
  const [res, setRes] = useState(null)
  const [verif, setVerif] = useState(false)
  const qrRef = useRef(null)
  const busy = useRef(false)

  async function arreter() {
    const qr = qrRef.current
    qrRef.current = null
    setActif(false)
    if (qr?.isScanning) await qr.stop().catch(() => {})
  }

  async function traiter(texte) {
    if (busy.current) return
    busy.current = true
    arreter()
    setVerif(true)
    try {
      const r = await api.scan(texte)
      navigator.vibrate?.(r.resultat === 'valide' ? 150 : [90, 60, 90, 60, 90])
      setRes(r)
      historique.reload()
      stats.reload()
    } catch (e) {
      setRes({ resultat: 'invalide', raison: e.message })
    } finally {
      setVerif(false)
    }
  }

  async function demarrer() {
    setErreurCam('')
    busy.current = false
    setActif(true)
    try {
      const qr = new Html5Qrcode('qr-reader', { verbose: false })
      qrRef.current = qr
      await qr.start({ facingMode: 'environment' }, { fps: 10, qrbox: { width: 240, height: 240 } }, traiter, () => {})
    } catch (e) {
      qrRef.current = null
      setActif(false)
      setErreurCam(
        window.isSecureContext
          ? `Caméra indisponible : ${e?.message ?? e}`
          : 'La caméra exige une connexion HTTPS (ou localhost).',
      )
    }
  }

  useEffect(
    () => () => {
      if (qrRef.current?.isScanning) qrRef.current.stop().catch(() => {})
    },
    [],
  )

  const s = stats.data?.stats
  const scans = historique.data?.scans ?? []

  return (
    <main className="mx-auto max-w-md px-4 py-6">
      {res && <Resultat res={res} onNext={() => { setRes(null); busy.current = false }} />}

      <div className="mb-6 border-b border-line pb-4">
        <Logo />
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gold">Contrôle d'accès</p>
          <h1 className="mt-1 font-display text-2xl font-bold">Scanner</h1>
        </div>
        <span className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${actif ? 'border-emerald-500/40 text-emerald-300' : 'border-line text-muted'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${actif ? 'animate-pulse bg-emerald-400' : 'bg-muted'}`} />
          {actif ? 'Caméra active' : 'En attente'}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-line bg-surface px-4 py-3">
          <p className="text-xs text-muted">Entrées</p>
          <p className="font-display text-2xl font-bold tabular-nums text-gold-light">{s?.scannes ?? '—'}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface px-4 py-3">
          <p className="text-xs text-muted">Attendus</p>
          <p className="font-display text-2xl font-bold tabular-nums">{s ? s.vendus - s.scannes : '—'}</p>
        </div>
      </div>

      <div className="relative mt-4 aspect-square overflow-hidden rounded-2xl border border-line bg-surface">
        <div id="qr-reader" className="h-full w-full" />
        {!actif && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-5 p-6 text-center">
            <div className="relative h-36 w-36">
              {['left-0 top-0 border-l-2 border-t-2 rounded-tl-xl', 'right-0 top-0 border-r-2 border-t-2 rounded-tr-xl', 'bottom-0 left-0 border-b-2 border-l-2 rounded-bl-xl', 'bottom-0 right-0 border-b-2 border-r-2 rounded-br-xl'].map((c) => (
                <span key={c} className={`absolute h-8 w-8 border-gold ${c}`} />
              ))}
              <IconCamera className="absolute inset-0 m-auto h-10 w-10 text-muted" />
            </div>
            <button onClick={demarrer} className={btn.gold}>Démarrer le scan</button>
            {erreurCam && <p className="text-sm text-red-400">{erreurCam}</p>}
          </div>
        )}
        {verif && (
          <div className="absolute inset-0 grid place-items-center bg-ink/70"><Spinner className="h-10 w-10" /></div>
        )}
      </div>
      {actif && <button onClick={arreter} className={`${btn.ghost} mt-3 w-full`}>Arrêter la caméra</button>}

      <section className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Derniers passages</h2>
        {scans.length === 0 ? (
          <p className="mt-3 text-sm text-muted">Aucun scan pour le moment.</p>
        ) : (
          <ul className="mt-3 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
            {scans.map((sc) => {
              const r = RESULTATS[sc.resultat]
              return (
                <li key={sc.id} className="flex items-center gap-3 px-4 py-3">
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${r.dot}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{sc.nom ?? 'Inconnu'}</p>
                    <p className="text-xs text-muted">
                      {sc.numero ? `N° ${numeroFormat(sc.numero)} · ` : ''}{r.court}{sc.raison ? ` · ${sc.raison}` : ''}
                    </p>
                  </div>
                  <time className="text-xs tabular-nums text-muted">{heure(sc.scanne_le)}</time>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </main>
  )
}

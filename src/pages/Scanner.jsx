import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode'
import { IconAlert, IconCamera, IconCheck, IconX } from '../components/Icons'
import { btn, Logo, Spinner } from '../components/ui'
import { api, usePolling } from '../lib/api'
import { dateCourte, heure, numeroFormat } from '../lib/format'

const RESULTATS = {
  valide: { bg: 'bg-emerald-600', dot: 'bg-emerald-500', Icon: IconCheck, titre: 'BILLET VALIDE', court: 'Valide', duree: 2200 },
  utilise: { bg: 'bg-red-700', dot: 'bg-orange-500', Icon: IconAlert, titre: 'DÉJÀ UTILISÉ', court: 'Déjà utilisé', duree: 4000 },
  invalide: { bg: 'bg-red-700', dot: 'bg-red-500', Icon: IconX, titre: 'BILLET INVALIDE', court: 'Invalide', duree: 3500 },
}

// Même QR ignoré pendant ce délai après la fermeture du résultat (évite « déjà utilisé » en rafale)
const ANTI_REBOND_MS = 4000

function IconTorche({ allumee, className = 'h-6 w-6' }) {
  return (
    <svg viewBox="0 0 24 24" fill={allumee ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M8 2h8v4l-2 4v11a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V10L8 6z" />
      <path d="M12 13v2" stroke={allumee ? '#0A0A0B' : 'currentColor'} strokeLinecap="round" />
    </svg>
  )
}

/** Bip court : aigu si valide, grave sinon (entrée bruyante : on ne regarde pas toujours l'écran). */
function bip(ok) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    const ctx = bip.ctx || (bip.ctx = new Ctx())
    const notes = ok ? [[880, 0], [1320, 0.12]] : [[220, 0], [220, 0.22]]
    for (const [freq, t] of notes) {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.frequency.value = freq
      osc.type = ok ? 'sine' : 'square'
      gain.gain.setValueAtTime(0.25, ctx.currentTime + t)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.15)
      osc.connect(gain).connect(ctx.destination)
      osc.start(ctx.currentTime + t)
      osc.stop(ctx.currentTime + t + 0.16)
    }
  } catch {
    /* audio indisponible */
  }
}

function Resultat({ res, onFermer }) {
  const { bg, Icon, titre, duree } = RESULTATS[res.resultat]
  useEffect(() => {
    const t = setTimeout(onFermer, duree)
    return () => clearTimeout(t)
  }, [onFermer, duree])

  return (
    <button onClick={onFermer} className={`fixed inset-0 z-50 flex animate-fade-in flex-col items-center justify-center p-6 text-center text-white ${bg}`}>
      <span className="grid h-32 w-32 animate-pop place-items-center rounded-full bg-white/15 ring-8 ring-white/10">
        <Icon className="h-20 w-20" strokeWidth="2.5" />
      </span>
      <span className="mt-8 text-4xl font-black tracking-tight">{titre}</span>
      {res.ticket && (
        <span className="mt-4 block space-y-1">
          <span className="block text-2xl font-bold">{res.ticket.acheteur_nom}</span>
          <span className="block font-mono text-lg text-white/85">Billet N° {numeroFormat(res.ticket.numero)}</span>
          {res.resultat === 'utilise' && (
            <span className="mt-4 block rounded-xl bg-black/25 px-4 py-2.5">
              Premier passage : <strong>{dateCourte(res.ticket.date_scan)}</strong>
            </span>
          )}
        </span>
      )}
      {res.raison && <span className="mt-3 block text-lg text-white/85">{res.raison}</span>}
      <span className="mt-12 text-sm text-white/70">Touchez l'écran pour scanner le suivant</span>
      {/* Barre de temps avant retour automatique au scan */}
      <span className="absolute inset-x-0 bottom-0 h-1.5 origin-left bg-white/60" style={{ animation: `decompte ${duree}ms linear forwards` }} />
      <style>{'@keyframes decompte{from{transform:scaleX(1)}to{transform:scaleX(0)}}'}</style>
    </button>
  )
}

export default function Scanner() {
  const stats = usePolling(api.stats, [], 5000)
  const historique = usePolling(api.scans, [], 5000)
  const [actif, setActif] = useState(false)
  const [demarrage, setDemarrage] = useState(false)
  const [erreurCam, setErreurCam] = useState('')
  const [res, setRes] = useState(null)
  const [verif, setVerif] = useState(false)
  const [torche, setTorche] = useState({ dispo: false, allumee: false })
  const qrRef = useRef(null)
  const torcheRef = useRef(null)
  const wakeLockRef = useRef(null)
  const busy = useRef(false)
  const dernier = useRef({ texte: '', jusqua: 0 })

  async function garderEcranAllume(oui) {
    try {
      if (oui) wakeLockRef.current = await navigator.wakeLock?.request('screen')
      else await wakeLockRef.current?.release()
    } catch {
      /* non supporté */
    }
  }

  async function arreter() {
    const qr = qrRef.current
    qrRef.current = null
    torcheRef.current = null
    setActif(false)
    setTorche({ dispo: false, allumee: false })
    garderEcranAllume(false)
    if (qr?.isScanning) await qr.stop().catch(() => {})
  }

  async function traiter(texte) {
    if (busy.current) return
    if (texte === dernier.current.texte && Date.now() < dernier.current.jusqua) return
    busy.current = true
    dernier.current = { texte, jusqua: Infinity }
    setVerif(true)
    try {
      const r = await api.scan(texte)
      navigator.vibrate?.(r.resultat === 'valide' ? 150 : [90, 60, 90, 60, 90])
      bip(r.resultat === 'valide')
      setRes(r)
      historique.reload()
      stats.reload()
    } catch (e) {
      bip(false)
      setRes({ resultat: 'invalide', raison: e.message })
    } finally {
      setVerif(false)
    }
  }

  function fermerResultat() {
    setRes(null)
    dernier.current = { ...dernier.current, jusqua: Date.now() + ANTI_REBOND_MS }
    busy.current = false
  }

  async function demarrer() {
    setErreurCam('')
    setDemarrage(true)
    busy.current = false
    // L'audio (bip) doit être débloqué pendant un geste de l'utilisateur
    try {
      bip.ctx ||= new (window.AudioContext || window.webkitAudioContext)()
      bip.ctx.resume()
    } catch {
      /* audio indisponible */
    }
    try {
      const qr = new Html5Qrcode('qr-reader', {
        verbose: false,
        formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
        useBarCodeDetectorIfSupported: true,
        // Détecteur natif du téléphone (Android/Chrome) : bien plus rapide et tolérant
        experimentalFeatures: { useBarCodeDetectorIfSupported: true },
      })
      qrRef.current = qr
      await qr.start(
        { facingMode: 'environment' },
        {
          fps: 15,
          // Zone d'analyse : 85 % du petit côté de l'image
          qrbox: (w, h) => {
            const cote = Math.floor(Math.min(w, h) * 0.85)
            return { width: cote, height: cote }
          },
          videoConstraints: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        },
        traiter,
        () => {},
      )
      setActif(true)
      garderEcranAllume(true)
      qr.applyVideoConstraints({ advanced: [{ focusMode: 'continuous' }] }).catch(() => {})
      try {
        const t = qr.getRunningTrackCameraCapabilities().torchFeature()
        if (t.isSupported()) {
          torcheRef.current = t
          setTorche({ dispo: true, allumee: false })
        }
      } catch {
        /* torche non gérée par ce navigateur */
      }
    } catch (e) {
      qrRef.current = null
      setErreurCam(
        window.isSecureContext
          ? `Caméra indisponible : ${e?.message ?? e}. Autorisez l'accès à la caméra dans le navigateur.`
          : 'La caméra exige une connexion HTTPS.',
      )
    } finally {
      setDemarrage(false)
    }
  }

  async function basculerTorche() {
    const t = torcheRef.current
    if (!t) return
    try {
      await t.apply(!torche.allumee)
      setTorche((s) => ({ ...s, allumee: !s.allumee }))
    } catch {
      setTorche({ dispo: false, allumee: false })
    }
  }

  useEffect(
    () => () => {
      if (qrRef.current?.isScanning) qrRef.current.stop().catch(() => {})
      wakeLockRef.current?.release?.().catch?.(() => {})
    },
    [],
  )

  const s = stats.data?.stats
  const scans = historique.data?.scans ?? []

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3">
      {res && <Resultat res={res} onFermer={fermerResultat} />}

      <header className="flex items-center justify-between gap-3">
        <Logo />
        <div className="flex gap-2 text-right">
          <div className="rounded-lg border border-line bg-surface px-3 py-1.5">
            <p className="text-[10px] uppercase tracking-wider text-muted">Entrées</p>
            <p className="font-display text-lg font-bold leading-tight tabular-nums text-gold-light">{s?.scannes ?? '—'}</p>
          </div>
          <div className="rounded-lg border border-line bg-surface px-3 py-1.5">
            <p className="text-[10px] uppercase tracking-wider text-muted">Attendus</p>
            <p className="font-display text-lg font-bold leading-tight tabular-nums">{s ? s.vendus - s.scannes : '—'}</p>
          </div>
        </div>
      </header>

      {/* Caméra */}
      <div className="relative mt-3 aspect-[3/4] w-full overflow-hidden rounded-2xl border border-line bg-black">
        <div id="qr-reader" className="h-full w-full [&_video]:!h-full [&_video]:!w-full [&_video]:object-cover" />

        {actif && (
          <>
            {/* Cadre de visée : html5-qrcode dessine le sien, on le remplace par un cadre doré */}
            <style>{'#qr-reader__scan_region img, #qr-shaded-region { display: none !important; }'}</style>
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <div className="relative aspect-square w-[78%]">
                {['left-0 top-0 border-l-4 border-t-4 rounded-tl-2xl', 'right-0 top-0 border-r-4 border-t-4 rounded-tr-2xl', 'bottom-0 left-0 border-b-4 border-l-4 rounded-bl-2xl', 'bottom-0 right-0 border-b-4 border-r-4 rounded-br-2xl'].map((c) => (
                  <span key={c} className={`absolute h-12 w-12 border-gold ${c}`} />
                ))}
                <span className="absolute inset-x-4 top-0 h-0.5 animate-[balayage_2.2s_ease-in-out_infinite] bg-gold shadow-[0_0_12px_2px] shadow-gold/60" />
              </div>
            </div>
            <style>{'@keyframes balayage{0%,100%{top:4%}50%{top:94%}}'}</style>
            <p className="pointer-events-none absolute inset-x-0 top-3 text-center text-sm font-medium text-white drop-shadow">
              Placez le QR code dans le cadre
            </p>

            <div className="absolute inset-x-0 bottom-0 flex items-center justify-center gap-4 bg-gradient-to-t from-black/80 to-transparent p-4">
              {torche.dispo && (
                <button
                  onClick={basculerTorche}
                  aria-label={torche.allumee ? 'Éteindre la lampe' : 'Allumer la lampe'}
                  className={`grid h-14 w-14 place-items-center rounded-full border-2 transition active:scale-95 ${torche.allumee ? 'border-gold bg-gold text-ink' : 'border-white/60 bg-black/40 text-white'}`}
                >
                  <IconTorche allumee={torche.allumee} />
                </button>
              )}
              <button onClick={arreter} className="h-14 rounded-full border-2 border-white/60 bg-black/40 px-6 text-sm font-semibold text-white active:scale-95">
                Arrêter
              </button>
            </div>
          </>
        )}

        {!actif && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 p-6 text-center">
            <IconCamera className="h-14 w-14 text-muted" />
            <button onClick={demarrer} disabled={demarrage} className={`${btn.gold} w-full max-w-60 py-5 text-lg`}>
              {demarrage ? <Spinner className="h-6 w-6 border-ink/25 border-t-ink" /> : 'Démarrer le scan'}
            </button>
            {erreurCam && <p className="text-sm text-red-400">{erreurCam}</p>}
          </div>
        )}

        {verif && (
          <div className="absolute inset-0 grid place-items-center bg-black/60"><Spinner className="h-12 w-12" /></div>
        )}
      </div>

      {actif && !torche.dispo && (
        <p className="mt-2 text-center text-xs text-muted">Lampe torche non disponible sur ce navigateur (iPhone : utilisez le Centre de contrôle).</p>
      )}

      <section className="mt-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Derniers passages</h2>
        {scans.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Aucun scan pour le moment.</p>
        ) : (
          <ul className="mt-2 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
            {scans.slice(0, 8).map((sc) => {
              const r = RESULTATS[sc.resultat]
              return (
                <li key={sc.id} className="flex items-center gap-3 px-4 py-3">
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${r.dot}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{sc.nom ?? 'Inconnu'}</p>
                    <p className="truncate text-xs text-muted">
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

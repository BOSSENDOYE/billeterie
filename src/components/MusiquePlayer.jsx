import { useEffect, useRef, useState } from 'react'
import ArtistePhoto from './ArtistePhoto'
import { btn, Logo } from './ui'
import { api } from '../lib/api'
import { dateEvenement } from '../lib/format'

const SRC = '/musique/son.mp4'
const PREF_KEY = 'billetterie_son_coupe'
const VOLUME = 0.5

const lirePref = () => {
  try {
    return localStorage.getItem(PREF_KEY) === '1'
  } catch {
    return false
  }
}
const ecrirePref = (coupe) => {
  try {
    localStorage.setItem(PREF_KEY, coupe ? '1' : '0')
  } catch {
    /* préférence non mémorisée */
  }
}

function IconSon({ coupe, className = 'h-5 w-5' }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" />
      {coupe ? <path d="m16 9.5 5 5m0-5-5 5" /> : <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />}
    </svg>
  )
}

/** Écran d'entrée : le clic sur « Entrer » est le geste qui autorise le son. */
function EcranEntree({ onEntrer, onSansSon }) {
  const [ev, setEv] = useState(null)
  useEffect(() => {
    api.evenement().then((d) => setEv(d.evenement), () => {})
  }, [])
  const d = ev && dateEvenement(ev.date)

  return (
    <div data-entree className="fixed inset-0 z-[60] isolate flex animate-fade-in flex-col items-center justify-center overflow-hidden bg-ink px-6 text-center">
      {ev && <ArtistePhoto src={ev.image} alt="" className="-z-10 opacity-45" />}
      <div className="absolute inset-0 -z-10 bg-gradient-to-t from-ink via-ink/60 to-ink/30" />

      <Logo />
      <p className="mt-10 text-xs font-semibold uppercase tracking-[0.35em] text-gold">
        {ev ? `Concert live · ${ev.ville}` : 'Concert live'}
      </p>
      <h1 className="mt-3 font-display text-5xl font-extrabold leading-none sm:text-7xl">
        <span className="text-gradient-gold">{ev?.artiste ?? ' '}</span>
      </h1>
      {d && <p className="mt-4 text-cream/80">{d.longue} · {ev.lieu}</p>}

      <button onClick={onEntrer} autoFocus className={`${btn.gold} mt-10 px-8 py-4 text-lg`}>
        <IconSon className="h-5 w-5" /> Entrer sur le site
      </button>
      <button onClick={onSansSon} className="mt-4 text-sm text-muted underline-offset-4 hover:text-cream hover:underline">
        Entrer sans le son
      </button>
    </div>
  )
}

/**
 * Musique d'ambiance du site. Les navigateurs interdisent le son automatique
 * avant une interaction : si la lecture est bloquée, un écran d'entrée
 * (page d'accueil) ou le premier clic / toucher du visiteur la déclenche.
 */
export default function MusiquePlayer({ actif = true, ecranEntree = false }) {
  const audioRef = useRef(null)
  const [coupe, setCoupe] = useState(lirePref)
  const [enLecture, setEnLecture] = useState(false)
  const [bloque, setBloque] = useState(false)

  // Lecture automatique, ou au premier geste du visiteur si le navigateur bloque
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || coupe || !actif) return

    const evenements = ['pointerdown', 'keydown', 'touchstart']
    const nettoyer = () => evenements.forEach((e) => window.removeEventListener(e, demarrer))
    function demarrer(e) {
      // Les boutons de l'écran d'entrée gèrent eux-mêmes la lecture
      if (e.target instanceof Element && e.target.closest('[data-entree]')) return
      audio.play().then(() => {
        nettoyer()
        setBloque(false)
      }, () => {})
    }

    audio.volume = VOLUME
    audio.play().then(
      () => setBloque(false),
      () => {
        setBloque(true)
        evenements.forEach((e) => window.addEventListener(e, demarrer))
      },
    )
    return nettoyer
  }, [coupe, actif])

  function entrer() {
    const audio = audioRef.current
    audio.volume = VOLUME
    audio.play().catch(() => {})
    setBloque(false)
  }

  function entrerSansSon() {
    setCoupe(true)
    ecrirePref(true)
    setBloque(false)
  }

  // Pause sur les pages où la musique ne doit pas jouer (scanner, tableau de bord)
  useEffect(() => {
    if (!actif) audioRef.current?.pause()
  }, [actif])

  function basculer() {
    const audio = audioRef.current
    const nouveau = !coupe
    setCoupe(nouveau)
    ecrirePref(nouveau)
    if (nouveau) audio.pause()
    else {
      audio.volume = VOLUME
      audio.play().catch(() => {})
    }
  }

  return (
    <>
      {bloque && ecranEntree && actif && !coupe && <EcranEntree onEntrer={entrer} onSansSon={entrerSansSon} />}
      <audio
        ref={audioRef}
        src={SRC}
        loop
        preload="auto"
        onPlay={() => setEnLecture(true)}
        onPause={() => setEnLecture(false)}
      />
      {actif && (
        <button
          onClick={basculer}
          aria-label={coupe ? 'Activer la musique' : 'Couper la musique'}
          title={coupe ? 'Activer la musique' : 'Couper la musique'}
          className="no-print fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full border border-gold/40 bg-ink/85 px-3.5 py-2.5 text-gold-light shadow-lg shadow-black/50 backdrop-blur transition hover:border-gold hover:text-gold active:scale-95"
        >
          <IconSon coupe={coupe || !enLecture} />
          {enLecture && !coupe && (
            <span className="flex h-4 items-end gap-0.5" aria-hidden="true">
              {[0, 150, 300].map((d) => (
                <span key={d} className="w-0.5 animate-pulse rounded-full bg-gold" style={{ height: `${8 + d / 50}px`, animationDelay: `${d}ms` }} />
              ))}
            </span>
          )}
        </button>
      )}
    </>
  )
}

// Billets achetés sur cet appareil, pour les retrouver même sans avoir enregistré l'image.
// Stockage local au navigateur : perdu en navigation privée ou si l'historique est effacé.
import { useSyncExternalStore } from 'react'

const CLE = 'billetterie_mes_billets'
const EVENEMENT = 'mes-billets:change'
const MAX = 30

let cacheBrut = null
let cache = []

function lire() {
  let brut = null
  try {
    brut = localStorage.getItem(CLE)
  } catch {
    /* stockage indisponible */
  }
  if (brut !== cacheBrut) {
    cacheBrut = brut
    try {
      cache = JSON.parse(brut) || []
    } catch {
      cache = []
    }
  }
  return cache
}

function ecrire(liste) {
  try {
    localStorage.setItem(CLE, JSON.stringify(liste))
  } catch {
    /* stockage plein ou indisponible */
  }
  window.dispatchEvent(new Event(EVENEMENT))
}

/** Mémorise (ou met à jour) un billet sur cet appareil. */
export function memoriserBillet(ticket, evenement) {
  const entree = {
    id: ticket.id,
    numero: ticket.numero,
    nom: ticket.acheteur_nom,
    artiste: evenement.artiste,
    date: evenement.date,
    capacite: evenement.capacite,
  }
  const liste = lire()
  const existant = liste.find((b) => b.id === ticket.id)
  if (existant && JSON.stringify(existant) === JSON.stringify(entree)) return
  ecrire([entree, ...liste.filter((b) => b.id !== ticket.id)].slice(0, MAX))
}

export function oublierBillet(id) {
  ecrire(lire().filter((b) => b.id !== id))
}

function abonner(cb) {
  window.addEventListener(EVENEMENT, cb)
  window.addEventListener('storage', cb)
  return () => {
    window.removeEventListener(EVENEMENT, cb)
    window.removeEventListener('storage', cb)
  }
}

export const useMesBillets = () => useSyncExternalStore(abonner, lire)

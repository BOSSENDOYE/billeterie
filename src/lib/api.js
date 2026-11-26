// Client de l'API Django (proxy Vite : /api -> http://127.0.0.1:8000)
import { useCallback, useEffect, useRef, useState } from 'react'

const STAFF_KEY = 'billetterie_staff_code'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export const staffCode = {
  get: () => {
    try {
      return sessionStorage.getItem(STAFF_KEY) || ''
    } catch {
      return ''
    }
  },
  set: (code) => {
    try {
      code ? sessionStorage.setItem(STAFF_KEY, code) : sessionStorage.removeItem(STAFF_KEY)
    } catch {
      /* stockage indisponible : l'utilisateur devra se reconnecter */
    }
    window.dispatchEvent(new Event('staff:change'))
  },
}

async function request(path, { method = 'GET', body, staff = false, code } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (staff) headers['X-Staff-Code'] = code ?? staffCode.get()

  let res
  try {
    res = await fetch(`/api/${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch {
    throw new ApiError('Serveur injoignable. Le backend Django est-il démarré ?', 0)
  }
  const data = await res.json().catch(() => null)
  if (data === null) {
    // Réponse HTML : le serveur Vite ne relaie pas /api vers Django (proxy absent ou mauvais port)
    throw new ApiError(
      `API injoignable (erreur ${res.status}) : ouvrez http://localhost:5173 et vérifiez que Django tourne sur le port 8000.`,
      res.status,
    )
  }
  if (!res.ok) {
    if (res.status === 401 && staff) staffCode.set('')
    throw new ApiError(data.erreur || `Erreur ${res.status}`, res.status)
  }
  return data
}

/** Télécharge un fichier renvoyé par une route du personnel (ex. PDF des billets papier). */
async function telechargerFichier(path, nomFichier) {
  let res
  try {
    res = await fetch(`/api/${path}`, { method: 'POST', headers: { 'X-Staff-Code': staffCode.get() } })
  } catch {
    throw new ApiError('Serveur injoignable.', 0)
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    if (res.status === 401) staffCode.set('')
    throw new ApiError(data.erreur || `Erreur ${res.status}`, res.status)
  }
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = nomFichier
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

export const api = {
  evenement: () => request('evenement'),
  // type : omis = tarif standard en cours (prévente) ; 'vip' ou 'vvip'
  creerPaiement: (nom, telephone, type) => request('paiements', { method: 'POST', body: { nom, telephone, type } }),
  paiement: (ref) => request(`paiements/${ref}`),
  simulerPaiement: (ref) => request(`paiements/${ref}/simuler`, { method: 'POST', body: {} }),
  declarerPaiement: (ref) => request(`paiements/${ref}/declarer`, { method: 'POST', body: {} }),
  ticket: (id) => request(`tickets/${id}`),

  login: (code) => request('staff/login', { method: 'POST', body: {}, staff: true, code }),
  scan: (qr) => request('staff/scan', { method: 'POST', body: { qr }, staff: true }),
  scans: () => request('staff/scans', { staff: true }),
  stats: () => request('staff/stats', { staff: true }),
  tickets: (statut, q, type = 'tous') => request(`staff/tickets?${new URLSearchParams({ statut, q, type })}`, { staff: true }),
  // Billets papier : type = 'jour_j' ou 'prevente'
  billetsPapierPdf: (type = 'jour_j') =>
    telechargerFichier(`staff/billets-physiques?type=${type}`, type === 'prevente' ? 'billets-prevente.pdf' : 'billets-jour-j.pdf'),
  apercuPapierPdf: (type = 'jour_j') => telechargerFichier(`staff/billets-physiques/apercu?type=${type}`, `apercu-billet-${type}.pdf`),
  designPapier: (type = 'jour_j') => request(`staff/billets-physiques/design?type=${type}`, { staff: true }),
  enregistrerDesignPapier: (type, design) =>
    request(`staff/billets-physiques/design?type=${type}`, { method: 'POST', body: { design }, staff: true }),
  reinitialiserTestsJourJ: () => request('staff/billets-jour-j/reinitialiser-tests', { method: 'POST', body: {}, staff: true }),
  reinitialiserTicket: (id) => request(`staff/tickets/${id}/reinitialiser`, { method: 'POST', body: {}, staff: true }),
  venteGuichet: (vente) => request('staff/vente-guichet', { method: 'POST', body: vente, staff: true }),
  paiements: (statut) => request(`staff/paiements?${new URLSearchParams({ statut })}`, { staff: true }),
  validerPaiement: (ref) => request(`staff/paiements/${ref}/valider`, { method: 'POST', body: {}, staff: true }),
  rejeterPaiement: (ref) => request(`staff/paiements/${ref}/rejeter`, { method: 'POST', body: {}, staff: true }),
}

/**
 * Charge une ressource et la rafraîchit périodiquement (synchro « temps réel »
 * entre acheteurs, scanners et tableau de bord).
 */
export function usePolling(fetcher, deps = [], intervalMs = 4000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const reload = useCallback(async () => {
    try {
      const d = await fetcherRef.current()
      setData(d)
      setError(null)
      return d
    } catch (e) {
      setError(e)
    }
  }, [])

  useEffect(() => {
    let actif = true
    const tick = () => actif && document.visibilityState === 'visible' && reload()
    reload()
    const id = intervalMs ? setInterval(tick, intervalMs) : null
    return () => {
      actif = false
      clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, error, reload }
}

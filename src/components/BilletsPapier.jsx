import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { formatPrix } from '../lib/format'
import { IconDownload, IconRefresh } from './Icons'
import { btn, input, Spinner } from './ui'

const ORDRE = ['bandeau', 'surtitre', 'titre', 'lieu', 'prix', 'mention']

/** Éditeur des textes et de la couleur du billet papier (les QR codes ne changent pas). */
function EditeurDesign({ type }) {
  const [infos, setInfos] = useState(null)
  const [design, setDesign] = useState({})
  const [etat, setEtat] = useState('')
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    api.designPapier(type).then(
      (d) => {
        setInfos(d)
        setDesign(d.design)
      },
      (e) => setErreur(e.message),
    )
  }, [type])

  if (!infos) return erreur ? <p className="mt-4 text-sm text-red-400">{erreur}</p> : <Spinner className="mt-4 h-5 w-5" />

  const changer = (cle, valeur) => {
    setDesign((d) => ({ ...d, [cle]: valeur }))
    setEtat('')
  }

  async function enregistrer(valeurs = design) {
    setEtat('enregistrement')
    setErreur('')
    try {
      // Une valeur identique au défaut n'est pas enregistrée : elle suivra l'événement (date, prix…)
      const aEnregistrer = Object.fromEntries(Object.entries(valeurs).filter(([k, v]) => v && v !== infos.defaut[k]))
      const d = await api.enregistrerDesignPapier(type, aEnregistrer)
      setInfos(d)
      setDesign(d.design)
      setEtat('enregistre')
      return true
    } catch (e) {
      setErreur(e.message)
      setEtat('')
      return false
    }
  }

  async function apercu() {
    if (!(await enregistrer())) return
    try {
      await api.apercuPapierPdf(type)
    } catch (e) {
      setErreur(e.message)
    }
  }

  return (
    <div className="mt-4 space-y-4 border-t border-line pt-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {ORDRE.map((cle) => (
          <label key={cle} className={`block ${cle === 'lieu' ? 'sm:col-span-2' : ''}`}>
            <span className="text-xs text-muted">{infos.champs[cle].libelle}</span>
            <input
              value={design[cle] ?? ''}
              maxLength={infos.champs[cle].max}
              onChange={(e) => changer(cle, e.target.value)}
              placeholder={infos.defaut[cle]}
              className={`${input} mt-1 py-2.5 text-sm`}
            />
          </label>
        ))}
        <label className="block">
          <span className="text-xs text-muted">{infos.champs.couleur.libelle}</span>
          <span className="mt-1 flex items-center gap-3">
            <input
              type="color"
              value={design.couleur ?? infos.defaut.couleur}
              onChange={(e) => changer('couleur', e.target.value.toUpperCase())}
              className="h-11 w-16 cursor-pointer rounded-lg border border-line bg-transparent"
            />
            <span className="font-mono text-sm text-muted">{design.couleur}</span>
          </span>
        </label>
      </div>
      <p className="text-xs text-muted">Les QR codes ne changent pas : modifier le design n'invalide aucun billet déjà imprimé.</p>
      {erreur && <p className="text-sm text-red-400">{erreur}</p>}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => enregistrer()} disabled={etat === 'enregistrement'} className={`${btn.gold} py-2.5 text-sm`}>
          {etat === 'enregistrement' ? <Spinner className="h-4 w-4 border-ink/25 border-t-ink" /> : etat === 'enregistre' ? 'Enregistré ✓' : 'Enregistrer le design'}
        </button>
        <button onClick={apercu} className={`${btn.ghost} py-2.5 text-sm`}>
          <IconDownload className="h-4 w-4" /> Aperçu (1 page PDF)
        </button>
        <button onClick={() => confirm('Revenir au design par défaut ?') && enregistrer({})} className={`${btn.ghost} py-2.5 text-sm`}>
          Design par défaut
        </button>
      </div>
    </div>
  )
}

// Textes et réglages propres à chaque série de billets papier
const SERIES = {
  jour_j: { titre: 'Billets Jour J à imprimer', nom: 'Jour J', cadre: 'border-ruby/40', bouton: 'border-ruby/60 text-ruby-light', accent: 'text-ruby-light' },
  prevente: { titre: 'Billets Prévente à imprimer', nom: 'Prévente', cadre: 'border-gold/40', bouton: 'border-gold/60 text-gold-light', accent: 'text-gold-light' },
}
const PAPIER_PREVENTE = 100

/** Billets vendus en papier (Jour J ou Prévente) : impression, remise à zéro des tests (Jour J), design. */
export default function BilletsPapier({ evenement: ev, serie, onChange, type = 'jour_j' }) {
  const conf = SERIES[type]
  const jourJ = type === 'jour_j'
  const prix = jourJ ? ev.prix_jour_j : ev.prix_prevente
  const nombre = jourJ ? ev.quota_jour_j : PAPIER_PREVENTE
  const [envoi, setEnvoi] = useState('')
  const [erreur, setErreur] = useState('')
  const [info, setInfo] = useState('')
  const [editeur, setEditeur] = useState(false)
  const dejaImprimes = serie.physiques > 0
  // Remise à zéro des tests : Jour J uniquement (en prévente, les billets hors papier sont de vraies ventes en ligne)
  const aRemettre = jourJ ? (serie.hors_papier ?? 0) + (serie.physiques_entres ?? 0) : 0

  async function action(nom, fn) {
    setEnvoi(nom)
    setErreur('')
    setInfo('')
    try {
      await fn()
      onChange?.()
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnvoi('')
    }
  }

  function telecharger() {
    const message = dejaImprimes
      ? `Télécharger le PDF des billets ${conf.nom} ? (mêmes billets, mêmes QR codes)`
      : `Émettre ${nombre} billets ${conf.nom} en papier ?` +
        (jourJ ? '' : `\n\nIls sont pris sur les places de prévente (numéros PV-${String(ev.quota_prevente - nombre + 1).padStart(3, '0')} à PV-${ev.quota_prevente}) et ne seront plus vendus en ligne.`) +
        "\n\nIls deviennent valides tout de suite : gardez-les en lieu sûr jusqu'à leur vente."
    if (confirm(message)) action('pdf', () => api.billetsPapierPdf(type))
  }

  function remettreAZero() {
    const message =
      `Remettre à zéro ${aRemettre} billet(s) Jour J utilisé(s) pour les tests ?\n\n` +
      'Les billets vendus hors papier redeviennent disponibles et les entrées des billets papier sont annulées.\n' +
      'À ne pas faire pendant le concert.'
    if (!confirm(message)) return
    action('reset', async () => {
      const { reinitialises } = await api.reinitialiserTestsJourJ()
      setInfo(reinitialises.length ? `Remis à zéro : ${reinitialises.join(', ')}` : 'Aucun billet à remettre à zéro.')
    })
  }

  return (
    <section className={`mt-6 rounded-2xl border bg-surface p-5 ${conf.cadre}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <h2 className="font-semibold">{conf.titre}</h2>
          <p className="mt-1 text-sm text-muted">
            PDF de {nombre} billets ({formatPrix(prix)}), 4 grands billets par page A4 avec traits de coupe. Chaque QR code ne permet qu'une seule
            entrée.{!jourJ && ' Les billets Prévente vendus en ligne ne changent pas.'}
          </p>
          <p className="mt-2 text-sm">
            <span className={conf.accent}>
              {serie.physiques ?? 0} / {nombre} imprimés
            </span>
            <span className="text-muted"> · {serie.physiques_entres ?? 0} entrés</span>
            {jourJ && serie.hors_papier > 0 && <span className="text-amber-300"> · {serie.hors_papier} vendu(s) hors papier</span>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {aRemettre > 0 && (
            <button onClick={remettreAZero} disabled={!!envoi} className={`${btn.ghost} border-amber-400/50 py-2.5 text-sm text-amber-300`}>
              {envoi === 'reset' ? <Spinner className="h-4 w-4" /> : <IconRefresh className="h-4 w-4" />}
              Remettre à zéro les tests ({aRemettre})
            </button>
          )}
          <button onClick={telecharger} disabled={!!envoi} className={`${btn.ghost} py-2.5 text-sm ${conf.bouton}`}>
            {envoi === 'pdf' ? <Spinner className="h-4 w-4" /> : <IconDownload className="h-4 w-4" />}
            {dejaImprimes ? 'Télécharger le PDF' : 'Télécharger les billets (PDF)'}
          </button>
          <button onClick={() => setEditeur((v) => !v)} className={`${btn.ghost} py-2.5 text-sm`}>
            {editeur ? 'Fermer le design' : 'Modifier le design'}
          </button>
        </div>
      </div>
      {jourJ && serie.hors_papier > 0 && (
        <p className="mt-3 rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
          {serie.hors_papier} billet(s) Jour J ont été vendus hors papier (tests au guichet ?) : ils ne sont pas dans le PDF. « Remettre à
          zéro les tests » les rend de nouveau imprimables.
        </p>
      )}
      {info && <p className="mt-3 text-sm text-emerald-300">{info}</p>}
      {erreur && <p className="mt-3 text-sm text-red-400">{erreur}</p>}
      {editeur && <EditeurDesign type={type} />}
    </section>
  )
}

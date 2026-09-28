import { toBlob } from 'html-to-image'

// Éléments animés à ne pas figer dans l'image (reflet doré)
const exclure = (node) => !(node instanceof Element && node.classList.contains('animate-shine'))

async function capturer(node, skipFonts) {
  const options = {
    pixelRatio: 3, // QR code net, même en grand
    backgroundColor: '#0A0A0B',
    cacheBust: true,
    filter: exclure,
    skipFonts,
  }
  // Safari n'affiche pas toujours les images au premier rendu : on rend deux fois
  await toBlob(node, options)
  return toBlob(node, options)
}

/** Génère l'image PNG du billet affiché. */
export async function genererImageBillet(node) {
  let blob
  try {
    blob = await capturer(node, false)
  } catch {
    blob = await capturer(node, true) // polices distantes indisponibles : polices système
  }
  if (!blob) throw new Error("Impossible de générer l'image du billet")
  return blob
}

/**
 * Enregistre l'image du billet :
 * - menu de partage du téléphone (« Enregistrer l'image » → Pellicule / Galerie),
 * - sinon téléchargement du fichier (ordinateur, ou navigateur sans partage de fichiers).
 * À appeler directement dans le clic : Safari exige que le partage suive le geste de l'utilisateur,
 * d'où l'image préparée à l'avance avec genererImageBillet.
 * Retourne 'partage', 'telecharge' ou 'annule'.
 */
export async function enregistrerImageBillet(blob, nomFichier) {
  const fichier = new File([blob], nomFichier, { type: 'image/png' })

  if (navigator.canShare?.({ files: [fichier] })) {
    try {
      await navigator.share({ files: [fichier], title: 'Mon billet' })
      return 'partage'
    } catch (e) {
      if (e?.name === 'AbortError') return 'annule'
      // Partage refusé par le navigateur : on bascule sur le téléchargement
    }
  }

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nomFichier
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
  return 'telecharge'
}

import { prepareZXingModule, readBarcodes } from 'zxing-wasm/reader'
import wasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url'

// Moteur ZXing servi par notre propre site (pas de dépendance à un CDN le jour de l'événement).
// Objet unique : ZXing réutilise le module tant que les « overrides » sont identiques.
const OVERRIDES = { locateFile: (chemin, prefixe) => (chemin.endsWith('.wasm') ? wasmUrl : prefixe + chemin) }
prepareZXingModule({ overrides: OVERRIDES })

// Taille maximale de l'image analysée (compromis vitesse / portée)
const COTE_MAX = 1280

// Réglages ZXing : robustes au flou, au biais, aux reflets et aux écrans en mode sombre
const OPTIONS_ZXING = {
  formats: ['QRCode'],
  tryHarder: true,
  tryInvert: true,
  tryRotate: true,
  maxNumberOfSymbols: 1,
}

/** Charge le moteur à l'avance (appelé à l'ouverture de la page du scanner). */
export function prechargerLecteur() {
  prepareZXingModule({ overrides: OVERRIDES, fireImmediately: true }).catch(() => {})
}

async function detecteurNatif() {
  if (!('BarcodeDetector' in window)) return null
  try {
    const formats = await window.BarcodeDetector.getSupportedFormats()
    return formats.includes('qr_code') ? new window.BarcodeDetector({ formats: ['qr_code'] }) : null
  } catch {
    return null
  }
}

/**
 * Lecteur de QR code sur la caméra arrière.
 * L'image entière est analysée : le QR est trouvé où qu'il soit dans le champ.
 * Moteur ZXing à chaque image ; sur Android, le détecteur natif du téléphone est essayé en alternance.
 */
export async function demarrerScanner(video, onCode) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
  })
  video.setAttribute('playsinline', '')
  video.muted = true
  video.srcObject = stream
  await video.play()

  const track = stream.getVideoTracks()[0]
  track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] }).catch(() => {})

  const natif = await detecteurNatif()
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  let arrete = false
  let tour = 0

  async function lireZxing() {
    const w = video.videoWidth
    const h = video.videoHeight
    if (!w || !h) return null
    const echelle = Math.min(1, COTE_MAX / Math.max(w, h))
    canvas.width = Math.round(w * echelle)
    canvas.height = Math.round(h * echelle)
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const resultats = await readBarcodes(ctx.getImageData(0, 0, canvas.width, canvas.height), OPTIONS_ZXING)
    return resultats.find((r) => r.isValid)?.text ?? null
  }

  async function lireNatif() {
    const codes = await natif.detect(video)
    return codes[0]?.rawValue ?? null
  }

  async function boucle() {
    if (arrete) return
    if (video.readyState >= 2) {
      try {
        tour += 1
        const texte = natif && tour % 2 === 0 ? await lireNatif() : await lireZxing()
        if (texte && !arrete) onCode(texte)
      } catch {
        /* image illisible : on continue */
      }
    }
    setTimeout(boucle, 60)
  }
  boucle()

  const capacites = track.getCapabilities?.() ?? {}
  return {
    torcheDispo: Boolean(capacites.torch),
    torche: (allumee) => track.applyConstraints({ advanced: [{ torch: allumee }] }),
    arreter() {
      arrete = true
      stream.getTracks().forEach((t) => t.stop())
      video.srcObject = null
    },
  }
}

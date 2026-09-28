import { useState } from 'react'

/** Photo de l'artiste en fond ; dégradé noir/or de secours si l'image est absente. */
export default function ArtistePhoto({ src, alt = '', className = '' }) {
  const [erreur, setErreur] = useState(false)

  if (erreur || !src) {
    return (
      <div className={`absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,var(--color-gold-dark),var(--color-ink)_65%)] ${className}`} />
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setErreur(true)}
      className={`absolute inset-0 h-full w-full object-cover object-top ${className}`}
    />
  )
}

// Apparence des deux séries de billets. Classes Tailwind écrites en entier (détectées au build).
export const TYPES = {
  prevente: {
    label: 'Prévente',
    bandeau: 'PRÉVENTE',
    cadre: 'bg-gradient-gold shadow-gold/10',
    titre: 'text-gradient-gold',
    accent: 'text-gold',
    accentClair: 'text-gold-light',
    champ: 'text-gold/80',
    bordure: 'border-gold/50',
    anneau: 'ring-gold/60',
    pointilles: 'border-gold/40',
    reflet: 'via-gold-light/10',
    teinte: '',
    ruban: 'bg-gradient-gold text-ink',
    badge: 'border-gold/50 bg-gold/15 text-gold-light',
    pleinEcran: 'bg-[#D4AF37] text-[#0A0A0B]',
  },
  jour_j: {
    label: 'Jour J',
    bandeau: 'JOUR J',
    cadre: 'bg-gradient-ruby shadow-ruby/25',
    titre: 'text-gradient-ruby',
    accent: 'text-ruby',
    accentClair: 'text-ruby-light',
    champ: 'text-ruby-light/80',
    bordure: 'border-ruby/60',
    anneau: 'ring-ruby/60',
    pointilles: 'border-ruby/50',
    reflet: 'via-ruby-light/10',
    teinte: 'bg-ruby-dark/35 mix-blend-multiply',
    ruban: 'bg-gradient-ruby text-white',
    badge: 'border-ruby/60 bg-ruby/15 text-ruby-light',
    pleinEcran: 'bg-[#E0314B] text-white',
  },
}

export const typeBillet = (type) => TYPES[type] ?? TYPES.prevente

export const formatPrix = (n) => `${Number(n).toLocaleString('fr-FR')} FCFA`

export const numeroFormat = (n, total = 300) => `${String(n).padStart(3, '0')}/${total}`

const fmt = (iso, opts) => (iso ? new Intl.DateTimeFormat('fr-FR', { timeZone: 'Africa/Dakar', ...opts }).format(new Date(iso)) : '—')

export const dateCourte = (iso) => fmt(iso, { dateStyle: 'short', timeStyle: 'short' })
export const heure = (iso) => fmt(iso, { timeStyle: 'medium' })

export function dateEvenement(iso) {
  const longue = fmt(iso, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  return {
    longue: longue.charAt(0).toUpperCase() + longue.slice(1),
    jour: fmt(iso, { day: '2-digit' }),
    mois: fmt(iso, { month: 'short' }).replace('.', '').toUpperCase(),
    annee: fmt(iso, { year: 'numeric' }),
    heure: fmt(iso, { hour: '2-digit', minute: '2-digit' }).replace(':', 'h'),
  }
}

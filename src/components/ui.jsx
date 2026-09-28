import { IconAlert, IconTicket } from './Icons'

export function Logo({ className = '', compact = false }) {
  return (
    <span className={`flex items-center gap-2.5 ${className}`}>
      <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-gold text-ink shadow-lg shadow-gold/20">
        <IconTicket className="h-5 w-5" />
      </span>
      <span className={`leading-tight ${compact ? 'hidden sm:block' : ''}`}>
        <span className="block font-display text-lg font-bold tracking-wide text-cream">Guichet</span>
        <span className="block text-[10px] font-semibold uppercase tracking-[0.3em] text-gold">Billetterie</span>
      </span>
    </span>
  )
}

export function Spinner({ className = 'h-8 w-8' }) {
  return <span className={`inline-block animate-spin rounded-full border-2 border-gold/25 border-t-gold ${className}`} />
}

export function PageLoader() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <Spinner />
    </div>
  )
}

export function ErrorState({ message, action }) {
  return (
    <div className="mx-auto grid min-h-[50vh] max-w-md place-items-center px-4 text-center">
      <div className="animate-fade-in">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-full border border-red-500/30 bg-red-500/10 text-red-400">
          <IconAlert className="h-6 w-6" />
        </span>
        <p className="mt-4 text-cream">{message}</p>
        {action && <div className="mt-6">{action}</div>}
      </div>
    </div>
  )
}

export const btn = {
  gold: 'inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-gold px-5 py-3.5 font-semibold text-ink shadow-lg shadow-gold/15 transition hover:brightness-110 active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-40',
  ghost: 'inline-flex items-center justify-center gap-2 rounded-xl border border-line px-5 py-3 font-medium text-cream transition hover:border-gold/50 hover:text-gold-light active:scale-[.98]',
}

export const input =
  'w-full rounded-xl border border-line bg-ink/60 px-4 py-3.5 text-cream placeholder:text-muted/60 outline-none transition focus:border-gold focus:ring-4 focus:ring-gold/10'

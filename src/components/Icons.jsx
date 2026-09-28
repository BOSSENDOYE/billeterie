// Jeu d'icônes SVG (trait 1.75, style Lucide)
const Svg = ({ children, className = 'h-5 w-5', ...p }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true" {...p}>
    {children}
  </svg>
)

export const IconTicket = (p) => (
  <Svg {...p}><path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4z" /><path d="M14 6v2m0 3v2m0 3v2" /></Svg>
)
export const IconCalendar = (p) => (
  <Svg {...p}><rect x="3" y="4.5" width="18" height="16" rx="2" /><path d="M3 9.5h18M8 2.5v4M16 2.5v4" /></Svg>
)
export const IconPin = (p) => (
  <Svg {...p}><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></Svg>
)
export const IconClock = (p) => (
  <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Svg>
)
export const IconShield = (p) => (
  <Svg {...p}><path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z" /><path d="m9 12 2 2 4-4" /></Svg>
)
export const IconQr = (p) => (
  <Svg {...p}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M17 20h4v-3" /></Svg>
)
export const IconBolt = (p) => (
  <Svg {...p}><path d="M13 2 4 14h7l-1 8 9-12h-7z" /></Svg>
)
export const IconScan = (p) => (
  <Svg {...p}><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10" /></Svg>
)
export const IconChart = (p) => (
  <Svg {...p}><path d="M3 3v18h18" /><path d="M7 15v2M11 11v6M15 7v10M19 12v5" /></Svg>
)
export const IconCheck = (p) => (
  <Svg {...p}><path d="m5 12.5 4.5 4.5L19 7.5" /></Svg>
)
export const IconX = (p) => (
  <Svg {...p}><path d="M6 6l12 12M18 6 6 18" /></Svg>
)
export const IconAlert = (p) => (
  <Svg {...p}><path d="M12 3 2 20h20z" /><path d="M12 10v4M12 17v.01" /></Svg>
)
export const IconLock = (p) => (
  <Svg {...p}><rect x="4" y="10.5" width="16" height="10.5" rx="2" /><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" /></Svg>
)
export const IconDownload = (p) => (
  <Svg {...p}><path d="M12 3v12m0 0-4.5-4.5M12 15l4.5-4.5M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" /></Svg>
)
export const IconArrow = (p) => (
  <Svg {...p}><path d="M5 12h14m-5-5 5 5-5 5" /></Svg>
)
export const IconRefresh = (p) => (
  <Svg {...p}><path d="M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16m0 4v-4h-4" /></Svg>
)
export const IconSearch = (p) => (
  <Svg {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Svg>
)
export const IconLogout = (p) => (
  <Svg {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></Svg>
)
export const IconCamera = (p) => (
  <Svg {...p}><path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" /><circle cx="12" cy="13.5" r="3.5" /></Svg>
)

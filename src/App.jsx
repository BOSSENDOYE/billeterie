import { Navigate, Routes, Route, useLocation } from 'react-router-dom'
import MusiquePlayer from './components/MusiquePlayer'
import Navbar from './components/Navbar'
import StaffGate from './components/StaffGate'
import Accueil from './pages/Accueil'
import Paiement from './pages/Paiement'
import Billet from './pages/Billet'
import MesBillets from './pages/MesBillets'
import Scanner from './pages/Scanner'
import Admin from './pages/Admin'

function Footer() {
  return (
    <footer className="no-print border-t border-line/60 py-8 text-center text-xs text-muted">
      <p>Paiement sécurisé via Wave · Billets nominatifs à QR code signé · Un billet = une entrée</p>
      <p className="mt-1 text-muted/60">© {new Date().getFullYear()} Guichet Billetterie</p>
    </footer>
  )
}

export default function App() {
  const { pathname } = useLocation()
  // Pages de l'équipe (scanner, tableau de bord) : autonomes, accessibles uniquement par leur lien,
  // sans l'en-tête ni le pied de page du site public, et sans musique
  const pageEquipe = pathname.startsWith('/scan') || pathname.startsWith('/admin')
  const externe = pageEquipe

  return (
    <div className="flex min-h-dvh flex-col">
      {!externe && <Navbar />}
      <div className="flex-1">
        <Routes>
          <Route path="/" element={<Accueil />} />
          <Route path="/paiement/:reference" element={<Paiement />} />
          <Route path="/billet/:id" element={<Billet />} />
          <Route path="/mes-billets" element={<MesBillets />} />
          <Route path="/scan" element={<StaffGate titre="Contrôle d'accès"><Scanner /></StaffGate>} />
          <Route path="/scanner" element={<Navigate to="/scan" replace />} />
          <Route path="/admin" element={<StaffGate titre="Tableau de bord"><Admin /></StaffGate>} />
          <Route path="*" element={<p className="p-16 text-center text-muted">Page introuvable</p>} />
        </Routes>
      </div>
      {!externe && <Footer />}
      <MusiquePlayer actif={!pageEquipe} ecranEntree={pathname === '/'} />
    </div>
  )
}

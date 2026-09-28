# Billetterie QR — Dip Doundou Guiss à Mboro

Frontend React (Vite + Tailwind) à la racine, backend Django + MySQL dans `backend/`.

## Démarrer

1. **MySQL** : démarrer MySQL depuis le panneau XAMPP.
2. **Backend** (terminal 1) :
   ```
   cd backend
   .venv\Scripts\activate
   python manage.py migrate        # première fois
   python manage.py seed_demo      # première fois uniquement : crée l'événement + 300 billets (EFFACE les ventes)
   python manage.py runserver 0.0.0.0:8000
   ```
3. **Frontend** (terminal 2, à la racine) : `npm run dev` puis ouvrir http://localhost:5173

## Pages

| URL | Rôle |
| --- | --- |
| `/` | Présentation du concert et achat |
| `/paiement/:ref` | Paiement via le lien marchand Wave |
| `/billet/:id` | E-billet horizontal avec QR code signé |
| `/scan` | Scanner autonome pour les contrôleurs, hors du site public (code personnel) |
| `/admin` | Tableau de bord (code personnel) |
| `/django-admin/` | Admin Django (`python manage.py createsuperuser`) |

Code d'accès personnel par défaut : `or2026` (variable `STAFF_ACCESS_CODE` dans `backend/.env`).

## Paiement Wave

Le lien marchand (`WAVE_MERCHANT_URL` dans `backend/.env`) encaisse le paiement mais ne prévient pas le site. Circuit :

1. L'acheteur clique sur « Payer avec Wave » (lien marchand avec `?amount=2500`).
2. Il clique sur « J'ai payé » → paiement « à vérifier ».
3. Dans le tableau de bord, l'équipe retrouve le paiement dans Wave Business (numéro Wave + montant) et clique sur **Confirmer** (ou **Rejeter**).
4. Le billet s'affiche automatiquement chez l'acheteur.

Pour une confirmation 100 % automatique, il faut l'API Wave Business (clé API + webhook).

## Sécurité des billets

- Le QR contient `{id, sig}` ; `sig` est un HMAC-SHA256 calculé avec `TICKET_SIGNING_KEY`, connue du serveur seul.
- Le scan verrouille la ligne en base (`SELECT … FOR UPDATE`) : un même billet ne peut pas entrer deux fois, même scanné simultanément sur deux téléphones.
- La confirmation de paiement est idempotente : une double validation ne vend pas deux billets.

Tests : `cd backend && .venv\Scripts\python manage.py test billetterie`

## Déploiement

Docker + Nginx sur le VPS Hostinger (billet.cml-sst.com) : voir [DEPLOIEMENT.md](DEPLOIEMENT.md).

## Passage en production

- `DJANGO_DEBUG=0`, clés secrètes neuves, `ENGINE` → `django.db.backends.mysql` sur MariaDB ≥ 10.5 / MySQL 8.
- Servir en HTTPS (indispensable pour la caméra du scanner sur téléphone).

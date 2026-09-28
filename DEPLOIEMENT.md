# Déploiement sur le VPS Hostinger — billet.cml-sst.com

Architecture :

```
Internet ──► Nginx du VPS (80/443, HTTPS)
               └─► 127.0.0.1:1654  conteneur web     (site React + relais /api)
                                     └─► backend:8000 conteneur backend (Django/Gunicorn) — aussi sur 127.0.0.1:1655
                                                        └─► db:3306 conteneur MariaDB — aussi sur 127.0.0.1:1657
```

Les ports 1654, 1655 et 1657 n'écoutent que sur `127.0.0.1` : ils ne sont pas accessibles depuis Internet.

## 1. DNS (hPanel Hostinger)

Domaines → cml-sst.com → DNS / Nameservers → ajouter :

| Type | Nom | Valeur | TTL |
| --- | --- | --- | --- |
| A | `billet` | adresse IP du VPS | 3600 |

Vérifier (peut prendre quelques minutes) : `ping billet.cml-sst.com`

## 2. Docker sur le VPS (si absent)

```bash
docker --version && docker compose version
# sinon :
curl -fsSL https://get.docker.com | sudo sh
```

## 3. Récupérer le projet

```bash
cd /opt
sudo git clone https://github.com/BOSSENDOYE/billeterie.git
cd billeterie
```

## 4. Configuration

```bash
sudo cp .env.production.example .env
sudo nano .env
```

Remplacer chaque `A_CHANGER`. Pour générer des valeurs aléatoires :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(40))"
```

- `STAFF_ACCESS_CODE` : le code du scanner et du tableau de bord (à communiquer à l'équipe).
- `PAIEMENT_SIMULE=0` pour les vraies ventes (1 = démonstration, billet sans payer).
- Ne jamais committer ce fichier `.env`.

## 5. Lancer les conteneurs

```bash
sudo docker compose up -d --build
sudo docker compose ps          # 3 services « Up », db « healthy »
curl -I http://127.0.0.1:1654   # doit répondre 200
```

Au premier démarrage, le backend crée les tables, l'événement et les 300 billets.
Les redémarrages suivants ne touchent pas aux ventes.

## 6. Nginx du VPS

```bash
sudo cp deploy/nginx/billet.cml-sst.com.conf /etc/nginx/sites-available/billet.cml-sst.com
sudo ln -s /etc/nginx/sites-available/billet.cml-sst.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 7. HTTPS (obligatoire pour la caméra du scanner)

```bash
sudo apt install -y certbot python3-certbot-nginx   # si absent
sudo certbot --nginx -d billet.cml-sst.com
```

Le site est alors sur **https://billet.cml-sst.com**.

| Page | Adresse |
| --- | --- |
| Billetterie | https://billet.cml-sst.com |
| Scanner (équipe) | https://billet.cml-sst.com/scan |
| Tableau de bord | https://billet.cml-sst.com/admin |
| Admin Django | https://billet.cml-sst.com/django-admin/ (`sudo docker compose exec backend python manage.py createsuperuser`) |

## Mises à jour

Après un `git push` depuis le PC :

```bash
cd /opt/billeterie && sudo sh deploy/deploy.sh
```

## Commandes utiles

```bash
sudo docker compose logs -f backend        # journaux Django
sudo docker compose restart backend        # après modification du .env
# Sauvegarde de la base :
sudo docker compose exec db sh -c 'mariadb-dump -u root -p"$MARIADB_ROOT_PASSWORD" billetterie' > sauvegarde.sql
```

⚠️ `docker compose down -v` supprime la base (ventes comprises) : ne pas utiliser `-v` en production.

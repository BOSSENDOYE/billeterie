#!/bin/sh
set -e

echo "Attente de la base de données..."
python - <<'PY'
import os, time, MySQLdb
for _ in range(60):
    try:
        MySQLdb.connect(host=os.environ['DB_HOST'], port=int(os.environ.get('DB_PORT', 3306)),
                        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD']).close()
        break
    except MySQLdb.OperationalError:
        time.sleep(2)
else:
    raise SystemExit('Base de données injoignable')
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput -v 0
# Crée l'événement et ses 300 billets au premier démarrage uniquement
python manage.py seed_demo --si-vide

exec "$@"

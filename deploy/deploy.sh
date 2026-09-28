#!/bin/sh
# Mise à jour sur le VPS : récupère le code et reconstruit les conteneurs.
set -e
cd "$(dirname "$0")/.."
git pull --ff-only
docker compose up -d --build
docker compose ps

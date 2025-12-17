#!/bin/bash
# TriForce Docker Wrapper - Lädt immer die richtigen Variablen

DOCKER_DIR="${HOME}/triforce/docker"
ENV_FILE="${HOME}/triforce/config/triforce.env"

# Alle alten ENV-Vars entfernen
unset MYSQL_ROOT_PASSWORD WORDPRESS_DB_PASSWORD SEARXNG_SECRET_KEY
unset MYSQL_PASSWORD WORDPRESS_DB_HOST WORDPRESS_DB_USER

# Config laden
set -a
source "$ENV_FILE"
set +a

cd "$DOCKER_DIR"
docker compose "$@"

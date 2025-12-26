#!/bin/sh
set -eu

# Renewal loop: uses the docker CLI to run the certbot/dns-cloudflare image
# Mounts:
# - /workspace/certbot/conf -> /etc/letsencrypt (certs)
# - /workspace/secrets/cloudflare.ini -> cloudflare credentials
# Requires access to docker socket to `docker exec` reload nginx container.

PROJECT=${COMPOSE_PROJECT_NAME:-docker}
CERT_DIR=/workspace/certbot/conf
CLOUDFLARE_INI=/workspace/secrets/cloudflare.ini

echo "Starting certbot renew loop (project=${PROJECT})"
while true; do
  echo "[certbot] running renew at $(date)"
  docker run --rm \
    -v "$CERT_DIR":/etc/letsencrypt \
    -v "$CLOUDFLARE_INI":/etc/letsencrypt/cloudflare.ini:ro \
    certbot/dns-cloudflare:latest \
    renew \
      --dns-cloudflare \
      --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
      --dns-cloudflare-propagation-seconds 30 \
      --non-interactive \
      --deploy-hook "docker exec ${PROJECT}_nginx nginx -s reload" || true

  echo "[certbot] sleeping 12 hours"
  sleep 43200
done

#!/bin/bash
# Génère un certificat auto-signé pour le développement local.
# Pour la production, utilisez Let's Encrypt (certbot) ou un CA reconnu.
set -e

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/server.key" \
  -out    "$CERT_DIR/server.crt" \
  -subj "/C=FR/ST=France/L=Paris/O=TradingBot/CN=localhost" \
  2>/dev/null

echo "Certificats auto-signés générés dans nginx/certs/"
echo "Usage dev : docker compose -f docker-compose.yml -f docker-compose.dev.yml up"

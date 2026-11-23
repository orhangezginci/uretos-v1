#!/usr/bin/env bash
set -euo pipefail

echo "--- Starte uretOS Dev-Reset ---"

# 1. Laufende Tenant-Container (Postgres & Redis) direkt stoppen und entfernen
containers=$(docker ps -aq --filter "name=tenant-")
if [ -n "$containers" ]; then
  echo "Entferne alte Tenant-Container..."
  docker rm -f $containers
fi

# 2. Docker Compose Services stoppen und ALLE Volumes (inkl. RabbitMQ & System-Postgres) löschen
echo "Stoppe Docker Compose Stack und bereinige Volumes..."
docker compose down -v

# 3. Restliche Tenant-Volumes manuell bereinigen (falls welche übrig sind)
volumes=$(docker volume ls -q --filter "name=tenant-")
if [ -n "$volumes" ]; then
  echo "Entferne verwaiste Tenant-Volumes..."
  docker volume rm $volumes
fi

# 4. TimescaleDB Test-Images optional bereinigen (optional, sorgt für frischen Pull)
images=$(docker images -q "timescale/timescaledb" 2>/dev/null || true)
if [ -n "$images" ]; then
  echo "Bereinige TimescaleDB Cache-Images..."
  docker rmi -f $images || true
fi

echo "--- Reset abgeschlossen! Umgebung ist wieder komplett sauber. ---"
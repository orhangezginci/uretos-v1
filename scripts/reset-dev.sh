#!/usr/bin/env bash
set -euo pipefail

# 1. Tenant-Container (Postgres UND Redis) entfernen
containers=$(docker ps -aq --filter "name=^/tenant-")
if [ -n "$containers" ]; then
  docker rm -f $containers
fi

# 2. Compose-Services und deren Volumes entfernen
docker compose down -v

# 3. Tenant-Volumes entfernen (die kennt Compose nicht)
volumes=$(docker volume ls -q --filter "name=^tenant-")
if [ -n "$volumes" ]; then
  docker volume rm $volumes
fi

images=$(docker images -q "timescale/timescaledb" 2>/dev/null || true)
if [ -n "$images" ]; then
  docker rmi -f $images || true
fi
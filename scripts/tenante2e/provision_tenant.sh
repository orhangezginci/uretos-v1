#!/usr/bin/env bash
set -e

# Prüfen, ob eine Tenant-ID übergeben wurde
if [ -z "$1" ]; then
    echo "[ERROR] Bitte gib eine Tenant-ID an!"
    echo "Verwendung: $0 <tenant_id>"
    exit 1
fi

TENANT_ID="$1"
GATEWAY_URL="http://localhost:8080"
PREFIX="tenant-${TENANT_ID}"

echo "============================================================"
echo "  uretOS Tenant Provisioning Tool - Tenant: ${TENANT_ID}"
echo "============================================================"

# 1. Gründlicher Cleanup (gleiche Logik wie im Testskript)
echo "[1/2] Räume alte Container und Volumes für '${PREFIX}*' auf..."
CONTAINER_IDS=$(docker ps -aq --filter "name=${PREFIX}")
if [ -n "$CONTAINER_IDS" ]; then
    echo " -> Entferne Container: ${CONTAINER_IDS}"
    docker rm -f -v ${CONTAINER_IDS} >/dev/null 2>&1
fi

VOLUME_NAMES=$(docker volume ls -q --filter "name=${PREFIX}")
if [ -n "$VOLUME_NAMES" ]; then
    echo " -> Entferne Volumes: ${VOLUME_NAMES}"
    docker volume rm -f ${VOLUME_NAMES} >/dev/null 2>&1
fi
echo " -> Cleanup abgeschlossen."

# 2. Tenant Provisionierung anstoßen
echo "[2/2] Trigeere Tenant-Provisionierung am Gateway..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${GATEWAY_URL}/v1/tenants" \
     -H "Content-Type: application/json" \
     -d "{\"tenant_id\": \"${TENANT_ID}\"}")

HTTP_BODY=$(echo "$RESPONSE" | head -n 1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

echo " -> HTTP Status: ${HTTP_CODE}"
echo " -> Antwort:     ${HTTP_BODY}"

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ] || [ "$HTTP_CODE" -eq 202 ]; then
    echo -e "\n[SUCCESS] Tenant '${TENANT_ID}' erfolgreich provisioniert!"
else
    echo -e "\n[FAIL] Provisionierung fehlgeschlagen."
    exit 1
fi
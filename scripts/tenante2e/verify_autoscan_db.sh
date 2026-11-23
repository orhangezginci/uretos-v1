#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
    echo "[ERROR] Bitte Tenant-ID angeben!"
    echo "Verwendung: $0 <tenant_id>"
    exit 1
fi

TENANT_ID="$1"
POSTGRES_CONTAINER="tenant-${TENANT_ID}-postgres"
DB_NAME="tenant_${TENANT_ID//-/_}"
PG_USER="tenant_${TENANT_ID//-/_}"
TIMEOUT=30
ELAPSED=0

echo "============================================================"
echo "  uretOS Autoscan & DB Validation - Tenant: ${TENANT_ID}"
echo "============================================================"

echo "[1/2] Warte auf Poller-Discovery und Autoscan-Processing (max. ${TIMEOUT}s)..."

while [ $ELAPSED -lt $TIMEOUT ]; do
    RAW_RESULT=$(docker exec -i "${POSTGRES_CONTAINER}" psql -U "${PG_USER}" -d "${DB_NAME}" -t -A -c \
      "SELECT machine_id, box_id, name, metadata->>'manufacturer', metadata->>'machine_type' FROM machines ORDER BY box_id, machine_id;" 2>/dev/null || true)
    
    if [ -n "$RAW_RESULT" ]; then
        break
    fi
    
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo "  .. Warte auf DB-Einträge (${ELAPSED}/${TIMEOUT}s)..."
done

echo -e "\n[2/2] Validiere Tenant-Datenbank '${POSTGRES_CONTAINER}'..."

if [ -z "$RAW_RESULT" ]; then
    echo -e "\n[FAIL] Keine Maschinen in der Tenant-Datenbank '${DB_NAME}' nach ${TIMEOUT}s gefunden!"
    echo "Checke Poller-Logs mit: docker logs uretos-connector-box-poller --tail 30"
    exit 1
else
    echo -e "\n[SUCCESS] Folgende Maschinen wurden erfolgreich in der Tenant-DB registriert:\n"
    echo "MACHINE ID   | BOX ID       | NAME            | HERSTELLER   | TYP"
    echo "----------------------------------------------------------------------------------------"
    echo "$RAW_RESULT" | while IFS='|' read -r mid box name mfr mtype; do
        printf "%-12s | %-12s | %-15s | %-12s | %s\n" "$mid" "$box" "$name" "$mfr" "$mtype"
    done
    
    COUNT=$(echo "$RAW_RESULT" | grep -c .)
    echo -e "\nGesamtanzahl registrierter Maschinen: ${COUNT}"
    
    echo -e "\nZuweisung nach Connector-Boxen:"
    echo "-----------------------------------"
    docker exec -i "${POSTGRES_CONTAINER}" psql -U "${PG_USER}" -d "${DB_NAME}" -c \
      "SELECT box_id, COUNT(*) as machine_count FROM machines GROUP BY box_id;"
fi
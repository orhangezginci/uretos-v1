#!/usr/bin/env bash
set -e

TENANT_ID="${1:-schwarzwald-metallwaren}"
BOX1="box-sw-01"
BOX2="box-sw-02"

echo "============================================================"
echo "  uretOS E2E Pipeline - Tenant: $TENANT_ID"
echo "============================================================"

# 1. Alte Box-Registrierungen aus der System-DB bereinigen
echo "[1/5] Bereinige alte Box-Registrierungen in der System-DB..."
docker exec -i uretos-system-postgres psql -U uretos_system -d uretos_system -c \
    "DELETE FROM connector_boxes WHERE tenant_id='$TENANT_ID'; DELETE FROM tenants WHERE tenant_id='$TENANT_ID';" 2>/dev/null || true

# 2. Tenant provisionieren
echo "[2/5] Starte Tenant-Provisionierung für '$TENANT_ID'..."
./provision_tenant.sh "$TENANT_ID"

echo " -> Warte 30 Sekunden auf Stabilität der Container..."
sleep 30

# 3. Box 1 registrieren und pairen
echo "[3/5] Registriere und paire Box: $BOX1..."
./register_and_pair.sh "$TENANT_ID" "$BOX1"
sleep 2

# 4. Box 2 registrieren und pairen
echo "[4/5] Registriere und paire Box: $BOX2..."
./register_and_pair.sh "$TENANT_ID" "$BOX2"

# 5. Sequenzieller Poller-Lauf über Docker Compose (Erst Box 1, dann Box 2 mit Recreate)
echo " -> Starte Poller für Box 1 ($BOX1)..."
docker stop uretos-connector-box-poller >/dev/null 2>&1 || true
BOX_HARDWARE_ID="$BOX1" MAX_MACHINES_PER_BOX="5" docker compose up -d --force-recreate connector-box-poller

echo " -> Warte 20 Sekunden, bis Box 1 ihr Limit (5) erreicht hat..."
sleep 20

echo " -> Schalte um auf Poller für Box 2 ($BOX2)..."
BOX_HARDWARE_ID="$BOX2" MAX_MACHINES_PER_BOX="5" docker compose up -d --force-recreate connector-box-poller

echo " -> Warte 15 Sekunden, bis Box 2 die verbleibenden Maschinen (3) erfasst hat..."
sleep 15

# 6. Autoscan & DB Validierung
echo "[5/5] Starte Autoscan- und DB-Validierung..."
./verify_autoscan_db.sh "$TENANT_ID"

echo "============================================================"
echo "  [SUCCESS] E2E Pipeline erfolgreich abgeschlossen!"
echo "============================================================"
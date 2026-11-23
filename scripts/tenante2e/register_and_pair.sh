#!/usr/bin/env bash
set -e

# Parameter prüfen
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "[ERROR] Bitte Tenant-ID und Hardware-ID der Box angeben!"
    echo "Verwendung: $0 <tenant_id> <hardware_id>"
    exit 1
fi

TENANT_ID="$1"
HARDWARE_ID="$2"
GATEWAY_URL="http://localhost:8080"
# Fiktive aber eindeutige MAC-Adresse basierend auf der Hardware-ID für Tests
MAC_ADDRESS="AA:BB:CC:DD:EE:$(echo $HARDWARE_ID | tr -dc '0-9' | fold -w2 | head -n1)"
[ -z "$MAC_ADDRESS" ] && MAC_ADDRESS="AA:BB:CC:DD:EE:01"

echo "============================================================"
echo "  uretOS Box Registration & Pairing - Box: ${HARDWARE_ID}"
echo "============================================================"

# 1. Box registrieren
echo "[1/2] Registriere Box '${HARDWARE_ID}' für Tenant '${TENANT_ID}'..."
REG_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${GATEWAY_URL}/v1/connector-boxes" \
     -H "Content-Type: application/json" \
     -d "{
         \"hardware_id\": \"${HARDWARE_ID}\",
         \"mac_address\": \"${MAC_ADDRESS}\",
         \"tenant_id\": \"${TENANT_ID}\"
     }")

REG_BODY=$(echo "$REG_RESPONSE" | head -n 1)
REG_CODE=$(echo "$REG_RESPONSE" | tail -n 1)

echo " -> HTTP Status: ${REG_CODE}"
echo " -> Antwort:     ${REG_BODY}"

if [ "$REG_CODE" -ne 200 ] && [ "$REG_CODE" -ne 201 ]; then
    echo "[FAIL] Registrierung fehlgeschlagen."
    exit 1
fi

# 2. Box pairen
echo -e "\n[2/2] Führe Pairing für Box '${HARDWARE_ID}' aus..."
PAIR_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${GATEWAY_URL}/v1/connector-boxes/pair" \
     -H "Content-Type: application/json" \
     -d "{
         \"hardware_id\": \"${HARDWARE_ID}\"
     }")

PAIR_BODY=$(echo "$PAIR_RESPONSE" | head -n 1)
PAIR_CODE=$(echo "$PAIR_RESPONSE" | tail -n 1)

echo " -> HTTP Status: ${PAIR_CODE}"
echo " -> Antwort:     ${PAIR_BODY}"

if [ "$PAIR_CODE" -eq 200 ]; then
    echo -e "\n[SUCCESS] Box '${HARDWARE_ID}' erfolgreich registriert und gepairt!"
else
    echo -e "\n[FAIL] Pairing fehlgeschlagen."
    exit 1
fi
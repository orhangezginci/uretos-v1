#!/usr/bin/env bash
set -e

TENANT_ID="schwarzwald-metallwaren"
BOX1="sim-box-01"
BOX2="sim-box-02"
GATEWAY_URL="http://localhost:8080"

echo "============================================================"
echo "  uretOS Shopfloor - 100% Automated Clean Startup"
echo "============================================================"

# 1. Compose-Stack komplett stoppen und Volumes bereinigen
echo "[1/6] Bereinige Docker Compose Stack und Volumes..."
docker compose down -v --remove-orphans >/dev/null 2>&1 || true

# 2. Stack frisch bauen und starten
echo "[2/6] Starte Docker-Stack (Build & Up)..."
docker compose up --build -d

# 3. Warten bis die System-DB bereit ist
echo "[3/6] Warte auf Bereitschaft der System-DB..."
until docker exec -i uretos-system-postgres pg_isready -U uretos_system -d uretos_system >/dev/null 2>&1; do
    sleep 2
done

echo " -> Bereinige alte Einträge in der System-DB..."
docker exec -i uretos-system-postgres psql -U uretos_system -d uretos_system -c \
    "DELETE FROM connector_boxes WHERE tenant_id='$TENANT_ID'; DELETE FROM tenants WHERE tenant_id='$TENANT_ID';"

# 4. Tenant provisionieren (inkl. Host-Cleanup für Postgres & Redis)
echo "[4/6] Provisioniere Tenant '$TENANT_ID'..."
PREFIX="tenant-${TENANT_ID}"

CONTAINER_IDS=$(docker ps -aq --filter "name=${PREFIX}")
if [ -n "$CONTAINER_IDS" ]; then
    docker rm -f -v ${CONTAINER_IDS} >/dev/null 2>&1 || true
fi

VOLUME_NAMES=$(docker volume ls -q --filter "name=${PREFIX}")
if [ -n "$VOLUME_NAMES" ]; then
    docker volume rm -f ${VOLUME_NAMES} >/dev/null 2>&1 || true
fi

# Warten bis Gateway API erreichbar ist
until curl -s "${GATEWAY_URL}/healthz" >/dev/null 2>&1; do
    sleep 2
done

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${GATEWAY_URL}/v1/tenants" \
     -H "Content-Type: application/json" \
     -d "{\"tenant_id\": \"${TENANT_ID}\"}")
HTTP_BODY=$(echo "$RESPONSE" | head -n 1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ] || [ "$HTTP_CODE" -eq 202 ]; then
    echo " -> Tenant erfolgreich provisioniert (HTTP ${HTTP_CODE})."
else
    echo " -> [FEHLER] Provisionierung fehlgeschlagen (HTTP ${HTTP_CODE}): $HTTP_BODY"
    exit 1
fi

echo " -> Warte 10 Sekunden auf Stabilität des Tenant-Containers..."
sleep 10

# 5. Boxen automatisch registrieren und pairen (mit Retry-Schleife)
for BOX in "$BOX1" "$BOX2"; do
    echo "[5/6] Registriere und paire Box automatisch: $BOX..."
    MAC_ADDRESS="AA:BB:CC:DD:EE:$(echo $BOX | tr -dc '0-9' | fold -w2 | head -n1)"
    [ -z "$MAC_ADDRESS" ] && MAC_ADDRESS="AA:BB:CC:DD:EE:01"

    # Warten bis das Gateway die Box-Registrierung annehmen kann
    until curl -s -o /dev/null -w "%{http_code}" -X POST "${GATEWAY_URL}/v1/connector-boxes" \
         -H "Content-Type: application/json" \
         -d "{\"hardware_id\": \"${BOX}\", \"mac_address\": \"${MAC_ADDRESS}\", \"tenant_id\": \"${TENANT_ID}\"}" | grep -E "200|201|400" >/dev/null; do
        sleep 2
    done

done

# Pairing direkt nacheinander, damit sich die Boxen beim Start gegenseitig als gepairt sehen
for BOX in "$BOX1" "$BOX2"; do
    curl -s -X POST "${GATEWAY_URL}/v1/connector-boxes/pair" \
         -H "Content-Type: application/json" \
         -d "{\"hardware_id\": \"${BOX}\"}" >/dev/null
done

# 6. Poller steuern & Autoscan ausführen
echo "[6/6] Autoscan-Validierung (Boxen laufen als Compose-Services connector-box-01/02)..."

# Der alte Einzel-Service würde mit Standard-Box-ID ebenfalls pollen (doppelte Telemetrie) -> stoppen, falls vorhanden
if docker compose config --services 2>/dev/null | grep -qx "connector-box-poller"; then
    echo " -> Stoppe Legacy-Service connector-box-poller (ersetzt durch connector-box-01/02)..."
    docker compose rm -sf connector-box-poller >/dev/null 2>&1 || true
fi
POLLERS="${BOX1}=uretos-connector-box-01 ${BOX2}=uretos-connector-box-02"

# Warten, bis die Maschinenzuweisung im Gateway stabil ist (Anzahl 4x in Folge unverändert, max. 120s)
echo " -> Warte auf stabile Maschinenzuweisung im Gateway..."
machine_count() {
    python3 - "$GATEWAY_URL" "$TENANT_ID" <<'PYEOF'
import json, sys, urllib.request
try:
    with urllib.request.urlopen(f"{sys.argv[1]}/v1/machines?tenant_id={sys.argv[2]}", timeout=10) as r:
        print(len(json.load(r)))
except Exception:
    print(-1)
PYEOF
}
LAST_COUNT=-1; STABLE=0
for _ in $(seq 1 40); do
    COUNT=$(machine_count)
    if [ "$COUNT" -gt 0 ] && [ "$COUNT" = "$LAST_COUNT" ]; then STABLE=$((STABLE + 1)); else STABLE=0; fi
    [ "$STABLE" -ge 4 ] && break
    LAST_COUNT="$COUNT"
    sleep 3
done

if [ -f "./verify_autoscan_db.sh" ]; then
    ./verify_autoscan_db.sh "$TENANT_ID"
fi

# ------------------------------------------------------------------
# Abschlussreport: Quelle der Wahrheit ist das Gateway (Boxen + zugewiesene Maschinen)
# ------------------------------------------------------------------
GATEWAY_URL="$GATEWAY_URL" TENANT_ID="$TENANT_ID" POLLERS="$POLLERS" python3 - <<'PYEOF'
import json, os, subprocess, urllib.request

gw = os.environ["GATEWAY_URL"].rstrip("/")
tenant = os.environ["TENANT_ID"]
warnings = []


def get(path):
    with urllib.request.urlopen(gw + path, timeout=15) as r:
        return json.load(r)


def first(d, keys, default="?"):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


try:
    boxes = sorted((b for b in get("/v1/connector-boxes") if b.get("tenant_id") == tenant),
                   key=lambda b: str(b.get("hardware_id")))
except Exception as exc:
    boxes = []
    warnings.append(f"Boxen konnten nicht vom Gateway gelesen werden: {exc}")

try:
    tenant_machines = get(f"/v1/machines?tenant_id={tenant}")
except Exception as exc:
    tenant_machines = []
    warnings.append(f"Maschinenliste konnte nicht gelesen werden: {exc}")

NAME_KEYS = ("name", "machine_name", "machine_id", "uid", "id")
rows = []  # (box, [machines])
for b in boxes:
    hw = b.get("hardware_id")
    try:
        machines = get(f"/v1/connector-boxes/{hw}/machines")
    except Exception as exc:
        machines = []
        warnings.append(f"Box {hw}: Maschinen konnten nicht gelesen werden ({exc})")
    rows.append((b, machines))

assigned_names = {}
for b, machines in rows:
    for m in machines:
        assigned_names.setdefault(first(m, NAME_KEYS), []).append(b.get("hardware_id"))

for b, machines in rows:
    if b.get("status") != "paired":
        warnings.append(f"Box {b.get('hardware_id')}: Status ist '{b.get('status')}' statt 'paired'")
    if not machines:
        warnings.append(f"Box {b.get('hardware_id')}: keine Maschinen zugewiesen")
for name, owners in assigned_names.items():
    if len(owners) > 1:
        warnings.append(f"Maschine {name} ist mehreren Boxen zugewiesen: {', '.join(map(str, owners))}")
unassigned = sorted({first(m, NAME_KEYS) for m in tenant_machines} - set(assigned_names))
if unassigned:
    warnings.append(f"Maschinen ohne Box-Zuweisung: {', '.join(unassigned)}")
if not boxes:
    warnings.append("Keine Connector-Boxen für diesen Tenant gefunden")

# Läuft für jede Box wirklich ein Poller-Container? (Maschinen können zugewiesen sein, ohne dass jemand pollt)
poller_running = {}
poller_container = {}
for pair in os.environ.get("POLLERS", "").split():
    hw, _, container = pair.partition("=")
    poller_container[hw] = container
    try:
        out = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container],
                             capture_output=True, text=True, timeout=15)
        poller_running[hw] = (out.returncode == 0 and out.stdout.strip() == "true")
    except Exception:
        pass  # kein docker verfügbar -> keine Aussage
for hw, running in poller_running.items():
    if not running:
        warnings.append(f"Box {hw}: Poller-Container {poller_container[hw]} läuft nicht (docker logs {poller_container[hw]})")

line = "=" * 60
print(line)
print("  [SUCCESS] uretOS Shopfloor erfolgreich gestartet!" if not warnings
      else "  [ACHTUNG] uretOS Shopfloor gestartet - mit Hinweisen (siehe unten)")
print(line)
print()
print("📊 SHOPFLOOR-REPORT")
print("-" * 60)
print(f"  Tenant:   {tenant}")
print(f"  Gateway:  {gw}")
dist = " : ".join(str(len(m)) for _, m in rows) or "-"
print(f"  Boxen:    {len(boxes)} | Maschinen im Tenant: {len(tenant_machines)} | Verteilung: {dist}")
print("-" * 60)
for b, machines in rows:
    hw = b.get("hardware_id")
    details = [f"Status: {b.get('status')}", f"zugewiesen: {len(machines)}"]
    if b.get("license_status"):
        details.insert(1, f"Lizenz: {b.get('license_status')}")
    if b.get("max_machines") is not None:
        details.insert(2, f"max. {b.get('max_machines')} Maschinen")
    if hw in poller_running:
        details.append("Poller: " + ("läuft" if poller_running[hw] else "GESTOPPT"))
    print(f"  [Box] {hw}  ({', '.join(details)})")
    if machines:
        for m in sorted(machines, key=lambda x: str(first(x, NAME_KEYS))):
            ep = first(m, ("endpoint_url", "endpoint"), "")
            st = first(m, ("status",), "")
            print(f"       └── ⚙️  {first(m, NAME_KEYS):<16} {ep}{('  [' + str(st) + ']') if st else ''}")
    else:
        print("       └── (keine Maschinen zugewiesen)")
    print()
if warnings:
    print("  ⚠️  Hinweise:")
    for w in warnings:
        print(f"     - {w}")
    print()
print("-" * 60)
print("  Live-Logs: docker logs -f uretos-connector-box-01   (bzw. -02)")
print(line)
PYEOF
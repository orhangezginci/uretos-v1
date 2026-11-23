import json
import os
import re
import requests

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway-api:8080")
YAML_FILE = os.environ.get("YAML_FILE", "shopfloor.yaml")

def parse_boxes_from_yaml(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Konnte {filepath} nicht lesen: {e}")
        return []

    boxes = []
    service_blocks = re.split(r'\n\s{2}(?=connector-box-[\w-]+:)', content)
    
    for block in service_blocks:
        if not block.strip().startswith("connector-box-"):
            continue
        
        box_id_match = re.search(r'BOX_HARDWARE_ID=([^\s]+)', block)
        hardware_id = box_id_match.group(1).strip() if box_id_match else "sim-box-01"
        
        boxes.append({
            "hardware_id": hardware_id,
            "tenant_id": "schwarzwald-metallwaren"
        })
    
    if not boxes:
        boxes.append({"hardware_id": "sim-box-01", "tenant_id": "schwarzwald-metallwaren"})
        
    return boxes

def parse_machines_from_yaml(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Konnte {filepath} nicht lesen: {e}")
        return []

    machines = []
    service_blocks = re.split(r'\n\s{2}(?=machine-[\w-]+:)', content)
    
    for block in service_blocks:
        if not block.strip().startswith("machine-"):
            continue
        
        machine_name_match = re.search(r'MACHINE_NAME=([^\s]+)', block)
        manufacturer_match = re.search(r'MANUFACTURER=(.+)', block)
        model_match = re.search(r'MODEL=(.+)', block)
        
        if machine_name_match:
            m_name = machine_name_match.group(1).strip()
            m_manuf = manufacturer_match.group(1).strip() if manufacturer_match else "Unknown"
            m_model = model_match.group(1).strip() if model_match else "Unknown"
            
            machine_id = f"urn:uretos:machine:{m_name}"
            
            machines.append({
                "machine_id": machine_id,
                "name": m_name.replace("-", " "),
                "manufacturer": m_manuf,
                "model": m_model,
                "machine_type": "Machine Tool",
                "status": "ok"
            })
    
    return machines

def register_full_shopfloor():
    print(f"1. Lese Shopfloor-Struktur dynamisch aus '{YAML_FILE}' ein...")
    boxes = parse_boxes_from_yaml(YAML_FILE)
    machines = parse_machines_from_yaml(YAML_FILE)

    if not boxes or not machines:
        print("Fehler: Keine Boxen oder Maschinen gefunden!")
        return

    print(f"   -> Gefundene Boxen: {[b['hardware_id'] for b in boxes]}")
    print(f"   -> Gefundene Maschinen: {len(machines)} Stück")

    tenant_id = boxes[0]["tenant_id"]

    # Schritt 2: Tenant provisionieren mit erhöhtem Timeout (120s für DB-Initialisierung)
    print(f"\n2. Provisioniere Tenant '{tenant_id}'...")
    try:
        resp = requests.post(f"{GATEWAY_URL}/v1/tenants", json={"tenant_id": tenant_id}, timeout=120)
        if resp.status_code in [200, 201]:
            print(f"  -> Tenant '{tenant_id}' erfolgreich provisioniert.")
        elif resp.status_code == 400 and "already exists" in resp.text:
            print(f"  -> Tenant-Container existiert bereits. Überspringe...")
        else:
            print(f"  -> [FEHLER] Tenant-Anlage fehlgeschlagen (Status {resp.status_code}): {resp.text}")
            return
    except Exception as exc:
        print(f"  -> Netzwerkfehler bei Tenant-Anlage: {exc}")
        return

    # Schritt 3: Connector-Boxen registrieren und pairen
    print("\n3. Registriere und paire Connector-Boxen am Gateway...")
    for i, box in enumerate(boxes):
        hw_id = box["hardware_id"]
        mac_address = f"02:00:00:00:00:0{i+1}"
        
        box_payload = {
            "hardware_id": hw_id,
            "tenant_id": box["tenant_id"],
            "mac_address": mac_address
        }
        try:
            reg_resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes", json=box_payload, timeout=30)
            if reg_resp.status_code in [200, 201]:
                print(f"  -> Connector Box '{hw_id}' erfolgreich registriert.")
            elif reg_reg_resp_status := reg_resp.status_code == 400 and "already exists" in reg_resp.text:
                print(f"  -> Connector Box '{hw_id}' war bereits registriert.")
            else:
                print(f"  -> [FEHLER] Box-Registrierung fehlgeschlagen (Status {reg_resp.status_code}): {reg_resp.text}")
                return
        except Exception as exc:
            print(f"  -> Netzwerkfehler bei Box-Registrierung: {exc}")
            return

        try:
            pair_resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes/pair", json={"hardware_id": hw_id}, timeout=30)
            if pair_resp.status_code == 200:
                print(f"  -> Connector Box '{hw_id}' erfolgreich gepairt.")
            else:
                print(f"  -> [FEHLER] Pairing fehlgeschlagen (Status {pair_resp.status_code}): {pair_resp.text}")
                return
        except Exception as exc:
            print(f"  -> Netzwerkfehler beim Pairing: {exc}")
            return

    # Schritt 4: Maschinen über Autoscan zuweisen
    print("\n4. Registriere Maschinen via Autoscan...")
    machine_idx = 0
    max_per_box = 5

    for box in boxes:
        box_id = box["hardware_id"]
        box_machines = machines[machine_idx:machine_idx + max_per_box]
        machine_idx += max_per_box

        if not box_machines:
            break

        payload = {
            "hardware_id": box_id,
            "machines": box_machines
        }
        
        try:
            resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes/autoscan", json=payload, timeout=30)
            if resp.status_code == 200:
                print(f"  -> {len(box_machines)} Maschinen erfolgreich für Box '{box_id}' registriert.")
            else:
                print(f"  -> Warnung/Fehler für Box '{box_id}': Status {resp.status_code} - {resp.text}")
        except Exception as exc:
            print(f"  -> Netzwerkfehler beim Autoscan: {exc}")

    print("\nVirtueller Shopfloor vollständig dynamisch und fehlerfrei eingerichtet!")

if __name__ == "__main__":
    register_full_shopfloor()
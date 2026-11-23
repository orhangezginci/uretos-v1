"""
Isoliertes Testskript für den mDNS-Discovery- und OPC-UA-Maschinenscan.
Lauscht aktiv im Netzwerk und gibt alle gefundenen Maschinen in der Konsole aus.
"""
from __future__ import annotations

import socket
import sys
import time
from zeroconf import ServiceBrowser, Zeroconf

try:
    from opc_inspector import inspect_machines
except ImportError:
    sys.path.append("./services/connector-box-poller")
    from opc_inspector import inspect_machines

class SimpleMDNSListener:
    def __init__(self):
        self.found_services = {}

    def remove_service(self, zeroconf, type_, name):
        if name in self.found_services:
            print(f"[-] mDNS Service verschwunden: {name}")
            del self.found_services[name]

    def update_service(self, zeroconf, type_, name):
        # Pflichtmethode für neuere Zeroconf-Versionen
        pass

    def add_service(self, zeroconf, type_, name):
        time.sleep(0.1)
        info = zeroconf.get_service_info(type_, name)
        if info and info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            endpoint = f"opc.tcp://{ip}:{port}"
            self.found_services[name] = endpoint
            print(f"[+] mDNS Service entdeckt: {name} -> {endpoint}")

def run_scanner():
    print("=" * 60)
    print("  uretOS mDNS & OPC-UA ISOLIERTER SCANNER-TEST")
    print("=" * 60)

    zeroconf = Zeroconf()
    listener = SimpleMDNSListener()
    
    print("Lausche für 10 Sekunden auf mDNS-Dienste (_opcua-tcp._tcp.local.)...\n")
    browser = ServiceBrowser(zeroconf, "_opcua-tcp._tcp.local.", listener)

    try:
        for i in range(10):
            time.sleep(1)
            print(".", end="", flush=True)
            
        print(f"\n\n--- mDNS Scan beendet. Gefundene Endpunkte: {len(listener.found_services)} ---")
        
        for name, endpoint in listener.found_services.items():
            print(f"\n🔍 Frage Maschinen-Identität ab für: {endpoint}")
            try:
                parsed_uri = endpoint.replace("opc.tcp://", "")
                host, port_str = parsed_uri.split(":")
                port = int(port_str)

                identities = inspect_machines(host, port, max_machines=1, timeout=3.0)
                
                if identities:
                    for ident in identities:
                        print(f"   ├── Name         : {ident.name}")
                        print(f"   ├── Hersteller   : {ident.manufacturer}")
                        print(f"   ├── Modell       : {ident.model}")
                        print(f"   └── Status       : {ident.status}")
                else:
                    print("   [!] Keine Maschinen-Identität über OPC-UA zurückgegeben.")
            except Exception as exc:
                print(f"   [X] Fehler beim Verbinden zur Maschine: {exc}")

    except KeyboardInterrupt:
        print("\nTest abgebrochen.")
    finally:
        zeroconf.close()
        print("\nScanner gestoppt.")

if __name__ == "__main__":
    run_scanner()
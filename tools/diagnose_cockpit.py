#!/usr/bin/env python3
"""
Findet die Stelle, an der der Weg  Browser -> Traefik -> BFF -> Gateway -> Services  bricht.

Prüft nacheinander (jede Station einzeln, nur lesend, nur Standardbibliothek):
  1 Gateway            erreichbar, Boxen/Maschinen/Box-Status-Endpoint vorhanden?
  2 BFF-Container      läuft, startet er in einer Schleife neu, Fehler in den Logs?
  3 BFF intern         antwortet /healthz und /api/v1/shopfloor von INNEN (python im BFF-Container)?
  4 Traefik-Netzwerk   passt das Label traefik.docker.network zu den Netzen von Traefik UND BFF?
  5 Traefik -> BFF     erreicht der Traefik-Container das BFF?
  6 Traefik-Router     existiert der Router, enthält die Regel /api/v1/shopfloor, hat der Service einen Server?
  7 Über Traefik       GET :8888/api/v1/shopfloor wie der Browser (inkl. CORS-Header)

Aufruf:  python3 diagnose_cockpit.py [tenant_id]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request

INTERNAL_FETCH = """
import json, sys, urllib.request, urllib.error
try:
    r = urllib.request.urlopen(sys.argv[1], timeout=15)
    print(json.dumps({"code": r.status, "body": r.read().decode()[:3000]}))
except urllib.error.HTTPError as e:
    print(json.dumps({"code": e.code, "body": e.read().decode()[:600]}))
except Exception as e:
    print(json.dumps({"code": 0, "body": str(e)}))
"""


def get(url: str, timeout: int = 10, headers: dict | None = None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), {k.lower(): v for k, v in e.headers.items()}
    except Exception as exc:
        return 0, str(exc), {}


def sh(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]} nicht gefunden"
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout"


def jload(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return None


class Diagnose:
    def __init__(self, a, run=None, fetch=None):
        self.a = a
        self.sh = run or sh
        self.get = fetch or get

    # ---------------------------------------------------------------- 1
    def gateway(self):
        a, lines = self.a, []
        code, body, _ = self.get(f"{a.gateway}/healthz")
        if code != 200:
            return "fail", [f"GET /healthz → HTTP {code} {body[:100]}"], \
                "gateway-api läuft nicht oder Port 8080 ist nicht veröffentlicht: docker logs uretos-gateway-api --tail 30"
        code, body, _ = self.get(f"{a.gateway}/v1/connector-boxes")
        j = jload(body)
        lines.append(f"/v1/connector-boxes → HTTP {code}" + (f", {len(j)} Box(en)" if isinstance(j, list) else ""))
        code, body, _ = self.get(f"{a.gateway}/v1/machines?tenant_id={urllib.parse.quote(a.tenant)}", timeout=70)
        j = jload(body)
        if code != 200:
            lines.append(f"/v1/machines?tenant_id={a.tenant} → HTTP {code}: {body[:260]}")
            hint = "Die Machine-Query liefert einen Fehler, das BFF kann daher keine Maschinen zeigen. "
            if "password authentication failed" in body:
                hint += "Veraltete Tenant-Zugangsdaten im Service: docker restart uretos-machine-query-service uretos-machine-command-service"
            elif code == 404:
                hint += "Tenant unbekannt: python simulate_boxes.py hat ihn evtl. noch nicht provisioniert."
            return "fail", lines, hint
        lines.append(f"/v1/machines → HTTP 200, {len(j) if isinstance(j, list) else '?'} Maschine(n)")
        code, body, _ = self.get(f"{a.gateway}/v1/connector-boxes/status")
        if code == 404:
            lines.append("/v1/connector-boxes/status → HTTP 404")
            return "warn", lines, "Gateway ohne den neuen Status-Endpoint, das Cockpit zeigt alle Boxen offline: docker compose up -d --build gateway-api"
        lines.append(f"/v1/connector-boxes/status → HTTP {code}")
        return "ok", lines, ""

    # ---------------------------------------------------------------- 2
    def container(self):
        a = self.a
        rc, out, err = self.sh(["docker", "inspect", "-f", "{{.State.Status}}|{{.State.ExitCode}}|{{.State.Restarting}}", a.bff_container])
        if rc != 0:
            return "fail", [f"Container '{a.bff_container}' nicht gefunden"], \
                "docker compose up -d --build shopfloor-bff-api   (Name prüfen: docker ps -a | grep bff)"
        status, exit_code, restarting = (out.strip().split("|") + ["", "", ""])[:3]
        lines = [f"Status: {status}, ExitCode: {exit_code}, Restart-Schleife: {restarting}"]
        _, logs, logs_err = self.sh(["docker", "logs", "--tail", "40", a.bff_container])
        text = logs + logs_err
        problem = [l for l in text.splitlines() if "Traceback" in l or "Error" in l or "error" in l.lower()][-3:]
        if status != "running" or restarting == "true":
            return "fail", lines + [f"Log: {l[:160]}" for l in text.splitlines()[-6:]], \
                "Der BFF-Container läuft nicht. Fehler in den Logs beheben (häufig: fehlende Abhängigkeit oder Importfehler)."
        if problem:
            return "warn", lines + [f"Log: {l[:160]}" for l in problem], "Auffällige Zeilen in den BFF-Logs: docker logs uretos-shopfloor-bff-api --tail 40"
        return "ok", lines, ""

    # ---------------------------------------------------------------- 3
    def internal(self):
        a = self.a
        base = f"http://127.0.0.1:{a.bff_port}"

        def fetch(path):
            rc, out, err = self.sh(["docker", "exec", a.bff_container, "python", "-c", INTERNAL_FETCH, base + path])
            return (jload(out.strip().splitlines()[-1]) if rc == 0 and out.strip() else None), (err or out).strip()[:160]

        health, e = fetch("/healthz")
        if not health or health["code"] != 200:
            return "fail", [f"{base}/healthz → {health['code'] if health else 'kein Ergebnis'} {e or (health or {}).get('body', '')}"], \
                f"Das BFF antwortet auf Port {a.bff_port} nicht (Uvicorn-Port im Dockerfile prüfen, --bff-port)."
        ov, e = fetch(f"/api/v1/shopfloor?tenant_id={urllib.parse.quote(a.tenant)}")
        if not ov:
            return "fail", ["/api/v1/shopfloor → kein Ergebnis " + e], "python im BFF-Container nicht ausführbar?"
        if ov["code"] == 404:
            return "fail", ["/api/v1/shopfloor → HTTP 404 (Not Found)"], \
                "Im Container läuft noch die ALTE BFF-Version ohne den neuen Endpoint: docker compose up -d --build shopfloor-bff-api"
        if ov["code"] != 200:
            return "fail", [f"/api/v1/shopfloor → HTTP {ov['code']}: {ov['body'][:200]}"], \
                "Das BFF erreicht das Gateway nicht oder dieses antwortet mit einem Fehler: Service shopfloor-bff-api braucht " \
                "GATEWAY_URL=http://gateway-api:8080 (und Gateway-Fehler siehe Station 1)."
        data = jload(ov["body"]) or {}
        return "ok", [f"/healthz ok, /api/v1/shopfloor → {data.get('box_count', '?')} Box(en), {data.get('machine_count', '?')} Maschine(n)"], ""

    # ---------------------------------------------------------------- 4
    def networks(self):
        a = self.a
        rc, label, _ = self.sh(["docker", "inspect", "-f", '{{index .Config.Labels "traefik.docker.network"}}', a.bff_container])
        label = label.strip() if rc == 0 else ""
        _, bff_nets, _ = self.sh(["docker", "inspect", "-f", "{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}", a.bff_container])
        _, tr_nets, _ = self.sh(["docker", "inspect", "-f", "{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}", a.traefik_container])
        bff, tr = bff_nets.split(), tr_nets.split()
        lines = [f"Label traefik.docker.network: {label or '(nicht gesetzt)'}", f"Netze des BFF: {', '.join(bff) or '-'}",
                 f"Netze von Traefik: {', '.join(tr) or '-'}"]
        shared = sorted(set(bff) & set(tr))
        if not shared:
            return "fail", lines, "BFF und Traefik teilen kein Docker-Netzwerk."
        if label and (label not in bff or label not in tr):
            return "fail", lines, f"Das Label nennt ein Netzwerk, das nicht beide haben. Setze es auf ein gemeinsames Netz, z.B. " \
                                  f"\"traefik.docker.network={shared[0]}\", und erstelle das BFF neu: docker compose up -d --force-recreate shopfloor-bff-api"
        if not label and len(bff) > 1:
            return "warn", lines, f"Das BFF hängt in mehreren Netzen, ohne Label wählt Traefik zufällig: \"traefik.docker.network={shared[0]}\" setzen."
        return "ok", lines, ""

    # ---------------------------------------------------------------- 5
    def traefik_to_bff(self):
        a = self.a
        rc, out, err = self.sh(["docker", "exec", a.traefik_container, "wget", "-qO-", "-T", "5", f"http://{a.bff_container}:{a.bff_port}/healthz"])
        if rc == 0 and "ok" in out:
            return "ok", [f"Traefik → {a.bff_container}:{a.bff_port}/healthz ok"], ""
        if rc in (127, 126) or "not found" in err:
            return "skip", ["wget im Traefik-Container nicht verfügbar"], ""
        return "fail", [f"Traefik → {a.bff_container}:{a.bff_port}/healthz fehlgeschlagen: {(err or out).strip()[:160]}"], \
            "Traefik erreicht das BFF über das Docker-Netz nicht (Netze siehe Station 4, Port siehe --bff-port)."

    # ---------------------------------------------------------------- 6
    def traefik_router(self):
        a = self.a
        code, body, _ = self.get(f"{a.traefik_api}/api/http/routers")
        routers = jload(body)
        if code != 200 or not isinstance(routers, list):
            return "skip", [f"Traefik-API {a.traefik_api} nicht erreichbar (HTTP {code})"], ""
        router = next((r for r in routers if "shopfloor-bff" in r.get("name", "")), None)
        if not router:
            return "fail", ["Router 'shopfloor-bff' existiert in Traefik nicht"], \
                "Die Labels wurden nicht geladen: docker compose up -d --force-recreate shopfloor-bff-api; docker logs uretos-traefik --tail 30"
        rule = router.get("rule", "")
        lines = [f"Router: {router.get('name')} | Status: {router.get('status')} | Regel: {rule}"]
        if "/api/v1/shopfloor" not in rule:
            return "fail", lines, "Die Regel kennt /api/v1/shopfloor nicht (altes Label). Regel erweitern: " \
                                  "PathPrefix(`/api/v1/machines`) || PathPrefix(`/api/v1/shopfloor`) und Service neu erstellen."
        code, body, _ = self.get(f"{a.traefik_api}/api/http/services")
        services = jload(body) or []
        svc = next((s for s in services if s.get("name", "").startswith(str(router.get("service", "")))), None)
        servers = (svc or {}).get("loadBalancer", {}).get("servers", [])
        if not servers:
            return "fail", lines + ["Service ohne Server (Traefik hat keine Container-IP gefunden)"], \
                "Meist das Label traefik.docker.network (Station 4) oder das BFF ist nicht gestartet/healthy."
        lines.append("Server: " + ", ".join(s.get("url", "?") for s in servers))
        return "ok", lines, ""

    # ---------------------------------------------------------------- 7
    def via_traefik(self):
        a = self.a
        code, body, headers = self.get(f"{a.traefik_web}/api/v1/shopfloor?tenant_id={urllib.parse.quote(a.tenant)}", timeout=20,
                                       headers={"Origin": "http://localhost:5500"})
        if code == 200:
            data = jload(body) or {}
            cors = headers.get("access-control-allow-origin")
            lines = [f"HTTP 200, {data.get('box_count', '?')} Box(en), {data.get('machine_count', '?')} Maschine(n)", f"CORS Access-Control-Allow-Origin: {cors or '(fehlt)'}"]
            return ("ok" if cors else "warn"), lines, "" if cors else "CORS-Header fehlt: der Browser blockiert die Antwort (BFF-Middleware prüfen)."
        hints = {0: f"Traefik antwortet auf {a.traefik_web} nicht (Port 8888 → Traefik :80, docker ps).",
                 404: "Kein Router passt auf den Pfad (Label/Regel, Station 6).",
                 502: "Traefik erreicht das BFF nicht (Netzwerk, Station 4/5).", 503: "Kein Server hinter dem Service (Station 4/6).",
                 504: "Zeitüberschreitung: das BFF wartet auf das Gateway oder einen langsamen Query-Service."}
        return "fail", [f"HTTP {code} {body[:160]}"], hints.get(code, "Unerwarteter Status vom BFF.")

    def run(self) -> int:
        stations = [("1 Gateway", self.gateway), ("2 BFF-Container", self.container), ("3 BFF intern", self.internal),
                    ("4 Traefik-Netzwerk", self.networks), ("5 Traefik → BFF", self.traefik_to_bff),
                    ("6 Traefik-Router", self.traefik_router), ("7 Über Traefik (wie der Browser)", self.via_traefik)]
        icons = {"ok": "✅", "warn": "⚠️ ", "fail": "❌", "skip": "➖"}
        first_fail = None
        for name, fn in stations:
            status, lines, hint = fn()
            print(f"{icons[status]} {name}")
            for l in lines:
                print(f"     {l}")
            if hint and status in ("fail", "warn"):
                print(f"     → {hint}")
            if status == "fail" and first_fail is None:
                first_fail = (name, hint)
        print()
        if first_fail:
            print(f"ERSTE BRUCHSTELLE: {first_fail[0]}\n  {first_fail[1]}")
            return 1
        print("Alle Stationen in Ordnung. Zeigt der Browser trotzdem 'BFF nicht erreichbar': Seite per http:// öffnen (nicht file://), "
              "Browser-Konsole (F12) auf CORS/Mixed-Content prüfen.")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tenant", nargs="?", default="schwarzwald-metallwaren")
    ap.add_argument("--gateway", default="http://localhost:8080")
    ap.add_argument("--traefik-web", default="http://localhost:8888")
    ap.add_argument("--traefik-api", default="http://localhost:8090")
    ap.add_argument("--bff-container", default="uretos-shopfloor-bff-api")
    ap.add_argument("--traefik-container", default="uretos-traefik")
    ap.add_argument("--bff-port", type=int, default=8080)
    return Diagnose(ap.parse_args()).run()


if __name__ == "__main__":
    raise SystemExit(main())

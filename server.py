#!/usr/bin/env python3
"""Servidor sin npm. En Windows: py server.py"""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import store

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
PORT = int(os.environ.get("PORT", "10000"))
HOST = "0.0.0.0"

VENUES = [
    {"id": "laurita", "name": "Centro Deportivo Laurita Vicuña", "addr": "Av. Ejército Libertador 2341, Villa La Foresta, Puente Alto"},
    {"id": "amador", "name": "Complejo Deportivo Amador Donoso", "addr": "Camino Público 0113, Puente Alto"},
    {"id": "estadio", "name": "Estadio Municipal de Puente Alto", "addr": "Nemesio Vicuña 450, Puente Alto"},
    {"id": "gabriela", "name": "Centro Deportivo Gabriela", "addr": "Av. Ejército Libertador 4011, Puente Alto"},
    {"id": "tocornal", "name": "Centro Deportivo Domingo Tocornal", "addr": "Domingo Tocornal con 4 Oriente, Puente Alto"},
    {"id": "gimnasio", "name": "Gimnasio Municipal", "addr": "Balmaceda 265, Puente Alto"},
    {"id": "patinodromo", "name": "Patinódromo Municipal", "addr": "Av. Ejército Libertador con Coyhaique, Puente Alto"},
    {"id": "sanfrancisco", "name": "Centro Comunitario Parque San Francisco", "addr": "Troncal San Francisco con Nonato Coo, Puente Alto"},
    {"id": "luismatte", "name": "Cancha de Futbolito Luis Matte", "addr": "Miguel Covarrubias 2811, Puente Alto"},
    {"id": "sangeronimo", "name": "Cancha Futbolito San Gerónimo", "addr": "Las Achiras con Los Caciques, Puente Alto"},
    {"id": "humberto", "name": "Cancha Humberto Díaz Casanueva", "addr": "Tome con Caleta Brava, Puente Alto"},
    {"id": "faustina", "name": "Complejo Deportivo Santa Faustina", "addr": "Cuatro Oriente 1040, Puente Alto"},
    {"id": "maipo", "name": "Cancha Maipo", "addr": "Tocornal Grez con Sargento Menadier, Puente Alto"},
    {"id": "altosoccer", "name": "Espacio Deportivo Alto Soccer", "addr": "Av. Eyzaguirre 3769, Puente Alto"},
    {"id": "estacion", "name": "Estación Futbolito", "addr": "Av. Concha y Toro 2980, Puente Alto"},
    {"id": "cdd", "name": "Complejo Deportivo CDD", "addr": "Av. Concha y Toro 0190, Puente Alto"},
]


def empty_db():
    return store.empty_db()


def load():
    return store.load()


def save(db):
    return store.save(db)


def norm(name):
    return " ".join(str(name or "").strip().lower().split())


def venue_of(db):
    return next((v for v in VENUES if v["id"] == db["cfg"]["venueId"]), VENUES[0])


def public_state():
    db = load()
    roster = []
    for k in db["match"]:
        p = db["profiles"].get(k)
        if not p:
            continue
        roster.append({
            "key": k,
            "name": p.get("name"),
            "nick": p.get("nick"),
            "photo": p.get("photo"),
            "points": p.get("points", 0),
            "matches": p.get("matches", 0),
        })
    cfg = dict(db["cfg"])
    cfg.pop("pin", None)
    vk = "s%s-m%s" % (cfg.get("season", 1), cfg.get("matchInSeason", 1))
    bucket = (db.get("votes") or {}).get(vk) or {"tally": {}, "voters": []}
    results = []
    for k, n in sorted(bucket.get("tally", {}).items(), key=lambda x: (-x[1], x[0])):
        p = db["profiles"].get(k)
        if p:
            results.append({"key": k, "name": p.get("name"), "nick": p.get("nick") or "", "votes": n})
    return {
        "cfg": cfg,
        "venue": venue_of(db),
        "venues": VENUES,
        "roster": roster,
        "poll": {
            "id": vk,
            "label": "Jornada %s · Temporada %s" % (cfg.get("matchInSeason", 1), cfg.get("season", 1)),
            "total": sum(bucket.get("tally", {}).values()),
            "results": results,
        },
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC, **kwargs)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _json(self, code, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            return self._json(200, public_state())
        if parsed.path == "/api/admin/players":
            pin = (parse_qs(parsed.query).get("pin") or [""])[0]
            db = load()
            if pin != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave admin incorrecta"})
            players = []
            for key, p in db["profiles"].items():
                players.append({
                    "key": key,
                    "name": p.get("name"),
                    "nick": p.get("nick"),
                    "points": p.get("points", 0),
                    "matches": p.get("matches", 0),
                    "inMatch": key in db["match"],
                })
            return self._json(200, {"players": players, "cfg": db["cfg"]})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        db = load()

        if path == "/api/admin/login":
            if body.get("pin") != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave incorrecta"})
            return self._json(200, {"ok": True})

        if path == "/api/signup":
            clean = str(body.get("name") or "").strip()
            key = norm(clean)
            leave = str(body.get("leaveKey") or "").strip()
            if len(clean) < 3:
                return self._json(400, {"error": "Ingresa un nombre."})
            if len(leave) < 4:
                return self._json(400, {"error": "La clave debe tener al menos 4 caracteres."})
            if key in db["match"]:
                return self._json(409, {"error": "Ese nombre ya está en este partido."})
            if len(db["match"]) >= db["cfg"]["max"]:
                return self._json(409, {"error": "La lista ya está completa."})
            prev = db["profiles"].get(key) or {"name": clean, "nick": "", "photo": "", "points": 0, "matches": 0}
            db["profiles"][key] = {
                "name": prev.get("name") or clean,
                "nick": str(body.get("nick") or prev.get("nick") or "").strip(),
                "photo": body.get("photo") or prev.get("photo") or "",
                "points": prev.get("points", 0) + db["cfg"]["pts"],
                "matches": prev.get("matches", 0) + 1,
                "leaveKey": leave,
            }
            db["match"].append(key)
            save(db)
            pts = db["profiles"][key]["points"]
            return self._json(200, {"ok": True, "points": pts, "message": f"+{db['cfg']['pts']} pts. Total: {pts}"})

        if path == "/api/leave":
            key = norm(body.get("name"))
            pin = str(body.get("leaveKey") or "").strip()
            p = db["profiles"].get(key)
            if not p or key not in db["match"]:
                return self._json(404, {"error": "Ese nombre no está en este partido."})
            if p.get("leaveKey") != pin:
                return self._json(401, {"error": "Clave incorrecta."})
            db["match"] = [x for x in db["match"] if x != key]
            p["points"] = max(0, p.get("points", 0) - db["cfg"]["pts"])
            p["matches"] = max(0, p.get("matches", 0) - 1)
            save(db)
            return self._json(200, {"ok": True, "message": "Saliste de la lista. Cupo liberado."})

        if path == "/api/lookup":
            p = db["profiles"].get(norm(body.get("name")))
            if not p:
                return self._json(200, {"found": False})
            return self._json(200, {"found": True, "nick": p.get("nick") or "", "photo": p.get("photo") or ""})

        if path == "/api/admin/config":
            if body.get("pin") != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave admin incorrecta"})
            if body.get("venueId"):
                db["cfg"]["venueId"] = body["venueId"]
            if body.get("date"):
                db["cfg"]["date"] = body["date"]
            if body.get("time"):
                db["cfg"]["time"] = body["time"]
            if body.get("max"):
                db["cfg"]["max"] = max(2, min(30, int(body.get("max") or 14)))
            if body.get("pts"):
                db["cfg"]["pts"] = max(1, min(200, int(body.get("pts") or 50)))
            if str(body.get("newPin") or "").strip():
                db["cfg"]["pin"] = str(body["newPin"]).strip()
            save(db)
            return self._json(200, {"ok": True})

        if path == "/api/admin/next-match":
            if body.get("pin") != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave admin incorrecta"})
            if db["cfg"]["matchInSeason"] >= 15:
                db["cfg"]["matchInSeason"] = 1
                db["cfg"]["season"] += 1
                for k in db["profiles"]:
                    db["profiles"][k]["points"] = 0
                msg = f"Temporada {db['cfg']['season']}. Puntos en 0."
            else:
                db["cfg"]["matchInSeason"] += 1
                msg = f"Partido {db['cfg']['matchInSeason']} de 15."
            db["match"] = []
            save(db)
            return self._json(200, {"ok": True, "message": msg})

        if path == "/api/admin/reset-season":
            if body.get("pin") != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave admin incorrecta"})
            db["cfg"]["season"] += 1
            db["cfg"]["matchInSeason"] = 1
            for k in db["profiles"]:
                db["profiles"][k]["points"] = 0
            db["match"] = []
            save(db)
            return self._json(200, {"ok": True, "message": "Temporada reiniciada."})

        if path == "/api/admin/player":
            if body.get("pin") != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave admin incorrecta"})
            name = str(body.get("name") or "").strip()
            if len(name) < 3:
                return self._json(400, {"error": "Escribe un nombre."})
            key = norm(name)
            if key not in db["profiles"]:
                db["profiles"][key] = {
                    "name": name,
                    "nick": str(body.get("nick") or "").strip(),
                    "photo": "",
                    "points": 0,
                    "matches": 0,
                    "leaveKey": "",
                }
            save(db)
            return self._json(200, {"ok": True})

        if path == "/api/admin/player-action":
            if body.get("pin") != db["cfg"]["pin"]:
                return self._json(401, {"error": "Clave admin incorrecta"})
            key = body.get("key")
            act = body.get("act")
            p = db["profiles"].get(key)
            if act != "del" and not p:
                return self._json(404, {"error": "No existe"})
            if act == "pts":
                p["points"] = p.get("points", 0) + db["cfg"]["pts"]
            elif act == "add":
                if key in db["match"]:
                    return self._json(409, {"error": "Ya está en este partido."})
                if len(db["match"]) >= db["cfg"]["max"]:
                    return self._json(409, {"error": "Cupo lleno."})
                db["match"].append(key)
                p["points"] = p.get("points", 0) + db["cfg"]["pts"]
                p["matches"] = p.get("matches", 0) + 1
            elif act == "del":
                db["profiles"].pop(key, None)
                db["match"] = [x for x in db["match"] if x != key]
            save(db)
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "Ruta no encontrada"})


if __name__ == "__main__":
    os.chdir(ROOT)
    print("Listening on %s:%s" % (HOST, PORT), flush=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()

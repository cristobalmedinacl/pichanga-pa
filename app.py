import os
from flask import Flask, jsonify, request, send_from_directory
import server as s

app = Flask(__name__, static_folder="public", static_url_path="")


def pin_ok(body=None):
    db = s.load()
    given = ""
    if body and isinstance(body, dict):
        given = str(body.get("pin") or "")
    if not given:
        given = request.args.get("pin") or ""
    return given == db["cfg"]["pin"], db


@app.get("/")
def index():
    return send_from_directory("public", "index.html")


@app.get("/api/state")
def state():
    return jsonify(s.public_state())


@app.get("/api/admin/players")
def admin_players():
    ok, db = pin_ok()
    if not ok:
        return jsonify({"error": "Clave admin incorrecta"}), 401
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
    return jsonify({"players": players, "cfg": db["cfg"]})


@app.post("/api/admin/login")
def admin_login():
    body = request.get_json(silent=True) or {}
    ok, _ = pin_ok(body)
    if not ok:
        return jsonify({"error": "Clave incorrecta"}), 401
    return jsonify({"ok": True})


@app.post("/api/signup")
def signup():
    body = request.get_json(silent=True) or {}
    req = type("R", (), {"path": "/api/signup", "headers": {"Content-Length": "1"}})
    # reuse logic via direct port of handler internals
    db = s.load()
    clean = str(body.get("name") or "").strip()
    key = s.norm(clean)
    leave = str(body.get("leaveKey") or "").strip()
    if len(clean) < 3:
        return jsonify({"error": "Ingresa un nombre."}), 400
    if len(leave) < 4:
        return jsonify({"error": "La clave debe tener al menos 4 caracteres."}), 400
    if key in db["match"]:
        return jsonify({"error": "Ese nombre ya está en este partido."}), 409
    if len(db["match"]) >= db["cfg"]["max"]:
        return jsonify({"error": "La lista ya está completa."}), 409
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
    s.save(db)
    pts = db["profiles"][key]["points"]
    return jsonify({"ok": True, "points": pts, "message": f"+{db['cfg']['pts']} pts. Total: {pts}"})


@app.post("/api/leave")
def leave():
    body = request.get_json(silent=True) or {}
    db = s.load()
    key = s.norm(body.get("name"))
    pin = str(body.get("leaveKey") or "").strip()
    p = db["profiles"].get(key)
    if not p or key not in db["match"]:
        return jsonify({"error": "Ese nombre no está en este partido."}), 404
    if p.get("leaveKey") != pin:
        return jsonify({"error": "Clave incorrecta."}), 401
    db["match"] = [x for x in db["match"] if x != key]
    p["points"] = max(0, p.get("points", 0) - db["cfg"]["pts"])
    p["matches"] = max(0, p.get("matches", 0) - 1)
    s.save(db)
    return jsonify({"ok": True, "message": "Saliste de la lista. Cupo liberado."})


@app.post("/api/lookup")
def lookup():
    body = request.get_json(silent=True) or {}
    p = s.load()["profiles"].get(s.norm(body.get("name")))
    if not p:
        return jsonify({"found": False})
    return jsonify({"found": True, "nick": p.get("nick") or "", "photo": p.get("photo") or ""})


@app.post("/api/admin/config")
def admin_config():
    body = request.get_json(silent=True) or {}
    ok, db = pin_ok(body)
    if not ok:
        return jsonify({"error": "Clave admin incorrecta"}), 401
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
    s.save(db)
    return jsonify({"ok": True})


@app.post("/api/admin/next-match")
def next_match():
    body = request.get_json(silent=True) or {}
    ok, db = pin_ok(body)
    if not ok:
        return jsonify({"error": "Clave admin incorrecta"}), 401
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
    s.save(db)
    return jsonify({"ok": True, "message": msg})


@app.post("/api/admin/reset-season")
def reset_season():
    body = request.get_json(silent=True) or {}
    ok, db = pin_ok(body)
    if not ok:
        return jsonify({"error": "Clave admin incorrecta"}), 401
    db["cfg"]["season"] = 1
    db["cfg"]["matchInSeason"] = 1
    for k in db["profiles"]:
        db["profiles"][k]["points"] = 0
    db["match"] = []
    s.save(db)
    return jsonify({"ok": True, "message": "Temporada 1. Puntos en 0."})


@app.post("/api/admin/player")
def admin_player():
    body = request.get_json(silent=True) or {}
    ok, db = pin_ok(body)
    if not ok:
        return jsonify({"error": "Clave admin incorrecta"}), 401
    name = str(body.get("name") or "").strip()
    if len(name) < 3:
        return jsonify({"error": "Escribe un nombre."}), 400
    key = s.norm(name)
    if key not in db["profiles"]:
        db["profiles"][key] = {
            "name": name,
            "nick": str(body.get("nick") or "").strip(),
            "photo": "",
            "points": 0,
            "matches": 0,
            "leaveKey": "",
        }
    s.save(db)
    return jsonify({"ok": True})


@app.post("/api/admin/player-action")
def player_action():
    body = request.get_json(silent=True) or {}
    ok, db = pin_ok(body)
    if not ok:
        return jsonify({"error": "Clave admin incorrecta"}), 401
    key = body.get("key")
    act = body.get("act")
    p = db["profiles"].get(key)
    if act != "del" and not p:
        return jsonify({"error": "No existe"}), 404
    if act == "pts":
        p["points"] = p.get("points", 0) + db["cfg"]["pts"]
    elif act == "add":
        if key in db["match"]:
            return jsonify({"error": "Ya está en este partido."}), 409
        if len(db["match"]) >= db["cfg"]["max"]:
            return jsonify({"error": "Cupo lleno."}), 409
        db["match"].append(key)
        p["points"] = p.get("points", 0) + db["cfg"]["pts"]
        p["matches"] = p.get("matches", 0) + 1
    elif act == "del":
        db["profiles"].pop(key, None)
        db["match"] = [x for x in db["match"] if x != key]
    s.save(db)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))

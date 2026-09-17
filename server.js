const express = require("express");
const fs = require("fs");
const path = require("path");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 3000;
const DB_PATH = path.join(__dirname, "data", "db.json");

const VENUES = [
  { id: "laurita", name: "Centro Deportivo Laurita Vicuña", addr: "Av. Ejército Libertador 2341, Villa La Foresta, Puente Alto" },
  { id: "amador", name: "Complejo Deportivo Amador Donoso", addr: "Camino Público 0113, Puente Alto" },
  { id: "estadio", name: "Estadio Municipal de Puente Alto", addr: "Nemesio Vicuña 450, Puente Alto" },
  { id: "gabriela", name: "Centro Deportivo Gabriela", addr: "Av. Ejército Libertador 4011, Puente Alto" },
  { id: "tocornal", name: "Centro Deportivo Domingo Tocornal", addr: "Domingo Tocornal con 4 Oriente, Puente Alto" },
  { id: "gimnasio", name: "Gimnasio Municipal", addr: "Balmaceda 265, Puente Alto" },
  { id: "patinodromo", name: "Patinódromo Municipal", addr: "Av. Ejército Libertador con Coyhaique, Puente Alto" },
  { id: "sanfrancisco", name: "Centro Comunitario Parque San Francisco", addr: "Troncal San Francisco con Nonato Coo, Puente Alto" },
  { id: "luismatte", name: "Cancha de Futbolito Luis Matte", addr: "Miguel Covarrubias 2811, Puente Alto" },
  { id: "sangeronimo", name: "Cancha Futbolito San Gerónimo", addr: "Las Achiras con Los Caciques, Puente Alto" },
  { id: "humberto", name: "Cancha Humberto Díaz Casanueva", addr: "Tome con Caleta Brava, Puente Alto" },
  { id: "faustina", name: "Complejo Deportivo Santa Faustina", addr: "Cuatro Oriente 1040, Puente Alto" },
  { id: "maipo", name: "Cancha Maipo", addr: "Tocornal Grez con Sargento Menadier, Puente Alto" },
  { id: "altosoccer", name: "Espacio Deportivo Alto Soccer", addr: "Av. Eyzaguirre 3769, Puente Alto" },
  { id: "estacion", name: "Estación Futbolito", addr: "Av. Concha y Toro 2980, Puente Alto" },
  { id: "cdd", name: "Complejo Deportivo CDD", addr: "Av. Concha y Toro 0190, Puente Alto" }
];

function emptyDb() {
  return {
    cfg: {
      pin: "admin123",
      venueId: "laurita",
      date: "2026-09-19",
      time: "19:00",
      max: 14,
      pts: 50,
      season: 1,
      matchInSeason: 1
    },
    profiles: {},
    match: []
  };
}

function load() {
  try {
    return { ...emptyDb(), ...JSON.parse(fs.readFileSync(DB_PATH, "utf8")) };
  } catch {
    const db = emptyDb();
    save(db);
    return db;
  }
}

function save(db) {
  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  fs.writeFileSync(DB_PATH, JSON.stringify(db, null, 2));
}

function norm(n) {
  return String(n || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function venueOf(db) {
  return VENUES.find((v) => v.id === db.cfg.venueId) || VENUES[0];
}

function publicState() {
  const db = load();
  const venue = venueOf(db);
  const roster = db.match
    .map((k) => {
      const p = db.profiles[k];
      if (!p) return null;
      return { key: k, name: p.name, nick: p.nick, photo: p.photo, points: p.points || 0, matches: p.matches || 0 };
    })
    .filter(Boolean);
  return { cfg: { ...db.cfg, pin: undefined }, venue, venues: VENUES, roster };
}

app.use(cors());
app.use(express.json({ limit: "4mb" }));
app.use(express.static(path.join(__dirname, "public")));

app.get("/api/state", (_req, res) => res.json(publicState()));

app.get("/api/admin/players", (req, res) => {
  const db = load();
  if (req.query.pin !== db.cfg.pin) return res.status(401).json({ error: "Clave admin incorrecta" });
  const players = Object.entries(db.profiles).map(([key, p]) => ({
    key,
    name: p.name,
    nick: p.nick,
    points: p.points || 0,
    matches: p.matches || 0,
    inMatch: db.match.includes(key)
  }));
  res.json({ players, cfg: db.cfg });
});

app.post("/api/admin/login", (req, res) => {
  const db = load();
  if ((req.body.pin || "") !== db.cfg.pin) return res.status(401).json({ error: "Clave incorrecta" });
  res.json({ ok: true });
});

app.post("/api/signup", (req, res) => {
  const { name, nick, leaveKey, photo } = req.body || {};
  const db = load();
  const clean = String(name || "").trim();
  const key = norm(clean);
  if (clean.length < 3) return res.status(400).json({ error: "Ingresa un nombre." });
  if (String(leaveKey || "").trim().length < 4) return res.status(400).json({ error: "La clave debe tener al menos 4 caracteres." });
  if (db.match.includes(key)) return res.status(409).json({ error: "Ese nombre ya está en este partido." });
  if (db.match.length >= db.cfg.max) return res.status(409).json({ error: "La lista ya está completa." });

  const prev = db.profiles[key] || { name: clean, nick: "", photo: "", points: 0, matches: 0, leaveKey: "" };
  db.profiles[key] = {
    name: prev.name || clean,
    nick: String(nick || prev.nick || "").trim(),
    photo: photo || prev.photo || "",
    points: (prev.points || 0) + db.cfg.pts,
    matches: (prev.matches || 0) + 1,
    leaveKey: String(leaveKey).trim()
  };
  db.match.push(key);
  save(db);
  res.json({ ok: true, points: db.profiles[key].points, message: `+${db.cfg.pts} pts. Total: ${db.profiles[key].points}` });
});

app.post("/api/leave", (req, res) => {
  const key = norm(req.body.name);
  const pin = String(req.body.leaveKey || "").trim();
  const db = load();
  const p = db.profiles[key];
  if (!p || !db.match.includes(key)) return res.status(404).json({ error: "Ese nombre no está en este partido." });
  if (!p.leaveKey || p.leaveKey !== pin) return res.status(401).json({ error: "Clave incorrecta." });
  db.match = db.match.filter((x) => x !== key);
  p.points = Math.max(0, (p.points || 0) - db.cfg.pts);
  p.matches = Math.max(0, (p.matches || 0) - 1);
  save(db);
  res.json({ ok: true, message: "Saliste de la lista. Cupo liberado." });
});

app.post("/api/lookup", (req, res) => {
  const p = load().profiles[norm(req.body.name)];
  if (!p) return res.json({ found: false });
  res.json({ found: true, nick: p.nick || "", photo: p.photo || "" });
});

app.post("/api/admin/config", (req, res) => {
  const db = load();
  if (req.body.pin !== db.cfg.pin) return res.status(401).json({ error: "Clave admin incorrecta" });
  const b = req.body;
  if (b.venueId) db.cfg.venueId = b.venueId;
  if (b.date) db.cfg.date = b.date;
  if (b.time) db.cfg.time = b.time;
  if (b.max) db.cfg.max = Math.max(2, Math.min(30, Number(b.max) || 14));
  if (b.pts) db.cfg.pts = Math.max(1, Math.min(200, Number(b.pts) || 50));
  if (b.newPin && String(b.newPin).trim()) db.cfg.pin = String(b.newPin).trim();
  save(db);
  res.json({ ok: true });
});

app.post("/api/admin/next-match", (req, res) => {
  const db = load();
  if (req.body.pin !== db.cfg.pin) return res.status(401).json({ error: "Clave admin incorrecta" });
  let msg;
  if (db.cfg.matchInSeason >= 15) {
    db.cfg.matchInSeason = 1;
    db.cfg.season += 1;
    Object.keys(db.profiles).forEach((k) => { db.profiles[k].points = 0; });
    msg = `Temporada ${db.cfg.season}. Puntos en 0.`;
  } else {
    db.cfg.matchInSeason += 1;
    msg = `Partido ${db.cfg.matchInSeason} de 15.`;
  }
  db.match = [];
  save(db);
  res.json({ ok: true, message: msg });
});

app.post("/api/admin/reset-season", (req, res) => {
  const db = load();
  if (req.body.pin !== db.cfg.pin) return res.status(401).json({ error: "Clave admin incorrecta" });
  db.cfg.season += 1;
  db.cfg.matchInSeason = 1;
  Object.keys(db.profiles).forEach((k) => { db.profiles[k].points = 0; });
  db.match = [];
  save(db);
  res.json({ ok: true, message: "Temporada reiniciada." });
});

app.post("/api/admin/player", (req, res) => {
  const db = load();
  if (req.body.pin !== db.cfg.pin) return res.status(401).json({ error: "Clave admin incorrecta" });
  const name = String(req.body.name || "").trim();
  if (name.length < 3) return res.status(400).json({ error: "Escribe un nombre." });
  const key = norm(name);
  if (!db.profiles[key]) {
    db.profiles[key] = { name, nick: String(req.body.nick || "").trim(), photo: "", points: 0, matches: 0, leaveKey: "" };
  }
  save(db);
  res.json({ ok: true });
});

app.post("/api/admin/player-action", (req, res) => {
  const db = load();
  if (req.body.pin !== db.cfg.pin) return res.status(401).json({ error: "Clave admin incorrecta" });
  const key = req.body.key;
  const act = req.body.act;
  const p = db.profiles[key];
  if (act !== "del" && !p) return res.status(404).json({ error: "No existe" });
  if (act === "pts") {
    p.points = (p.points || 0) + db.cfg.pts;
  } else if (act === "add") {
    if (db.match.includes(key)) return res.status(409).json({ error: "Ya está en este partido." });
    if (db.match.length >= db.cfg.max) return res.status(409).json({ error: "Cupo lleno." });
    db.match.push(key);
    p.points = (p.points || 0) + db.cfg.pts;
    p.matches = (p.matches || 0) + 1;
  } else if (act === "del") {
    delete db.profiles[key];
    db.match = db.match.filter((x) => x !== key);
  }
  save(db);
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Pichanga PA en http://localhost:${PORT}`);
});

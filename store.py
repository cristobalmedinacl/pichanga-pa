"""Persistencia: JSON local o PostgreSQL (Supabase) si existe DATABASE_URL."""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "db.json")


def empty_db():
    return {
        "cfg": {
            "pin": "admin123",
            "venueId": "laurita",
            "date": "2026-09-19",
            "time": "19:00",
            "max": 14,
            "pts": 50,
            "season": 1,
            "matchInSeason": 1,
        },
        "profiles": {},
        "match": [],
        "votes": {},
    }


def _use_pg():
    return bool(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))


def _conn():
    import psycopg2

    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = url + sep + "sslmode=require"
    return psycopg2.connect(url)


def _ensure_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS app_config (
            id integer PRIMARY KEY DEFAULT 1,
            pin text NOT NULL DEFAULT 'admin123',
            venue_id text NOT NULL DEFAULT 'laurita',
            match_date text NOT NULL DEFAULT '2026-09-19',
            match_time text NOT NULL DEFAULT '19:00',
            max_players integer NOT NULL DEFAULT 14,
            pts integer NOT NULL DEFAULT 50,
            season integer NOT NULL DEFAULT 1,
            match_in_season integer NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS profiles (
            player_key text PRIMARY KEY,
            name text NOT NULL,
            nick text NOT NULL DEFAULT '',
            photo text NOT NULL DEFAULT '',
            points integer NOT NULL DEFAULT 0,
            matches integer NOT NULL DEFAULT 0,
            leave_key text NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS roster (
            sort_order integer NOT NULL,
            player_key text PRIMARY KEY REFERENCES profiles(player_key) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS votes (
            poll_id text NOT NULL,
            player_key text NOT NULL,
            tally integer NOT NULL DEFAULT 0,
            PRIMARY KEY (poll_id, player_key)
        );
        CREATE TABLE IF NOT EXISTS vote_voters (
            poll_id text NOT NULL,
            voter_id text NOT NULL,
            PRIMARY KEY (poll_id, voter_id)
        );
        INSERT INTO app_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
        """
    )


def load():
    if _use_pg():
        return _load_pg()
    return _load_json()


def save(db):
    if _use_pg():
        return _save_pg(db)
    return _save_json(db)


def _load_json():
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = empty_db()
        base.update(data)
        base["cfg"] = {**empty_db()["cfg"], **data.get("cfg", {})}
        if "votes" not in base:
            base["votes"] = {}
        return base
    except Exception:
        db = empty_db()
        _save_json(db)
        return db


def _save_json(db):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def _load_pg():
    conn = _conn()
    try:
        cur = conn.cursor()
        _ensure_schema(cur)
        conn.commit()
        cur.execute(
            "SELECT pin, venue_id, match_date, match_time, max_players, pts, season, match_in_season FROM app_config WHERE id=1"
        )
        row = cur.fetchone()
        db = empty_db()
        if row:
            db["cfg"] = {
                "pin": row[0],
                "venueId": row[1],
                "date": row[2],
                "time": row[3],
                "max": int(row[4]),
                "pts": int(row[5]),
                "season": int(row[6]),
                "matchInSeason": int(row[7]),
            }
        cur.execute("SELECT player_key, name, nick, photo, points, matches, leave_key FROM profiles")
        db["profiles"] = {}
        for k, name, nick, photo, points, matches, leave_key in cur.fetchall():
            db["profiles"][k] = {
                "name": name,
                "nick": nick or "",
                "photo": photo or "",
                "points": int(points or 0),
                "matches": int(matches or 0),
                "leaveKey": leave_key or "",
            }
        cur.execute("SELECT player_key FROM roster ORDER BY sort_order ASC")
        db["match"] = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT poll_id, player_key, tally FROM votes")
        votes = {}
        for poll_id, player_key, tally in cur.fetchall():
            bucket = votes.setdefault(poll_id, {"tally": {}, "voters": []})
            bucket["tally"][player_key] = int(tally)
        cur.execute("SELECT poll_id, voter_id FROM vote_voters")
        for poll_id, voter_id in cur.fetchall():
            bucket = votes.setdefault(poll_id, {"tally": {}, "voters": []})
            bucket["voters"].append(voter_id)
        db["votes"] = votes
        return db
    finally:
        conn.close()


def _save_pg(db):
    cfg = db.get("cfg") or {}
    profiles = db.get("profiles") or {}
    match = db.get("match") or []
    votes = db.get("votes") or {}
    conn = _conn()
    try:
        cur = conn.cursor()
        _ensure_schema(cur)
        cur.execute(
            """
            UPDATE app_config SET
                pin=%s, venue_id=%s, match_date=%s, match_time=%s,
                max_players=%s, pts=%s, season=%s, match_in_season=%s
            WHERE id=1
            """,
            (
                cfg.get("pin") or "admin123",
                cfg.get("venueId") or "laurita",
                cfg.get("date") or "2026-09-19",
                cfg.get("time") or "19:00",
                int(cfg.get("max") or 14),
                int(cfg.get("pts") or 50),
                int(cfg.get("season") or 1),
                int(cfg.get("matchInSeason") or 1),
            ),
        )
        keys = list(profiles.keys())
        if keys:
            cur.execute(
                "DELETE FROM roster WHERE player_key NOT IN %s",
                (tuple(keys),),
            )
            cur.execute(
                "DELETE FROM profiles WHERE player_key NOT IN %s",
                (tuple(keys),),
            )
        else:
            cur.execute("DELETE FROM roster")
            cur.execute("DELETE FROM profiles")
        for k, p in profiles.items():
            cur.execute(
                """
                INSERT INTO profiles (player_key, name, nick, photo, points, matches, leave_key)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (player_key) DO UPDATE SET
                    name=EXCLUDED.name,
                    nick=EXCLUDED.nick,
                    photo=EXCLUDED.photo,
                    points=EXCLUDED.points,
                    matches=EXCLUDED.matches,
                    leave_key=EXCLUDED.leave_key
                """,
                (
                    k,
                    p.get("name") or k,
                    p.get("nick") or "",
                    p.get("photo") or "",
                    int(p.get("points") or 0),
                    int(p.get("matches") or 0),
                    p.get("leaveKey") or "",
                ),
            )
        cur.execute("DELETE FROM roster")
        for i, k in enumerate(match):
            if k not in profiles:
                continue
            cur.execute(
                "INSERT INTO roster (sort_order, player_key) VALUES (%s,%s)",
                (i, k),
            )
        cur.execute("DELETE FROM votes")
        cur.execute("DELETE FROM vote_voters")
        for poll_id, bucket in votes.items():
            tally = (bucket or {}).get("tally") or {}
            voters = (bucket or {}).get("voters") or []
            for pk, n in tally.items():
                cur.execute(
                    "INSERT INTO votes (poll_id, player_key, tally) VALUES (%s,%s,%s)",
                    (poll_id, pk, int(n)),
                )
            for voter in voters:
                cur.execute(
                    "INSERT INTO vote_voters (poll_id, voter_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (poll_id, voter),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

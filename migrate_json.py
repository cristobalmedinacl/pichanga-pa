#!/usr/bin/env python3
"""Carga data/db.json en Supabase. No borra el JSON.
Uso:
  set DATABASE_URL=postgresql://...
  py migrate_json.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(ROOT, "data", "db.json")


def main():
    if not (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")):
        print("Falta DATABASE_URL o SUPABASE_DB_URL")
        sys.exit(1)
    if not os.path.exists(JSON_PATH):
        print("No hay", JSON_PATH, "— se creará config por defecto en Postgres.")
        data = {}
    else:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("Leído", JSON_PATH)
    import store

    db = store.empty_db()
    db.update(data)
    db["cfg"] = {**store.empty_db()["cfg"], **data.get("cfg", {})}
    db["profiles"] = data.get("profiles") or {}
    db["match"] = data.get("match") or []
    db["votes"] = data.get("votes") or {}
    print("Perfiles:", len(db["profiles"]), "en plantel:", len(db["match"]))
    store.save(db)
    check = store.load()
    print("OK en Postgres. Perfiles ahora:", len(check.get("profiles") or {}))
    print("No se borró el JSON original.")


if __name__ == "__main__":
    main()

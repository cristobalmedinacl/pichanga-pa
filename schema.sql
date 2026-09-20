-- Pegar en Supabase → SQL Editor → Run
-- Plan gratis. No requiere tablas extra.

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

ALTER TABLE app_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE roster ENABLE ROW LEVEL SECURITY;
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE vote_voters ENABLE ROW LEVEL SECURITY;
-- Sin políticas para anon/authenticated: solo la conexión del servidor (DATABASE_URL) accede.

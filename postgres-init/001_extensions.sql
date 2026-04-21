-- PostgreSQL Extensions — auto-applied on first container start
-- Container: pgvector/pgvector:pg17 mounted /docker-entrypoint-initdb.d
--
-- WICHTIG: pg_stat_statements muss in postgresql.conf via shared_preload_libraries
-- geladen sein (docker-compose command: -c shared_preload_libraries=pg_stat_statements).
-- CREATE EXTENSION IF NOT EXISTS alleine reicht nicht.

CREATE EXTENSION IF NOT EXISTS vector;            -- pgvector (Hindsight, Memory-Fusion)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Query-Performance-Tracking
CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- Trigram-Similarity (fuzzy search in agent-audit / skills)

-- Optional (nicht enabled):
-- CREATE EXTENSION IF NOT EXISTS postgis;         -- Geo-Data (nicht benötigt)
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;        -- Postgres-native crypto (wir nutzen AESGCMVault Go-side)

-- Verification:
--   SELECT extname, extversion FROM pg_extension ORDER BY extname;
--   SELECT * FROM pg_stat_statements LIMIT 5;  -- sollte leer sein initial, füllt sich bei queries

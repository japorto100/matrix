use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

use redb::{Database, TableDefinition};

const OHLCV_CACHE_TABLE: TableDefinition<&str, &[u8]> = TableDefinition::new("ohlcv_cache_v1");
static DB_CACHE: OnceLock<Mutex<HashMap<String, Arc<Database>>>> = OnceLock::new();

fn current_unix_ms() -> u64 {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    duration.as_millis() as u64
}

fn encode_record(expires_at_ms: u64, payload: &str) -> Vec<u8> {
    let mut out = expires_at_ms.to_string().into_bytes();
    out.push(b'\n');
    out.extend_from_slice(payload.as_bytes());
    out
}

fn decode_record(bytes: &[u8]) -> Option<(u64, String)> {
    let split = bytes.iter().position(|byte| *byte == b'\n')?;
    let expires = std::str::from_utf8(&bytes[..split])
        .ok()?
        .parse::<u64>()
        .ok()?;
    let payload = String::from_utf8(bytes[split + 1..].to_vec()).ok()?;
    Some((expires, payload))
}

fn db_cache() -> &'static Mutex<HashMap<String, Arc<Database>>> {
    DB_CACHE.get_or_init(|| Mutex::new(HashMap::new()))
}

fn open_database(path: &str) -> Result<Arc<Database>, String> {
    let cache = db_cache();
    {
        let guard = cache
            .lock()
            .map_err(|_| "db cache mutex poisoned".to_string())?;
        if let Some(db) = guard.get(path) {
            return Ok(Arc::clone(db));
        }
    }

    let db =
        Arc::new(Database::create(path).map_err(|error| format!("redb create/open: {error}"))?);
    let mut guard = cache
        .lock()
        .map_err(|_| "db cache mutex poisoned".to_string())?;
    let entry = guard
        .entry(path.to_string())
        .or_insert_with(|| Arc::clone(&db));
    Ok(Arc::clone(entry))
}

pub fn cache_set(path: &str, key: &str, payload_json: &str, ttl_ms: u64) -> Result<(), String> {
    if ttl_ms == 0 {
        return Err("ttl_ms must be > 0".to_string());
    }

    let expires_at_ms = current_unix_ms().saturating_add(ttl_ms);
    let db = open_database(path)?;
    let write_txn = db
        .begin_write()
        .map_err(|error| format!("redb begin_write: {error}"))?;
    {
        let mut table = write_txn
            .open_table(OHLCV_CACHE_TABLE)
            .map_err(|error| format!("redb open_table(write): {error}"))?;
        let record = encode_record(expires_at_ms, payload_json);
        table
            .insert(key, record.as_slice())
            .map_err(|error| format!("redb insert: {error}"))?;
    }
    write_txn
        .commit()
        .map_err(|error| format!("redb commit: {error}"))?;
    Ok(())
}

pub fn cache_get(path: &str, key: &str, now_ms: Option<u64>) -> Result<Option<String>, String> {
    let db = open_database(path)?;
    let read_txn = db
        .begin_read()
        .map_err(|error| format!("redb begin_read: {error}"))?;
    let table = read_txn
        .open_table(OHLCV_CACHE_TABLE)
        .map_err(|error| format!("redb open_table(read): {error}"))?;

    let Some(value) = table
        .get(key)
        .map_err(|error| format!("redb get: {error}"))?
    else {
        return Ok(None);
    };

    let (expires_at_ms, payload) =
        decode_record(value.value()).ok_or_else(|| "invalid cache record".to_string())?;
    let now = now_ms.unwrap_or_else(current_unix_ms);
    if now > expires_at_ms {
        return Ok(None);
    }
    Ok(Some(payload))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn record_roundtrip() {
        let encoded = encode_record(12345, r#"{"ok":true}"#);
        let decoded = decode_record(&encoded).expect("decode record");
        assert_eq!(decoded.0, 12345);
        assert_eq!(decoded.1, r#"{"ok":true}"#);
    }

    #[test]
    fn cache_set_get_roundtrip() {
        let temp = tempdir().expect("tempdir");
        let db_path = temp.path().join("ohlcv-cache.redb");
        let db_path_string = db_path.to_string_lossy().to_string();

        cache_set(&db_path_string, "AAPL:1D:30", r#"{"candles":[1]}"#, 60_000).expect("cache_set");
        let got = cache_get(&db_path_string, "AAPL:1D:30", None).expect("cache_get");
        assert_eq!(got.as_deref(), Some(r#"{"candles":[1]}"#));
    }

    #[test]
    fn expired_entry_returns_none() {
        let temp = tempdir().expect("tempdir");
        let db_path = temp.path().join("ohlcv-cache-expired.redb");
        let db_path_string = db_path.to_string_lossy().to_string();

        cache_set(&db_path_string, "BTCUSD:1H:200", r#"{"candles":[42]}"#, 10).expect("cache_set");
        let future_now = current_unix_ms().saturating_add(60_000);
        let got = cache_get(&db_path_string, "BTCUSD:1H:200", Some(future_now)).expect("cache_get");
        assert_eq!(got, None);
    }
}

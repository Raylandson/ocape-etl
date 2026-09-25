use std::path::{Path, PathBuf};

use rusqlite::{Connection, OpenFlags};

pub const SNAPSHOT_FILE_NAME: &str = "datajud_pe.sqlite";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Source {
    File(PathBuf),
    #[cfg_attr(not(feature = "embedded-snapshot"), allow(dead_code))]
    Embedded,
}

impl Source {
    pub fn describe(&self) -> String {
        match self {
            Source::File(path) => path.display().to_string(),
            Source::Embedded => "Cópia embutida no executável".to_string(),
        }
    }
}

#[cfg(feature = "embedded-snapshot")]
static EMBEDDED_SNAPSHOT: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/snapshot.sqlite.z"));

pub fn resolve() -> Option<Source> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--db" {
            return args.next().map(|p| Source::File(PathBuf::from(p)));
        }
        if let Some(p) = arg.strip_prefix("--db=") {
            return Some(Source::File(PathBuf::from(p)));
        }
    }

    if let Ok(p) = std::env::var("DATAJUD_DB")
        && !p.trim().is_empty()
    {
        return Some(Source::File(PathBuf::from(p)));
    }

    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(exe) = std::env::current_exe()
        && let Some(dir) = exe.parent()
    {
        candidates.push(dir.join(SNAPSHOT_FILE_NAME));
    }
    candidates.push(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("data")
            .join("exports")
            .join("datajud")
            .join(SNAPSHOT_FILE_NAME),
    );

    if let Some(found) = candidates.into_iter().find(|p| p.is_file()) {
        return Some(Source::File(found.canonicalize().unwrap_or(found)));
    }

    if cfg!(feature = "embedded-snapshot") {
        return Some(Source::Embedded);
    }

    None
}

pub fn open(source: &Source) -> Result<Connection, String> {
    match source {
        Source::File(path) => {
            if !path.is_file() {
                return Err(format!("Arquivo não encontrado: {}", path.display()));
            }
            Connection::open_with_flags(
                path,
                OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
            )
            .map_err(|e| format!("Não foi possível abrir {}: {e}", path.display()))
        }
        Source::Embedded => open_embedded(),
    }
}

#[cfg(feature = "embedded-snapshot")]
fn open_embedded() -> Result<Connection, String> {
    let (len_bytes, compressed) = EMBEDDED_SNAPSHOT.split_at(8);
    let len = u64::from_le_bytes(len_bytes.try_into().expect("8-byte header")) as usize;
    let decoder = flate2::read::ZlibDecoder::new(compressed);
    let mut conn = Connection::open_in_memory().map_err(|e| e.to_string())?;
    conn.deserialize_read_exact("main", decoder, len, true)
        .map_err(|e| format!("Falha ao descompactar a base embutida: {e}"))?;
    Ok(conn)
}

#[cfg(not(feature = "embedded-snapshot"))]
fn open_embedded() -> Result<Connection, String> {
    Err("Este executável foi compilado sem a base embutida.".to_string())
}

#[cfg(all(test, feature = "embedded-snapshot"))]
mod tests {
    #[test]
    fn embedded_snapshot_loads() {
        let ds = crate::data::store::load(super::Source::Embedded).expect("embedded snapshot");
        assert!(ds.rows.len() > 90_000);
    }
}

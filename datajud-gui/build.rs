use std::fs::File;
use std::io::{BufReader, BufWriter, Write};
use std::path::PathBuf;

fn main() {
    println!("cargo:rerun-if-env-changed=DATAJUD_SNAPSHOT");
    if std::env::var_os("CARGO_FEATURE_EMBEDDED_SNAPSHOT").is_none() {
        return;
    }

    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let snapshot = std::env::var_os("DATAJUD_SNAPSHOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| manifest_dir.join("../data/exports/datajud/datajud_pe.sqlite"));
    println!("cargo:rerun-if-changed={}", snapshot.display());

    let input = File::open(&snapshot).unwrap_or_else(|e| {
        panic!(
            "embedded-snapshot: não foi possível abrir {} ({e}). \
             Gere-o com `uv run python src/export_datajud_sqlite.py` ou defina DATAJUD_SNAPSHOT.",
            snapshot.display()
        )
    });
    let len = input.metadata().unwrap().len();

    let out_path = PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("snapshot.sqlite.z");
    let mut out = BufWriter::new(File::create(&out_path).unwrap());
    out.write_all(&len.to_le_bytes()).unwrap();
    let mut encoder = flate2::write::ZlibEncoder::new(out, flate2::Compression::best());
    std::io::copy(&mut BufReader::new(input), &mut encoder).unwrap();
    encoder.finish().unwrap().flush().unwrap();
}

"""Exports public.processos_conflitos_judiciais to a SQLite snapshot for datajud-gui."""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from src.config import EXPORTS_DIR
from src.database import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
SOURCE_TABLE = "public.processos_conflitos_judiciais"
DEFAULT_OUT = EXPORTS_DIR / "datajud" / "datajud_pe.sqlite"

COLUMNS = [
    ("id", "TEXT PRIMARY KEY"),
    ("numero_processo", "TEXT NOT NULL"),
    ("tribunal", "TEXT NOT NULL"),
    ("grau", "TEXT"),
    ("data_ajuizamento", "TEXT"),
    ("categoria_conflito", "TEXT NOT NULL"),
    ("classe_codigo", "INTEGER"),
    ("classe_nome", "TEXT"),
    ("assuntos_codigos", "TEXT"),
    ("assuntos_nomes", "TEXT"),
    ("assuntos_str", "TEXT"),
    ("orgao_julgador_codigo", "INTEGER"),
    ("orgao_julgador_nome", "TEXT"),
    ("municipio_ibge", "INTEGER"),
    ("municipio_nome", "TEXT"),
    ("ultimo_movimento", "TEXT"),
    ("data_ultimo_movimento", "TEXT"),
    ("total_movimentos", "INTEGER"),
    ("url_consulta_publica", "TEXT"),
    ("comarca_sede_nome", "TEXT"),
    ("comarca_sede_ibge", "INTEGER"),
    ("municipios_abrangidos", "TEXT"),
    ("total_municipios_abrangidos", "INTEGER"),
    ("tem_municipios_filhos", "INTEGER"),
    ("tipo_jurisdicao", "TEXT"),
    ("lat", "REAL"),
    ("lon", "REAL"),
]

ARRAY_COLUMNS = {"assuntos_codigos", "assuntos_nomes"}


def _select_sql() -> str:
    exprs = []
    for name, _ in COLUMNS:
        if name == "lat":
            exprs.append("ST_Y(geometry) AS lat")
        elif name == "lon":
            exprs.append("ST_X(geometry) AS lon")
        else:
            exprs.append(name)
    return f"SELECT {', '.join(exprs)} FROM {SOURCE_TABLE} ORDER BY id"


def _to_sqlite_value(name: str, value):
    if value is None:
        return None
    if name in ARRAY_COLUMNS:
        return json.dumps(list(value), ensure_ascii=False)
    if isinstance(value, datetime):
        if value.hour == value.minute == value.second == 0:
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, bool):
        return int(value)
    return value


def export_snapshot(out_path: Path = DEFAULT_OUT) -> Path:
    start = time.time()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    logger.info(f"Reading {SOURCE_TABLE} from PostgreSQL...")
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(_select_sql())).fetchall()
    logger.info(f"Fetched {len(rows)} lawsuits. Writing SQLite snapshot...")

    names = [name for name, _ in COLUMNS]
    ddl = ",\n    ".join(f"{name} {decl}" for name, decl in COLUMNS)
    placeholders = ", ".join("?" for _ in names)

    db = sqlite3.connect(tmp_path)
    try:
        db.execute(f"CREATE TABLE lawsuits (\n    {ddl}\n)")
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.executemany(
            f"INSERT INTO lawsuits ({', '.join(names)}) VALUES ({placeholders})",
            ([_to_sqlite_value(n, v) for n, v in zip(names, row)] for row in rows),
        )
        meta = {
            "schema_version": str(SCHEMA_VERSION),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_table": SOURCE_TABLE,
            "row_count": str(len(rows)),
        }
        db.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta.items())
        db.commit()
        db.execute("VACUUM")
    finally:
        db.close()

    os.replace(tmp_path, out_path)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info(
        f"Snapshot written: {out_path} ({len(rows)} lawsuits, {size_mb:.1f} MB) "
        f"in {time.time() - start:.1f}s"
    )
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export DataJud lawsuits to a SQLite snapshot for datajud-gui")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output path (default: {DEFAULT_OUT})")
    args = parser.parse_args()
    export_snapshot(args.out)

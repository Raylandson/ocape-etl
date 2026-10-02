"""
Server-side OGC KML 2.2 writer.

A port of `frontend/src/app/services/kml-export.service.ts`, kept deliberately faithful so a
bulk export looks identical to the single-feature export that popup button produces.

Two deliberate differences from the TypeScript original:

* **Geometry is not built here.** It arrives as a ready `<Polygon>` / `<MultiGeometry>` fragment
  from PostGIS `ST_AsKML`, which also handles `MultiPoint` and (behind an `ST_CollectionExtract`
  guard) `GeometryCollection` — two cases the TS `geometryToKml` silently dropped, losing
  geometry on 1,028 features. Keeping geometry out also keeps this module pure and testable
  with no database.
* **Dates are parsed properly.** The TS used `Date.parse`, which reads `08/07/2020` as US
  month-first. Here `dd/mm/yyyy` and ISO are both understood.

This module must not import `src.database`: it stays importable with no live connection.
"""

from __future__ import annotations

import json
import math
import re
import time
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import islice
from typing import Any, Iterable, Iterator

DEFAULT_FILL = "#3b82f6"
DEFAULT_BORDER = "#1d4ed8"
DEFAULT_LAYER_NAME = "Feições Selecionadas"
FALLBACK_TITLE_LAYER = "Feição"

#: Rendered elsewhere, or pure noise in a balloon.
SKIP_FIELDS = {"geometry", "geom", "the_geom", "shape", "cor_hex", "id", "ogc_fid", "objectid"}

_COMBINING = re.compile(r"[̀-ͯ]")
_UNSAFE_FILENAME = re.compile(r"[^a-zA-Z0-9_\-.]")
_REPEATED_UNDERSCORE = re.compile(r"_+")
_HEX_COLOR = re.compile(r"^#?[0-9a-fA-F]{3,8}$")


@dataclass
class KmlItem:
    """One feature to place in the document. `geometry_kml` comes from `ST_AsKML`."""
    geometry_kml: str
    properties: dict[str, Any] = field(default_factory=dict)
    #: `search_index.label`, the title each layer declares in SEARCH_SOURCES. Preferred over
    #: the inherited property chain, which has no entry for several layers (`terrai_nom` on
    #: tis_poligonais, for one) and falls back to a useless "<Layer> (ID: n)" for them.
    title: str | None = None
    layer_id: str | None = None
    layer_name: str | None = None
    fill_color: str | None = None
    border_color: str | None = None
    #: Free text a user attached to this feature in a saved selection; rendered as "Observação".
    note: str | None = None


# --------------------------------------------------------------------------- primitives

def hex_to_kml_color(hex_color: str | None, default_alpha: str = "ff") -> str:
    """CSS `#RRGGBB[AA]` to Google Earth `AABBGGRR`."""
    if not hex_color:
        return "ff000000"
    clean = str(hex_color).replace("#", "").strip()
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    r = g = b = "00"
    a = default_alpha
    if len(clean) >= 6:
        r, g, b = clean[0:2], clean[2:4], clean[4:6]
    if len(clean) >= 8:
        a = clean[6:8]
    return f"{a}{b}{g}{r}".lower()


def is_valid_hex_color(value: Any) -> bool:
    """Guards colours supplied by the client before they reach the XML."""
    return isinstance(value, str) and bool(_HEX_COLOR.match(value))


#: XML 1.0 forbids these outright (even escaped): C0 controls except tab/LF/CR, and lone
#: surrogates, which would also make `.encode("utf-8")` raise. Text pasted from Word or a PDF
#: carries them easily, and one is enough to make Google Earth reject the whole file.
_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def escape_xml(value: Any) -> str:
    if value is None:
        return ""
    return (
        _XML_ILLEGAL.sub("", str(value))
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def sanitize_filename(name: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(name))
    stripped = _COMBINING.sub("", decomposed)
    safe = _UNSAFE_FILENAME.sub("_", stripped)
    return _REPEATED_UNDERSCORE.sub("_", safe).lower()


def _truthy(props: dict[str, Any], key: str) -> Any:
    """Mirrors JS `||` chaining, where '' and 0 fall through to the next candidate."""
    value = props.get(key)
    return value if value else None


def feature_title(properties: dict[str, Any] | None, layer_name: str = FALLBACK_TITLE_LAYER) -> str:
    # `is None`, not falsiness: an empty dict is falsy in Python but truthy in JS, and the
    # original falls through to the "<layer> (ID: 1)" rung for it.
    if properties is None:
        return layer_name

    for key in ("nome_imovel", "nome_area", "nome_imove", "no_projeto", "nome_uc", "nomeuc",
                "nm_fcu", "comunidade", "nome", "traditional_name"):
        value = _truthy(properties, key)
        if value:
            return str(value)

    for key, prefix in (("numero_processo", "Processo CNJ "), ("processo", "Processo ANM "),
                        ("cod_imovel", "CAR "), ("codigo_imo", "SIGEF "),
                        ("alertcode", "Alerta #"), ("numero_ai", "Auto #"),
                        ("numero_emb", "Embargo #")):
        value = _truthy(properties, key)
        if value:
            return f"{prefix}{value}"

    ident = (_truthy(properties, "id") or _truthy(properties, "objectid")
             or _truthy(properties, "fid") or "1")
    return f"{layer_name} (ID: {ident})"


# --------------------------------------------------------------------------- formatting

def format_number_pt_br(value: Any, max_fraction_digits: int = 4) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    text = f"{number:,.{max_fraction_digits}f}"
    integer, _, fraction = text.partition(".")
    fraction = fraction.rstrip("0")
    integer = integer.replace(",", ".")
    return f"{integer},{fraction}" if fraction else integer


def format_date_pt_br(value: Any) -> str | None:
    """Accepts `dd/mm/yyyy` and ISO dates/timestamps; returns `dd/mm/yyyy`."""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    if not isinstance(value, str):
        return None
    text = value.strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        return text
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return f"{iso.group(3)}/{iso.group(2)}/{iso.group(1)}"
    return None


def _display_value(key: str, value: Any) -> str:
    lowered = key.lower()
    if "area" in lowered:
        formatted = format_number_pt_br(value)
        if formatted is not None:
            return f"{formatted} ha"
    if "data" in lowered:
        formatted = format_date_pt_br(value)
        if formatted is not None:
            return formatted
    return str(value)


def _humanize(key: str) -> str:
    return " ".join(part.capitalize() if part else part for part in key.split("_"))


# --------------------------------------------------------------------------- fragments

def html_description(title: str, layer_name: str, properties: dict[str, Any],
                     note: str | None = None) -> str:
    """The styled balloon table. CDATA-wrapped, but values are still escaped so a stray
    `]]>` in the data cannot terminate the section early."""
    rows = []
    for key, value in (properties or {}).items():
        if key.lower() in SKIP_FIELDS or value is None or value == "":
            continue
        rows.append(
            '\n        <tr style="border-bottom: 1px solid #f1f5f9;">\n'
            f'          <td style="padding: 4px 6px; font-size: 11px; font-weight: 600; color: #475569; width: 38%;">{escape_xml(_humanize(key))}:</td>\n'
            f'          <td style="padding: 4px 6px; font-size: 11px; color: #0f172a; word-break: break-word;">{escape_xml(_display_value(key, value))}</td>\n'
            "        </tr>"
        )

    note_html = ""
    if note and note.strip():
        note_html = (
            '<div style="margin-bottom: 8px; padding: 6px 8px; background: #fffbeb; '
            'border: 1px solid #fde68a; border-radius: 4px; font-size: 11px; color: #78350f;">'
            f'<strong>Observação:</strong> {escape_xml(note.strip())}</div>'
        )

    return f"""<![CDATA[
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 360px; color: #1e293b;">
        <div style="background-color: #0f172a; color: #ffffff; padding: 8px 12px; border-radius: 6px 6px 0 0;">
          <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.85;">{escape_xml(layer_name)}</div>
          <div style="font-size: 14px; font-weight: 600; margin-top: 2px;">{escape_xml(title)}</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-top: none; border-radius: 0 0 6px 6px; padding: 8px;">
          {note_html}
          <table style="width: 100%; border-collapse: collapse;">
            <tbody>{''.join(rows)}
            </tbody>
          </table>
          <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: right;">
            Plataforma de Mapeamento de Conflitos Agrários • PE
          </div>
        </div>
      </div>
    ]]>"""


def extended_data(properties: dict[str, Any]) -> str:
    """`<ExtendedData>` so QGIS and ArcGIS get a real attribute table."""
    tags = []
    for key, value in (properties or {}).items():
        if value is None:
            continue
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        tags.append(f'      <Data name="{escape_xml(key)}"><value>{escape_xml(text)}</value></Data>')
    return "    <ExtendedData>\n" + "\n".join(tags) + "\n    </ExtendedData>"


def build_placemark(item: KmlItem, style_id: str | None = None) -> str:
    properties = item.properties or {}
    layer_name = item.layer_name or FALLBACK_TITLE_LAYER
    title = item.title or feature_title(properties, layer_name)
    style_url = f"\n      <styleUrl>#{style_id}</styleUrl>" if style_id else ""
    return f"""
    <Placemark>
      <name>{escape_xml(title)}</name>{style_url}
      <description>{html_description(title, layer_name, properties, item.note)}</description>
{extended_data(properties)}
      {item.geometry_kml}
    </Placemark>"""


# --------------------------------------------------------------------------- document

def _style_key(item: KmlItem) -> tuple[str, str, str]:
    return (item.layer_id or "default",
            item.fill_color or DEFAULT_FILL,
            item.border_color or DEFAULT_BORDER)


def build_document(document_name: str, items: Iterable[KmlItem]) -> str:
    """A complete KML document: one `<Style>` per layer/colour combination, one `<Folder>`
    per layer named `"<Layer> (<n>)"`."""
    items = list(items)

    styles: dict[tuple[str, str, str], str] = {}
    for item in items:
        key = _style_key(item)
        if key not in styles:
            styles[key] = f"style_{item.layer_id or 'layer'}_{len(styles) + 1}"

    styles_xml = "".join(
        f"""
    <Style id="{style_id}">
      <LineStyle>
        <color>{hex_to_kml_color(border if is_valid_hex_color(border) else DEFAULT_BORDER, 'ff')}</color>
        <width>2.2</width>
      </LineStyle>
      <PolyStyle>
        <color>{hex_to_kml_color(fill if is_valid_hex_color(fill) else DEFAULT_FILL, '66')}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
      <IconStyle>
        <color>{hex_to_kml_color(border if is_valid_hex_color(border) else DEFAULT_BORDER, 'ff')}</color>
        <scale>1.1</scale>
      </IconStyle>
    </Style>"""
        for (_, fill, border), style_id in styles.items()
    )

    folders: dict[str, list[KmlItem]] = {}
    for item in items:
        folders.setdefault(item.layer_name or DEFAULT_LAYER_NAME, []).append(item)

    folders_xml = "\n".join(
        f"""
    <Folder>
      <name>{escape_xml(name)} ({len(group)})</name>
      {''.join(build_placemark(i, styles[_style_key(i)]) for i in group)}
    </Folder>"""
        for name, group in folders.items()
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape_xml(document_name)}</name>
    <description><![CDATA[Exportação KML gerada pela Plataforma de Mapeamento de Conflitos Agrários de Pernambuco.]]></description>
{styles_xml}
{folders_xml}
  </Document>
</kml>"""


# --------------------------------------------------------------------------- archive

@dataclass
class LayerGroup:
    """One layer's worth of an export. `items` may be a generator streamed from the database;
    `count` comes from the preview query and is what the folder label and any splitting use."""
    layer_id: str
    layer_name: str
    count: int
    items: Iterable[KmlItem]
    fill_color: str | None = None
    border_color: str | None = None


class _UnseekableSink:
    """Minimal file-like target for `zipfile`.

    It deliberately has no `seek`, which makes ZipFile emit data descriptors instead of
    rewinding to patch headers — the thing that lets the archive be produced as a stream.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._position = 0

    def write(self, data: bytes) -> int:
        self._buffer += data
        self._position += len(data)
        return len(data)

    def tell(self) -> int:
        return self._position

    def flush(self) -> None:  # pragma: no cover - required by the interface
        pass

    def drain(self) -> bytes:
        chunk = bytes(self._buffer)
        self._buffer.clear()
        return chunk


def _zip_entry(name: str) -> "zipfile.ZipInfo":
    info = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def _resolved_colors(group: LayerGroup) -> tuple[str, str]:
    fill = group.fill_color if is_valid_hex_color(group.fill_color) else DEFAULT_FILL
    border = group.border_color if is_valid_hex_color(group.border_color) else DEFAULT_BORDER
    return fill, border


def _layer_document_chunks(group: LayerGroup, size: int, items: "Iterator[KmlItem]"):
    """Yields a complete KML document in pieces, so a 25k-placemark file never exists in
    memory all at once."""
    style_id = f"style_{group.layer_id or 'layer'}_1"
    fill, border = _resolved_colors(group)

    yield f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape_xml(group.layer_name)}</name>
    <description><![CDATA[Exportação KML gerada pela Plataforma de Mapeamento de Conflitos Agrários de Pernambuco.]]></description>
    <Style id="{style_id}">
      <LineStyle>
        <color>{hex_to_kml_color(border, 'ff')}</color>
        <width>2.2</width>
      </LineStyle>
      <PolyStyle>
        <color>{hex_to_kml_color(fill, '66')}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
      <IconStyle>
        <color>{hex_to_kml_color(border, 'ff')}</color>
        <scale>1.1</scale>
      </IconStyle>
    </Style>
    <Folder>
      <name>{escape_xml(group.layer_name)} ({size})</name>"""

    for item in islice(items, size):
        yield build_placemark(item, style_id)

    yield """
    </Folder>
  </Document>
</kml>"""


def stream_archive(
    groups: Iterable[LayerGroup],
    *,
    grouping: str = "layer",
    readme_text: str = "",
    max_per_file: int = 25_000,
) -> "Iterator[bytes]":
    """Streams a ZIP archive of the export.

    `grouping="layer"` writes one KML per layer, split into `_parteNN` files beyond
    `max_per_file` placemarks. `grouping="feature"` writes one KML per feature under a
    per-layer directory, with a row-number suffix because feature titles collide heavily
    (36 duplicate `cod_imovel` values in `area_imovel_1`; `apps_1` has 273k rows over 47k codes).
    """
    sink = _UnseekableSink()
    archive = zipfile.ZipFile(sink, "w", zipfile.ZIP_DEFLATED)

    def drain():
        chunk = sink.drain()
        if chunk:
            return chunk
        return None

    try:
        for group in groups:
            slug = sanitize_filename(group.layer_id or group.layer_name or "camada")

            if grouping == "feature":
                for index, item in enumerate(group.items, start=1):
                    title = item.title or feature_title(item.properties, item.layer_name or group.layer_name)
                    name = f"{slug}/{sanitize_filename(title)}_{index}.kml"
                    document = build_document(f"{group.layer_name} - {title}", [item])
                    with archive.open(_zip_entry(name), "w") as handle:
                        handle.write(document.encode("utf-8"))
                    chunk = drain()
                    if chunk:
                        yield chunk
                continue

            total = max(0, int(group.count or 0))
            parts = max(1, math.ceil(total / max_per_file)) if total else 1
            items = iter(group.items)
            for part in range(parts):
                size = min(max_per_file, total - part * max_per_file) if total else 0
                name = f"{slug}.kml" if parts == 1 else f"{slug}_parte{part + 1:02d}.kml"
                with archive.open(_zip_entry(name), "w") as handle:
                    for piece in _layer_document_chunks(group, size, items):
                        handle.write(piece.encode("utf-8"))
                        chunk = drain()
                        if chunk:
                            yield chunk
                chunk = drain()
                if chunk:
                    yield chunk

        with archive.open(_zip_entry("LEIAME.txt"), "w") as handle:
            handle.write(readme_text.encode("utf-8"))
        chunk = drain()
        if chunk:
            yield chunk
    finally:
        archive.close()

    chunk = drain()
    if chunk:
        yield chunk

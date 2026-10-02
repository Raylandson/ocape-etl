"""
Compiles a saved-filter definition into parameterised SQL over `public.search_index`.

Design notes that matter:

* **Nothing a user types becomes SQL text.** Every condition reads `search_index.props`, which
  is jsonb, so a field name is a *value* (`props -> :p3`) rather than an identifier. Combined
  with a syntactic check and a catalog membership check, there is no injection surface. The
  only structural interpolation is a comparison symbol taken from a frozen table.
* **Spatial conditions compile to a materialised CTE driven from the target layer.** Measured
  on CAR x Terras Indigenas: the correlated `EXISTS` form takes 13,960 ms because it probes the
  shared GIST index 429,750 times, while this form takes 226 ms. The shape is not optional.
* **Numeric and date access is guarded by `CASE`.** A bare cast raises on the first row holding
  non-numeric text, and an `AND`-chained `jsonb_typeof` guard is not safe either because the
  planner may reorder `AND` operands. `CASE` arms only evaluate when their `WHEN` holds.

Pure by design: it must not import `src.database`, so it stays unit-testable with no server.

One hard constraint on the generated text: casts must be written `CAST(:p AS type)`, never
`:p::type`. SQLAlchemy's bind-parameter regex ends with a `(?!:)` lookahead, so a placeholder
immediately followed by `::` is silently left as literal SQL and never bound.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

SCHEMA_VERSION = 1
INDEX_TABLE = "search_index"

#: Field and layer names must look like plain PostgreSQL identifiers before anything else runs.
_NAME = re.compile(r"[a-z_][a-z0-9_]{0,62}")

_NUMERIC_TYPES = {"double precision", "numeric", "integer", "bigint", "real", "smallint"}
_DATE_TYPES = {"date", "timestamp without time zone", "timestamp with time zone"}

_COMPARISONS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
_DATE_COMPARISONS = {"date_gt": ">", "date_gte": ">=", "date_lt": "<", "date_lte": "<="}

TEXT_OPS = {"contains", "not_contains", "starts_with"}
SET_OPS = {"in", "not_in"}
NULL_OPS = {"is_null", "is_not_null"}
RANGE_OPS = {"between", "date_between"}
EQUALITY_OPS = {"eq", "neq"}

VALID_OPS = (EQUALITY_OPS | TEXT_OPS | SET_OPS | NULL_OPS | RANGE_OPS
             | set(_COMPARISONS) | set(_DATE_COMPARISONS))

SPATIAL_RELATIONS = {"intersects", "not_intersects"}
SELECT_MODES = ("count", "count_by_layer", "features", "ids")

Catalog = Mapping[str, Mapping[str, str]]


class FilterError(ValueError):
    """A filter definition that cannot be compiled. The message names the offending value."""


@dataclass(frozen=True)
class CompiledFilter:
    sql: str
    params: dict[str, Any]
    layers: tuple[str, ...]


class _Params:
    """One flat namespace for every bound value, so names cannot collide across blocks."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self._n = 0

    def add(self, value: Any) -> str:
        name = f"p{self._n}"
        self._n += 1
        self.values[name] = value
        return name


def _check_name(value: Any, what: str, context: str = "") -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        where = f" em '{context}'" if context else ""
        raise FilterError(f"{what} inválido{where}: {value!r}")
    return value


def _escape_like(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def field_kind(data_type: str) -> str:
    """Maps an information_schema type onto the accessor the compiler should use."""
    lowered = (data_type or "").lower()
    if lowered in _NUMERIC_TYPES:
        return "number"
    if lowered in _DATE_TYPES:
        return "date"
    return "text"


def _numeric_accessor(field_param: str) -> str:
    return (
        "CASE\n"
        f"             WHEN jsonb_typeof(s.props -> :{field_param}) = 'number'\n"
        f"               THEN (s.props ->> :{field_param})::numeric\n"
        f"             WHEN jsonb_typeof(s.props -> :{field_param}) = 'string'\n"
        f"                    AND s.props ->> :{field_param} ~ '^\\s*-?[0-9]+([.,][0-9]+)?\\s*$'\n"
        f"               THEN replace(btrim(s.props ->> :{field_param}), ',', '.')::numeric\n"
        "           END"
    )


def _date_accessor(field_param: str) -> str:
    return (
        "CASE\n"
        f"             WHEN s.props ->> :{field_param} ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$'\n"
        f"               THEN to_date(s.props ->> :{field_param}, 'DD/MM/YYYY')\n"
        f"             WHEN s.props ->> :{field_param} ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}'\n"
        f"               THEN substring(s.props ->> :{field_param}, 1, 10)::date\n"
        "           END"
    )


def _containment(field_param: str, value: Any, kind: str, params: _Params) -> str:
    """`props @> jsonb_build_object(k, v)` is 6x faster than `props ->> k = v` and, more
    importantly, gives the planner a correct row estimate."""
    cast = "numeric" if kind == "number" else "text"
    value_param = params.add(value)
    return f"s.props @> jsonb_build_object(:{field_param}, CAST(:{value_param} AS {cast}))"


def _compile_condition(condition: Mapping[str, Any], layer: str, columns: Mapping[str, str],
                       params: _Params) -> str:
    if not isinstance(condition, Mapping):
        raise FilterError(f"condição inválida em '{layer}': {condition!r}")

    op = condition.get("op")
    if op not in VALID_OPS:
        raise FilterError(f"op desconhecido em '{layer}': {op!r}")

    field = _check_name(condition.get("field"), "campo", layer)
    if field not in columns:
        raise FilterError(f"campo '{field}' não existe na camada '{layer}'")

    kind = field_kind(columns[field])
    field_param = params.add(field)
    value = condition.get("value")

    if op in EQUALITY_OPS:
        clause = _containment(field_param, value, kind, params)
        return clause if op == "eq" else f"NOT ({clause})"

    if op in SET_OPS:
        values = value if isinstance(value, (list, tuple)) else [value]
        if not values:
            raise FilterError(f"operador '{op}' exige ao menos um valor em '{layer}'")
        joined = " OR ".join(_containment(field_param, v, kind, params) for v in values)
        return f"({joined})" if op == "in" else f"NOT ({joined})"

    if op in NULL_OPS:
        clause = (f"(s.props -> :{field_param} IS NULL "
                  f"OR jsonb_typeof(s.props -> :{field_param}) = 'null')")
        return clause if op == "is_null" else f"NOT {clause}"

    if op in TEXT_OPS:
        value_param = params.add(_escape_like(value))
        pattern = (f"lower(unaccent(:{value_param})) || '%'" if op == "starts_with"
                   else f"'%' || lower(unaccent(:{value_param})) || '%'")
        clause = f"lower(unaccent(s.props ->> :{field_param})) LIKE {pattern}"
        return f"NOT ({clause})" if op == "not_contains" else clause

    if op in _COMPARISONS:
        value_param = params.add(value)
        return f"({_numeric_accessor(field_param)}) {_COMPARISONS[op]} CAST(:{value_param} AS numeric)"

    if op in _DATE_COMPARISONS:
        value_param = params.add(value)
        return f"({_date_accessor(field_param)}) {_DATE_COMPARISONS[op]} CAST(:{value_param} AS date)"

    # between / date_between
    bounds = value if isinstance(value, (list, tuple)) else None
    if not bounds or len(bounds) != 2:
        raise FilterError(f"operador '{op}' exige dois limites em '{layer}'")
    low, high = params.add(bounds[0]), params.add(bounds[1])
    if op == "between":
        return f"({_numeric_accessor(field_param)}) BETWEEN CAST(:{low} AS numeric) AND CAST(:{high} AS numeric)"
    return f"({_date_accessor(field_param)}) BETWEEN CAST(:{low} AS date) AND CAST(:{high} AS date)"


def _free_text_clause(text: str, params: _Params) -> str:
    """Reuses the trigram columns the search API already relies on."""
    tokens = [t for t in re.split(r"\s+", str(text).strip()) if t][:6]
    clauses = []
    for token in tokens:
        token_param = params.add(_escape_like(token))
        clauses.append(f"s.search_text LIKE '%' || lower(unaccent(:{token_param})) || '%'")
    return "(" + " AND ".join(clauses) + ")" if clauses else ""


def compile_filter(
    definition: Mapping[str, Any],
    catalog: Catalog,
    *,
    select: Literal["count", "count_by_layer", "features", "ids"] = "count",
    limit: int | None = None,
) -> CompiledFilter:
    if select not in SELECT_MODES:
        raise FilterError(f"select desconhecido: {select!r}")
    if not isinstance(definition, Mapping):
        raise FilterError("definição inválida")

    version = definition.get("version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise FilterError(f"version não suportada: {version!r}")

    blocks = definition.get("blocks")
    if not isinstance(blocks, Sequence) or not blocks:
        raise FilterError("blocks deve conter ao menos um bloco")

    params = _Params()
    text = definition.get("text")
    ctes: list[str] = []
    branches: list[str] = []
    layers: list[str] = []

    for index, raw in enumerate(blocks):
        if not isinstance(raw, Mapping):
            raise FilterError(f"bloco inválido na posição {index}")

        layer = _check_name(raw.get("layer"), "camada")
        if layer not in catalog:
            raise FilterError(f"camada '{layer}' não é filtrável")
        layers.append(layer)
        columns = catalog[layer]
        layer_param = params.add(layer)

        match = raw.get("match", "all")
        if match not in ("all", "any"):
            raise FilterError(f"match deve ser 'all' ou 'any', não {match!r}")
        joiner = " AND " if match == "all" else " OR "

        conditions = raw.get("conditions") or []
        compiled = [_compile_condition(c, layer, columns, params) for c in conditions]
        predicate = f"({joiner.join(compiled)})" if compiled else ""

        if text:
            clause = _free_text_clause(text, params)
            if clause:
                predicate = f"{predicate} AND {clause}" if predicate else clause

        where = f"s.layer_id = :{layer_param}" + (f" AND {predicate}" if predicate else "")

        positives: list[str] = []
        negatives: list[str] = []
        for s_index, spatial in enumerate(raw.get("spatial") or []):
            if not isinstance(spatial, Mapping):
                raise FilterError(f"condição espacial inválida em '{layer}'")
            relation = spatial.get("relation")
            if relation not in SPATIAL_RELATIONS:
                raise FilterError(f"relação espacial desconhecida: {relation!r}")
            target = _check_name(spatial.get("layer"), "camada espacial")
            if target not in catalog:
                raise FilterError(f"camada espacial '{target}' não é filtrável")

            target_param = params.add(target)
            t_name, m_name = f"t{index}_{s_index}", f"m{index}_{s_index}"

            # AS MATERIALIZED is load-bearing: inlined, the planner reverts to the slow plan.
            ctes.append(
                f"{t_name} AS MATERIALIZED (\n"
                f"    SELECT geometry AS g FROM {INDEX_TABLE} WHERE layer_id = :{target_param}\n"
                f"  )"
            )
            # Driven from the small target side, with an explicit && so the GIST index
            # condition stays visible to the planner.
            inner_where = where if relation == "intersects" else f"s.layer_id = :{layer_param}"
            ctes.append(
                f"{m_name} AS (\n"
                f"    SELECT DISTINCT s.id\n"
                f"    FROM {t_name}\n"
                f"    JOIN {INDEX_TABLE} s\n"
                f"      ON s.geometry && {t_name}.g AND ST_Intersects(s.geometry, {t_name}.g)\n"
                f"    WHERE {inner_where}\n"
                f"  )"
            )
            (positives if relation == "intersects" else negatives).append(m_name)

        if positives:
            base = "\n    INTERSECT\n    ".join(f"SELECT id FROM {name}" for name in positives)
        else:
            base = f"SELECT s.id FROM {INDEX_TABLE} s WHERE {where}"

        if negatives:
            anti = " AND ".join(
                f"NOT EXISTS (SELECT 1 FROM {name} WHERE {name}.id = b.id)" for name in negatives
            )
            base = f"SELECT b.id FROM (\n    {base}\n  ) AS b WHERE {anti}"

        branches.append(base)

    ctes.append("matched AS (\n    SELECT DISTINCT id FROM (\n    "
                + "\n    UNION ALL\n    ".join(branches)
                + "\n    ) AS blocks\n  )")

    with_clause = "WITH " + ",\n  ".join(ctes)

    if select == "count":
        body = "SELECT count(*) AS total FROM matched"
    elif select == "count_by_layer":
        body = (f"SELECT s.layer_id, count(*) AS total\n"
                f"FROM {INDEX_TABLE} s JOIN matched ON matched.id = s.id\n"
                f"GROUP BY s.layer_id")
    elif select == "ids":
        body = "SELECT id FROM matched"
    else:
        body = (
            "SELECT s.id, s.layer_id, s.label, s.place, s.props,\n"
            "       ST_AsKML(CASE WHEN GeometryType(s.geometry) = 'GEOMETRYCOLLECTION'\n"
            "                     THEN ST_CollectionExtract(s.geometry)\n"
            "                     ELSE s.geometry END, 7) AS geom_kml\n"
            f"FROM {INDEX_TABLE} s JOIN matched ON matched.id = s.id\n"
            "ORDER BY s.layer_id, s.id"
        )

    if limit is not None and select in ("features", "ids"):
        body += f"\nLIMIT :{params.add(int(limit))}"

    return CompiledFilter(sql=f"{with_clause}\n{body}",
                          params=params.values,
                          layers=tuple(layers))

import { Injectable } from '@angular/core';
// Aliased: the maplibre `Map` type would otherwise shadow the global Map constructor.
import type { Map as MapLibreMap } from 'maplibre-gl';
import { LAYERS, LayerConfig, renderedLayerIds } from '../layers.config';

/**
 * Separator joining composite key columns. UNIT SEPARATOR cannot occur in the source data,
 * so a joined key can never be ambiguous.
 */
const KEY_SEP = '\u001f';

/** Collects polygon/line parts of a geometry, or null for kinds that cannot be merged. */
function geometryParts(g: any): { kind: 'poly' | 'line'; parts: any[] } | null {
  if (!g) return null;
  switch (g.type) {
    case 'Polygon': return { kind: 'poly', parts: [g.coordinates] };
    case 'MultiPolygon': return { kind: 'poly', parts: g.coordinates };
    case 'LineString': return { kind: 'line', parts: [g.coordinates] };
    case 'MultiLineString': return { kind: 'line', parts: g.coordinates };
    default: return null;
  }
}

/**
 * Unions two tile fragments of the same feature into one multi-geometry.
 *
 * This is a concatenation, not a topological union: the fragments abut at a tile seam, so
 * drawing them together reproduces the whole shape. Points and mixed types fall back to the
 * first geometry.
 */
export function mergeGeometries(a: any, b: any): any {
  if (!a) return b;
  if (!b) return a;
  const pa = geometryParts(a);
  const pb = geometryParts(b);
  if (!pa || !pb || pa.kind !== pb.kind) return a;
  return {
    type: pa.kind === 'poly' ? 'MultiPolygon' : 'MultiLineString',
    coordinates: [...pa.parts, ...pb.parts]
  };
}


export interface HiddenEntry {
  key: string;
  label: string;
  /** Captured when the feature was hidden, so its outline can still be previewed on hover. */
  geometry: any;
}

/** One feature found under the cursor, as shown in the overlap stack panel. */
export interface StackEntry {
  baseLayerId: string;
  renderedLayerId: string;
  layerName: string;
  fillColor: string;
  borderColor: string;
  /** null when the layer has no usable identity; the hide control is then disabled. */
  key: string | null;
  title: string;
  canHide: boolean;
  shared: boolean;
  /**
   * Geometry for this feature. Starts as the tile fragment under the cursor (clipped at tile
   * seams) and is replaced by the full boundary from `/feature/geometry` once it arrives.
   */
  geometry: any;
  feature: any;
  lngLat: any;
  underlyingSigefProps?: any;
}

/**
 * Session-only control over which features are drawn and in what depth order.
 *
 * Nothing here is persisted: no localStorage, no backend. A reload returns the map to the
 * registry defaults, which is the agreed behaviour (docs/specs §2.2).
 */
@Injectable({ providedIn: 'root' })
export class FeatureVisibilityService {
  private map?: MapLibreMap;
  private firstLabelId?: string;

  /** layerId -> (featureKey -> label and geometry captured at hide time) */
  private readonly hidden = new Map<string, Map<string, { label: string; geometry: any }>>();

  /**
   * Non-hiding filters owned by other features, e.g. the SIGEF phase filter. Kept separate so
   * the two sources compose instead of overwriting each other.
   */
  private readonly domainFilters = new Map<string, unknown>();

  /** Layer ids ordered bottom -> top. Initialised from registry order, which is the draw order. */
  readonly drawOrder: string[] = LAYERS.map(l => l.id);

  private readonly byId = new Map<string, LayerConfig>(LAYERS.map(l => [l.id, l]));

  /** Called once the map and its highlight layers exist. */
  attach(map: MapLibreMap, firstLabelId?: string): void {
    this.map = map;
    this.firstLabelId = firstLabelId;
  }

  // ---------------------------------------------------------------- feature identity

  /**
   * Per-feature key, or null when the layer has no usable identity.
   *
   * Mirrors `keyExpression()` exactly; the two must never diverge, which is why both live here.
   */
  featureKey(layerId: string, props: Record<string, unknown> | null | undefined): string | null {
    // Deliberately does NOT fall back to `feature.id`. Martin emits no MVT feature ids
    // (verified: 3,892 features in an area_imovel_1 tile, none carrying one), and more
    // importantly `keyExpression()` has no way to express such a fallback, so using it here
    // would let the JS key and the filter expression disagree.
    const cols = this.byId.get(layerId)?.keyColumns ?? [];
    if (cols.length === 0 || !props) return null;

    const parts = cols.map(c => {
      const v = props[c];
      return v === null || v === undefined ? '' : String(v);
    });

    // Every component empty means we cannot tell this feature from any other null-keyed one.
    // Returning a key here would hide all of them at once.
    return parts.some(p => p !== '') ? parts.join(KEY_SEP) : null;
  }

  /** MapLibre expression producing the same string `featureKey()` produces. */
  keyExpression(layerId: string): unknown {
    const cols = this.byId.get(layerId)?.keyColumns ?? [];
    // `to-string` of a missing/null property yields '', matching the JS branch above.
    // `coalesce` must NOT be used here: it skips nulls and would shift the components.
    const parts = cols.map(c => ['to-string', ['get', c]]);
    if (parts.length === 1) return parts[0];

    const concat: unknown[] = ['concat'];
    parts.forEach((p, i) => {
      if (i > 0) concat.push(KEY_SEP);
      concat.push(p);
    });
    return concat;
  }

  canHide(layerId: string): boolean {
    const layer = this.byId.get(layerId);
    return !!layer && layer.keyStability !== 'none' && layer.keyColumns.length > 0;
  }

  keyStability(layerId: string) {
    return this.byId.get(layerId)?.keyStability ?? 'none';
  }

  layerName(layerId: string): string {
    return this.byId.get(layerId)?.name ?? layerId;
  }

  layerColor(layerId: string): string {
    return this.byId.get(layerId)?.fillColor ?? '#64748b';
  }

  /**
   * Orders the features found under the cursor topmost-first and removes duplicates.
   *
   * Ordering is by draw order, NOT by PRIORITY_ORDER: the panel exists to explain visual
   * occlusion, and PRIORITY_ORDER is deliberately the inverse (small point targets first), so
   * using it would put the layer doing the covering at the bottom of the list.
   *
   * Deduplication is required rather than cosmetic. Two layers appear twice in PRIORITY_ORDER
   * (`_line` and `_fill`), and queryRenderedFeatures additionally returns one entry per tile
   * for features crossing a tile seam.
   */
  dedupeAndSort(entries: StackEntry[]): StackEntry[] {
    const byId = new Map<string, StackEntry>();
    const unique: StackEntry[] = [];
    for (const e of entries) {
      // Null-keyed features cannot be compared, so they are all kept.
      if (e.key === null) {
        unique.push(e);
        continue;
      }
      const id = `${e.baseLayerId}${KEY_SEP}${e.key}`;
      const kept = byId.get(id);
      if (kept) {
        // Same-feature fragments are only combined as a stopgap: a point query rarely returns
        // more than one, so the app replaces this with the server's full boundary.
        kept.geometry = mergeGeometries(kept.geometry, e.geometry);
        continue;
      }
      byId.set(id, e);
      unique.push(e);
    }
    const depth = (id: string) => this.drawOrder.indexOf(id);
    return unique.sort((a, b) => depth(b.baseLayerId) - depth(a.baseLayerId));
  }

  // ---------------------------------------------------------------- filter composition

  /**
   * The complete filter for a layer: every active source ANDed together.
   *
   * Before this existed, `applySigefFilter` and any second filter source both called
   * `setFilter` directly on the same layer and whichever ran last silently won.
   */
  buildLayerFilter(layerId: string): unknown {
    const parts: unknown[] = [];

    const domain = this.domainFilters.get(layerId);
    if (domain) parts.push(domain);

    const keys = [...(this.hidden.get(layerId)?.keys() ?? [])];
    if (keys.length > 0) {
      parts.push(['!', ['in', this.keyExpression(layerId), ['literal', keys]]]);
    }

    if (parts.length === 0) return null;
    if (parts.length === 1) return parts[0];
    return ['all', ...parts];
  }

  private applyFilter(layerId: string): void {
    if (!this.map) return;
    const expr = this.buildLayerFilter(layerId);
    for (const rid of renderedLayerIds(this.map, layerId)) {
      this.map.setFilter(rid, expr as never);
    }
  }

  /** Registers a non-hiding filter (e.g. SIGEF phases). Pass null to clear it. */
  setDomainFilter(layerId: string, expr: unknown): void {
    if (expr === null || expr === undefined) {
      this.domainFilters.delete(layerId);
    } else {
      this.domainFilters.set(layerId, expr);
    }
    this.applyFilter(layerId);
  }

  // ---------------------------------------------------------------- hiding

  hide(layerId: string, key: string, label: string, geometry: any): void {
    let layerHidden = this.hidden.get(layerId);
    if (!layerHidden) {
      layerHidden = new Map<string, { label: string; geometry: any }>();
      this.hidden.set(layerId, layerHidden);
    }
    // The geometry is kept so the hidden row can still show the user where the feature is.
    layerHidden.set(key, { label, geometry });
    this.applyFilter(layerId);
  }

  restore(layerId: string, key: string): void {
    const layerHidden = this.hidden.get(layerId);
    if (!layerHidden) return;
    layerHidden.delete(key);
    if (layerHidden.size === 0) this.hidden.delete(layerId);
    this.applyFilter(layerId);
  }

  restoreLayer(layerId: string): void {
    if (!this.hidden.delete(layerId)) return;
    this.applyFilter(layerId);
  }

  restoreAll(): void {
    const touched = [...this.hidden.keys()];
    this.hidden.clear();
    // Rebuilds through buildLayerFilter, so any domain filter (e.g. SIGEF phases) survives.
    for (const layerId of touched) this.applyFilter(layerId);
  }

  isHidden(layerId: string, key: string): boolean {
    return this.hidden.get(layerId)?.has(key) ?? false;
  }

  hiddenFor(layerId: string): HiddenEntry[] {
    const layerHidden = this.hidden.get(layerId);
    if (!layerHidden) return [];
    return [...layerHidden].map(([key, v]) => ({ key, label: v.label, geometry: v.geometry }));
  }

  /** Layer ids that currently hide something, in draw order (bottom -> top). */
  hiddenLayerIds(): string[] {
    return this.drawOrder.filter(id => this.hidden.has(id));
  }

  get hiddenTotal(): number {
    let total = 0;
    for (const m of this.hidden.values()) total += m.size;
    return total;
  }

  // ---------------------------------------------------------------- draw order

  depthOf(layerId: string): number {
    return this.drawOrder.indexOf(layerId) + 1;
  }

  moveToBack(layerId: string): void { this.move(layerId, () => 0); }
  moveToFront(layerId: string): void { this.move(layerId, () => this.drawOrder.length - 1); }
  moveDown(layerId: string): void { this.move(layerId, i => i - 1); }
  moveUp(layerId: string): void { this.move(layerId, i => i + 1); }

  private move(layerId: string, target: (index: number) => number): void {
    const from = this.drawOrder.indexOf(layerId);
    if (from === -1) return;
    const to = Math.max(0, Math.min(this.drawOrder.length - 1, target(from)));
    if (to === from) return;
    this.drawOrder.splice(from, 1);
    this.drawOrder.splice(to, 0, layerId);
    this.applyLayerOrder();
  }

  /**
   * Reconciles the whole stack against `drawOrder`, rather than computing per-move offsets.
   *
   * `moveLayer(id, before)` inserts immediately below `before`. Walking bottom -> top against a
   * fixed top anchor lands each layer just under the anchor and therefore above everything moved
   * before it, so the final order is exactly `drawOrder`.
   *
   * The anchor is the lowest overlay layer (the hover preview), not the first label layer:
   * the `hover-feature-*` and `selected-feature-*` layers were registered with
   * `beforeId = firstLabelId` and so already sit above all data. Anchoring at the label layer
   * would push moved data layers over both of them.
   *
   * Satellite rasters were added before the data loop and stay below by construction, so the
   * invariant satellite < data < highlight < labels is re-established on every call.
   */
  applyLayerOrder(): void {
    if (!this.map) return;
    // Must be the LOWEST overlay layer, otherwise reordered data layers would land above the
    // hover preview and bury it. Overlay order is hover-* then selected-*, so hover is lowest.
    const anchor = ['hover-feature-fill', 'selected-feature-fill']
      .find(id => this.map!.getLayer(id)) ?? this.firstLabelId;
    if (!anchor) return;

    for (const layerId of this.drawOrder) {
      for (const rid of renderedLayerIds(this.map, layerId)) {
        this.map.moveLayer(rid, anchor);
      }
    }
  }
}

import { Injectable, effect, inject, signal, untracked } from '@angular/core';
import type { Map as MapLibreMap, GeoJSONSource } from 'maplibre-gl';
import { SelectionService, SelectionGeometry } from './selection.service';

export interface LayerHost {
  layers: { id: string; visible: boolean; fillColor: string; borderColor: string }[];
  setLayerVisible(id: string, visible: boolean): void;
}

const SOURCE = 'selection-members-source';
const FILL = 'selection-members-fill';
const LINE = 'selection-members-line';
const CIRCLE = 'selection-members-circle';
/** Registered below this layer so the invariant satellite < data < highlight < labels holds. */
const ANCHOR = 'hover-feature-fill';

/**
 * "Isolar": hides every data layer and draws only the active set's full boundaries.
 *
 * Entering snapshots each layer's visibility; leaving restores exactly that snapshot, so
 * toggling layers while isolated can never leave the map in a different state afterwards.
 */
@Injectable({ providedIn: 'root' })
export class SelectionIsolationService {
  private selection = inject(SelectionService);

  private map?: MapLibreMap;
  private host?: LayerHost;
  private snapshot: { id: string; visible: boolean }[] = [];
  private busy = false;

  readonly active = signal(false);
  readonly count = signal(0);
  readonly layerIds = [FILL, LINE, CIRCLE];

  constructor() {
    // Switching or deleting the active set, or editing its members, while isolated.
    effect(() => {
      this.selection.changed();
      this.selection.activeId();
      untracked(() => { if (this.active()) void this.refresh(); });
    });
  }

  /** Registers the overlay once the highlight layers exist. */
  attach(map: MapLibreMap, host: LayerHost) {
    this.map = map;
    this.host = host;

    map.addSource(SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addLayer({
      id: FILL, type: 'fill', source: SOURCE, filter: ['==', '$type', 'Polygon'],
      paint: { 'fill-color': ['get', '__fill'], 'fill-opacity': 0.45 },
    }, ANCHOR);
    map.addLayer({
      id: LINE, type: 'line', source: SOURCE,
      filter: ['any', ['==', '$type', 'Polygon'], ['==', '$type', 'LineString']],
      paint: { 'line-color': ['get', '__border'], 'line-width': 2 },
    }, ANCHOR);
    map.addLayer({
      id: CIRCLE, type: 'circle', source: SOURCE, filter: ['==', '$type', 'Point'],
      paint: {
        'circle-radius': 7, 'circle-color': ['get', '__fill'],
        'circle-stroke-color': ['get', '__border'], 'circle-stroke-width': 2,
      },
    }, ANCHOR);
  }

  flyTo(lng: number, lat: number) {
    this.map?.flyTo({ center: [lng, lat], zoom: Math.max(this.map.getZoom(), 15), essential: true });
  }

  async enter(): Promise<void> {
    if (this.busy || this.active() || !this.map || !this.host) return;
    this.busy = true;
    try {
      const collection = await this.selection.geometry(this.map.getZoom());
      if (!collection.features.length) {
        this.selection.say('Nenhuma área encontrada neste conjunto para isolar.');
        return;
      }
      // Anything that can throw on odd geometry runs before the map is touched.
      const bounds = this.boundsOf(collection);

      this.snapshot = this.host.layers.map(l => ({ id: l.id, visible: l.visible }));
      this.active.set(true);          // from here on, exit() undoes whatever happens next
      try {
        for (const layer of this.host.layers) {
          if (layer.visible) this.host.setLayerVisible(layer.id, false);
        }
        this.draw(collection);
        if (bounds) this.map.fitBounds(bounds, { padding: 80, maxZoom: 16, essential: true });
      } catch (error) {
        this.exit();
        throw error;
      }
    } catch {
      this.selection.say('Não foi possível carregar as áreas do conjunto.');
    } finally {
      this.busy = false;
    }
  }

  exit(): void {
    if (!this.active() || !this.host) return;
    for (const saved of this.snapshot) {
      const layer = this.host.layers.find(l => l.id === saved.id);
      if (layer && layer.visible !== saved.visible) this.host.setLayerVisible(saved.id, saved.visible);
    }
    this.snapshot = [];
    (this.map?.getSource(SOURCE) as GeoJSONSource | undefined)
      ?.setData({ type: 'FeatureCollection', features: [] });
    this.count.set(0);
    this.active.set(false);
  }

  /** Redraws after the set changed; leaves isolation when there is nothing left to show. */
  private async refresh(): Promise<void> {
    if (!this.selection.activeId()) { this.exit(); return; }
    try {
      const collection = await this.selection.geometry(this.map?.getZoom() ?? 12);
      if (!collection.features.length) { this.exit(); return; }
      this.draw(collection);
    } catch {
      this.exit();
    }
  }

  private draw(collection: SelectionGeometry) {
    for (const feature of collection.features) {
      const layer = this.host?.layers.find(l => l.id === feature.properties['__layer']);
      feature.properties['__fill'] = layer?.fillColor ?? '#64748b';
      feature.properties['__border'] = layer?.borderColor ?? '#475569';
    }
    (this.map?.getSource(SOURCE) as GeoJSONSource | undefined)?.setData(collection as any);
    this.count.set(collection.features.length);
  }

  /**
   * Bounds of every coordinate, or null when there are none. Tolerates GeometryCollection
   * (`geometries`, no `coordinates`; 4 `ucs_estaduais_cprh_pe` rows) and null geometries.
   */
  private boundsOf(collection: SelectionGeometry): [[number, number], [number, number]] | null {
    let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
    const coords = (c: any): void => {
      if (!Array.isArray(c) || c.length === 0) return;
      if (typeof c[0] === 'number') {
        minX = Math.min(minX, c[0]); maxX = Math.max(maxX, c[0]);
        minY = Math.min(minY, c[1]); maxY = Math.max(maxY, c[1]);
      } else {
        c.forEach(coords);
      }
    };
    const geometry = (g: any): void => {
      if (!g) return;
      if (g.type === 'GeometryCollection') (g.geometries ?? []).forEach(geometry);
      else coords(g.coordinates);
    };
    collection.features.forEach(f => geometry(f.geometry));
    return Number.isFinite(minX) ? [[minX, minY], [maxX, maxY]] : null;
  }
}

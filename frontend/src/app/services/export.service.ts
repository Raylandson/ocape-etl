import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { SEARCH_API_URL } from './search.service';

export interface LayerStyle {
  name?: string;
  fill?: string;
  border?: string;
}

/** Everything needed to re-find a clicked feature server-side and export its exact geometry. */
export interface ActiveFeatureRef {
  layerId: string;
  layerName: string;
  fillColor: string;
  borderColor: string;
  lng: number;
  lat: number;
  zoom: number;
  props: Record<string, any>;
  /** Set when the selection came from the search bar, which already knows the exact row. */
  searchIndexId?: number;
  /** Polygons resolve with zero tolerance; points and lines need a pixel box. */
  tolerancePx?: number;
}

@Injectable({ providedIn: 'root' })
export class ExportService {
  private http = inject(HttpClient);

  /** Exports the active selection: one KML for the set, or a ZIP with one KML per area. */
  exportSelection(id: string, grouping: 'set' | 'feature',
                  style: Record<string, LayerStyle>, fallbackName: string): Observable<void> {
    return this.http
      .post(`${SEARCH_API_URL}/selections/${id}/export/kml`, { grouping, style },
            { responseType: 'blob', observe: 'response' })
      .pipe(map(response => this.save(response, fallbackName)));
  }

  /**
   * Whole boundary of a clicked feature, for the map highlight. The tile only holds the
   * fragment under the cursor, so a parcel crossing tile seams highlights as a clipped sliver.
   */
  featureGeometry(ref: ActiveFeatureRef): Observable<any> {
    const body = {
      layer: ref.layerId,
      lng: ref.lng,
      lat: ref.lat,
      zoom: ref.zoom,
      tolerance_px: ref.tolerancePx ?? 6,
      props: ref.props ?? {},
      search_index_id: ref.searchIndexId ?? null,
    };
    return this.http
      .post<{ geometry: any }>(`${SEARCH_API_URL}/feature/geometry`, body)
      .pipe(map(response => response.geometry));
  }

  /** Single feature, replacing the old client-side generator so geometry is exact. */
  exportFeature(ref: ActiveFeatureRef): Observable<void> {
    const body = {
      layer: ref.layerId,
      lng: ref.lng,
      lat: ref.lat,
      zoom: ref.zoom,
      tolerance_px: ref.tolerancePx ?? 6,
      props: ref.props ?? {},
      search_index_id: ref.searchIndexId ?? null,
      style: { name: ref.layerName, fill: ref.fillColor, border: ref.borderColor },
    };
    return this.http
      .post(`${SEARCH_API_URL}/export/kml/feature`, body,
            { responseType: 'blob', observe: 'response' })
      .pipe(map(response => this.save(response, 'feicao.kml')));
  }

  /** Reads the server-provided filename; needs CORS `expose_headers` to see the header. */
  private save(response: HttpResponse<Blob>, fallback: string): void {
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const match = /filename="?([^";]+)"?/.exec(disposition);
    const filename = match ? match[1] : fallback;

    const url = URL.createObjectURL(response.body as Blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

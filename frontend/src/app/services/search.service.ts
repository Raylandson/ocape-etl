import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export const SEARCH_API_URL = 'http://localhost:7055';

export interface SearchResult {
  id: number;
  layer_id: string;
  label: string;
  code: string | null;
  place: string | null;
  match_rank: number;
  props: Record<string, any>;
  geometry: any; // GeoJSON.Geometry
  anchor: [number, number];
  bbox: [number, number, number, number];
}

@Injectable({
  providedIn: 'root'
})
export class SearchService {
  private http = inject(HttpClient);

  search(query: string, limit: number = 30): Observable<SearchResult[]> {
    const params = new HttpParams().set('q', query).set('limit', limit);
    return this.http
      .get<{ query: string; results: SearchResult[] }>(`${SEARCH_API_URL}/search`, { params })
      .pipe(map(res => res.results));
  }
}

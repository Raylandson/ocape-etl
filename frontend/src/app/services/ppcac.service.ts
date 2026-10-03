import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SEARCH_API_URL } from './search.service';

export interface PpcacStats {
  ativos: number;
  arquivados: number;
  com_geometria_exata: number;
  com_poligono?: number;
  com_poligono_sigef?: number;
  com_car?: number;
  total_processos_judiciais: number;
  total_procedimentos_mppe: number;
  total_processos_sei: number;
}

export interface PpcacArea {
  id: number;
  nome_area: string;
  municipio: string;
  municipio_ibge: number | null;
  proprietario: string | null;
  movimento_social: string | null;
  processos_judiciais: string[];
  processos_mppe: string[];
  processos_sei: string[];
  ano_referencia: number | null;
  situacao: 'ATIVO' | 'ARQUIVADO' | string;
  observacoes: string | null;
  datajud_processos: string[];
  despejo_zero_ids: string[];
  sigef_codigos?: string[];
  car_codigos?: string[];
  iterpe_nomes?: string[];
  incra_projetos?: string[];
  total_car_imoveis?: number;
  fonte_geometria?: string;
  tipo_geometria?: string;
  tem_geometria_exata: boolean;
  centroid_lat: number;
  centroid_lon: number;
  bbox: [number, number, number, number];
  geometry?: any;
}

export interface PpcacResponse {
  total: number;
  stats: PpcacStats;
  areas: PpcacArea[];
}

export interface PpcacFilterKeys {
  processos_conflitos_judiciais: string[];
  despejo_zero_pe: string[];
}

@Injectable({
  providedIn: 'root'
})
export class PpcacService {
  private http = inject(HttpClient);

  getAreas(situacao?: string, q?: string, municipio?: string): Observable<PpcacResponse> {
    let params = new HttpParams();
    if (situacao && situacao !== 'ALL') {
      params = params.set('situacao', situacao);
    }
    if (q && q.trim()) {
      params = params.set('q', q.trim());
    }
    if (municipio && municipio.trim()) {
      params = params.set('municipio', municipio.trim());
    }
    return this.http.get<PpcacResponse>(`${SEARCH_API_URL}/ppcac/areas`, { params });
  }

  getFilterKeys(): Observable<PpcacFilterKeys> {
    return this.http.get<PpcacFilterKeys>(`${SEARCH_API_URL}/ppcac/filter-keys`);
  }
}

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SEARCH_API_URL } from './search.service';

export type FieldKind = 'text' | 'number' | 'date';

export interface CatalogField {
  name: string;
  data_type: string;
  kind: FieldKind;
}

export interface CatalogLayer {
  id: string;
  fields: CatalogField[];
}

export interface FilterCondition {
  field: string;
  op: string;
  value: any;
}

export interface SpatialCondition {
  relation: 'intersects' | 'not_intersects';
  layer: string;
}

export interface FilterBlock {
  layer: string;
  match: 'all' | 'any';
  conditions: FilterCondition[];
  spatial: SpatialCondition[];
}

export interface FilterDefinition {
  version: 1;
  text?: string;
  blocks: FilterBlock[];
}

export interface SavedFilter {
  id: string;
  name: string;
  description: string | null;
  definition: FilterDefinition;
  created_at: string;
  updated_at: string;
}

export interface PreviewResult {
  total: number;
  by_layer: Record<string, number>;
  layers: string[];
}

export interface FieldValues {
  values: { value: string; count: number }[];
  truncated: boolean;
}

/** Operators offered per field kind. Mirrors what the compiler accepts. */
export const OPERATORS: Record<FieldKind, { op: string; label: string; arity: 0 | 1 | 2 }[]> = {
  text: [
    { op: 'eq', label: 'é igual a', arity: 1 },
    { op: 'neq', label: 'é diferente de', arity: 1 },
    { op: 'contains', label: 'contém', arity: 1 },
    { op: 'not_contains', label: 'não contém', arity: 1 },
    { op: 'starts_with', label: 'começa com', arity: 1 },
    { op: 'is_null', label: 'está vazio', arity: 0 },
    { op: 'is_not_null', label: 'está preenchido', arity: 0 },
  ],
  number: [
    { op: 'eq', label: 'é igual a', arity: 1 },
    { op: 'gte', label: 'maior ou igual a', arity: 1 },
    { op: 'lte', label: 'menor ou igual a', arity: 1 },
    { op: 'gt', label: 'maior que', arity: 1 },
    { op: 'lt', label: 'menor que', arity: 1 },
    { op: 'between', label: 'entre', arity: 2 },
    { op: 'is_null', label: 'está vazio', arity: 0 },
  ],
  date: [
    { op: 'date_gte', label: 'a partir de', arity: 1 },
    { op: 'date_lte', label: 'até', arity: 1 },
    { op: 'date_between', label: 'entre', arity: 2 },
    { op: 'is_null', label: 'está vazio', arity: 0 },
  ],
};

@Injectable({ providedIn: 'root' })
export class FilterService {
  private http = inject(HttpClient);

  catalog(): Observable<{ layers: CatalogLayer[] }> {
    return this.http.get<{ layers: CatalogLayer[] }>(`${SEARCH_API_URL}/filters/catalog`);
  }

  fieldValues(layer: string, field: string, limit = 200): Observable<FieldValues> {
    return this.http.get<FieldValues>(
      `${SEARCH_API_URL}/filters/catalog/${layer}/fields/${field}/values?limit=${limit}`);
  }

  preview(definition: FilterDefinition): Observable<PreviewResult> {
    return this.http.post<PreviewResult>(`${SEARCH_API_URL}/filters/preview`, { definition });
  }

  list(): Observable<SavedFilter[]> {
    return this.http.get<SavedFilter[]>(`${SEARCH_API_URL}/filters`);
  }

  create(name: string, description: string | null, definition: FilterDefinition): Observable<SavedFilter> {
    return this.http.post<SavedFilter>(`${SEARCH_API_URL}/filters`, { name, description, definition });
  }

  update(id: string, patch: Partial<Pick<SavedFilter, 'name' | 'description' | 'definition'>>): Observable<SavedFilter> {
    return this.http.put<SavedFilter>(`${SEARCH_API_URL}/filters/${id}`, patch);
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${SEARCH_API_URL}/filters/${id}`);
  }
}

import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { SEARCH_API_URL } from './search.service';
import { ActiveFeatureRef } from './export.service';

export type Resolved = 'exact' | 'approximate' | 'missing';

export interface SelectionSummary {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
  updated_at: string;
}

export interface SelectionMember {
  id: string;
  layer_id: string;
  label: string;
  note: string | null;
  anchor: { lng: number; lat: number };
  resolved: Resolved;
}

export interface SelectionGeometry {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: any; properties: Record<string, any> }[];
  missing: string[];
}

const BASE = `${SEARCH_API_URL}/selections`;

/**
 * Shared state for saved selections. Three places need the active set (the Filtros panel, the
 * Sobreposições rows and the detail popup), so it lives in a root service.
 */
@Injectable({ providedIn: 'root' })
export class SelectionService {
  private http = inject(HttpClient);

  readonly panelOpen = signal(false);
  readonly selections = signal<SelectionSummary[]>([]);
  readonly activeId = signal<string | null>(null);
  readonly members = signal<SelectionMember[]>([]);
  readonly notice = signal('');
  /** Bumped whenever the active set's members change, so the map overlay can redraw. */
  readonly changed = signal(0);

  private noticeTimer?: ReturnType<typeof setTimeout>;

  say(text: string) {
    this.notice.set(text);
    clearTimeout(this.noticeTimer);
    this.noticeTimer = setTimeout(() => this.notice.set(''), 4000);
  }

  async refresh(): Promise<void> {
    try {
      this.selections.set(await firstValueFrom(this.http.get<SelectionSummary[]>(BASE)));
    } catch {
      this.selections.set([]);
      this.say('Não foi possível carregar os conjuntos. A API de busca está no ar?');
    }
  }

  /** Makes a set active (or none) and loads its members. */
  async open(id: string | null): Promise<void> {
    this.activeId.set(id);
    await this.loadMembers();
  }

  private async loadMembers(): Promise<void> {
    const id = this.activeId();
    if (!id) {
      this.members.set([]);
    } else {
      try {
        const detail = await firstValueFrom(
          this.http.get<SelectionSummary & { members: SelectionMember[] }>(`${BASE}/${id}`));
        this.members.set(detail.members);
      } catch {
        this.members.set([]);
        this.say('Não foi possível carregar o conjunto.');
      }
    }
    this.changed.update(n => n + 1);
  }

  async create(name: string): Promise<string | null> {
    try {
      const created = await firstValueFrom(this.http.post<SelectionSummary>(BASE, { name }));
      await this.refresh();
      await this.open(created.id);
      return null;
    } catch (err: any) {
      return err?.error?.detail ?? 'Não foi possível criar o conjunto.';
    }
  }

  async rename(id: string, name: string): Promise<string | null> {
    try {
      await firstValueFrom(this.http.put(`${BASE}/${id}`, { name }));
      await this.refresh();
      return null;
    } catch (err: any) {
      return err?.status === 409 ? err.error.detail : 'Não foi possível renomear.';
    }
  }

  async remove(id: string): Promise<void> {
    await firstValueFrom(this.http.delete(`${BASE}/${id}`));
    if (this.activeId() === id) await this.open(null);
    await this.refresh();
  }

  /** Adds the feature to the active set. A feature already there is not duplicated. */
  async add(ref: ActiveFeatureRef): Promise<void> {
    const id = this.activeId();
    if (!id) {
      this.panelOpen.set(true);
      this.say('Escolha ou crie um conjunto em Filtros.');
      return;
    }
    const body = {
      layer: ref.layerId, lng: ref.lng, lat: ref.lat, zoom: ref.zoom,
      tolerance_px: ref.tolerancePx ?? 6, props: ref.props ?? {},
      search_index_id: ref.searchIndexId ?? null,
    };
    try {
      const res = await firstValueFrom(
        this.http.post<{ member: SelectionMember; created: boolean }>(`${BASE}/${id}/members`, body));
      await this.loadMembers();
      await this.refresh();
      this.panelOpen.set(true);
      this.say(res.created ? `Adicionada: ${res.member.label}` : 'Já está no conjunto.');
    } catch (err: any) {
      this.say(err?.status === 404 ? 'Feição não encontrada nesta posição.'
             : err?.status === 409 ? 'O conjunto atingiu o limite de 500 áreas.'
             : 'Não foi possível adicionar a área.');
    }
  }

  async removeMember(memberId: string): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    await firstValueFrom(this.http.delete(`${BASE}/${id}/members/${memberId}`));
    await this.loadMembers();
    await this.refresh();
  }

  async setNote(memberId: string, note: string): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    await firstValueFrom(this.http.put(`${BASE}/${id}/members/${memberId}`, { note }));
    this.members.update(list => list.map(m => m.id === memberId ? { ...m, note: note || null } : m));
  }

  geometry(zoom: number): Promise<SelectionGeometry> {
    return firstValueFrom(
      this.http.get<SelectionGeometry>(`${BASE}/${this.activeId()}/geometry?zoom=${zoom}`));
  }

  async exportBackup(): Promise<void> {
    const data = await firstValueFrom(this.http.get<unknown[]>(`${BASE}/backup`));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `conjuntos_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  async importBackup(file: File): Promise<void> {
    try {
      const parsed = JSON.parse(await file.text());
      if (!Array.isArray(parsed)) throw new Error('formato');
      const result = await firstValueFrom(
        this.http.post<{ selections: number; members_added: number; skipped: number }>(`${BASE}/backup`, parsed));
      await this.refresh();
      await this.loadMembers();
      this.say(`${result.selections} conjunto(s) novo(s), ${result.members_added} área(s) adicionada(s), ${result.skipped} ignorada(s).`);
    } catch {
      this.say('Arquivo inválido: esperado uma lista de conjuntos em JSON.');
    }
  }
}

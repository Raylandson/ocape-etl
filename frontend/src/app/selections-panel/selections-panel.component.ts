import { Component, Input, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectionService, SelectionMember } from '../services/selection.service';
import { ExportService, LayerStyle } from '../services/export.service';
import { SelectionIsolationService } from '../services/selection-isolation.service';

interface LayerMetaItem {
  id: string;
  name: string;
  fillColor: string;
  borderColor: string;
}

@Component({
  selector: 'app-selections-panel',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './selections-panel.component.html',
  styleUrl: './selections-panel.component.css',
})
export class SelectionsPanelComponent {
  readonly sel = inject(SelectionService);
  readonly isolation = inject(SelectionIsolationService);
  private exporter = inject(ExportService);

  /** The frontend layer registry: the only place layer colours and pt-BR names live. */
  @Input() layers: LayerMetaItem[] = [];

  newName = '';
  createError = '';
  renamingId: string | null = null;
  renameValue = '';
  renameError = '';
  grouping: 'set' | 'feature' = 'set';
  exporting = false;
  exportError = '';

  constructor() {
    void this.sel.refresh();
  }

  toggleOpen() { this.sel.panelOpen.update(v => !v); }

  layerName(id: string): string { return this.layers.find(l => l.id === id)?.name ?? id; }
  layerColor(id: string): string { return this.layers.find(l => l.id === id)?.fillColor ?? '#64748b'; }
  layerBorder(id: string): string { return this.layers.find(l => l.id === id)?.borderColor ?? '#475569'; }

  get activeName(): string {
    return this.sel.selections().find(s => s.id === this.sel.activeId())?.name ?? '';
  }

  /** Members that still resolve; nothing else can be drawn or exported. */
  get usable(): number {
    return this.sel.members().filter(m => m.resolved !== 'missing').length;
  }

  async create() {
    const name = this.newName.trim();
    if (!name) return;
    this.createError = (await this.sel.create(name)) ?? '';
    if (!this.createError) this.newName = '';
  }

  async pick(id: string) {
    if (this.sel.activeId() === id) return;
    await this.sel.open(id);
  }

  startRename(id: string, current: string, event: Event) {
    event.stopPropagation();
    this.renamingId = id;
    this.renameValue = current;
    this.renameError = '';
  }

  async commitRename() {
    if (!this.renamingId) return;
    const id = this.renamingId;
    const name = this.renameValue.trim();
    this.renamingId = null;                       // also guards the Enter + blur double call
    if (!name) return;
    this.renameError = (await this.sel.rename(id, name)) ?? '';
    if (this.renameError) { this.renamingId = id; }
  }

  async removeSet(id: string, event: Event) {
    event.stopPropagation();
    await this.sel.remove(id);
  }

  zoomTo(member: SelectionMember) {
    this.isolation.flyTo(member.anchor.lng, member.anchor.lat);
  }

  async saveNote(member: SelectionMember, value: string) {
    if ((member.note ?? '') === value.trim()) return;
    await this.sel.setNote(member.id, value.trim());
  }

  async toggleIsolation() {
    if (this.isolation.active()) this.isolation.exit();
    else await this.isolation.enter();
  }

  exportNow() {
    const id = this.sel.activeId();
    if (!id || !this.usable) return;
    this.exporting = true;
    this.exportError = '';
    const style: Record<string, LayerStyle> = {};
    for (const layer of this.layers) {
      style[layer.id] = { name: layer.name, fill: layer.fillColor, border: layer.borderColor };
    }
    const fallback = this.grouping === 'set' ? 'conjunto.kml' : 'conjunto.zip';
    this.exporter.exportSelection(id, this.grouping, style, fallback).subscribe({
      next: () => this.exporting = false,
      error: () => { this.exporting = false; this.exportError = 'Falha ao exportar.'; },
    });
  }

  async onImport(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) await this.sel.importBackup(file);
  }
}

import { Component, EventEmitter, Input, OnInit, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, switchMap, catchError, of } from 'rxjs';
import {
  CatalogField, CatalogLayer, FilterBlock, FilterCondition, FilterDefinition,
  FilterService, OPERATORS, PreviewResult, SavedFilter,
} from '../services/filter.service';
import { ExportService, LayerStyle } from '../services/export.service';

interface LayerMetaItem {
  id: string;
  name: string;
  fillColor: string;
  borderColor: string;
}

/** Mirrors the server-side caps in src/export_api.py. */
const CAPS: Record<'layer' | 'feature', number> = { layer: 50_000, feature: 2_000 };

@Component({
  selector: 'app-filter-builder',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './filter-builder.component.html',
  styleUrl: './filter-builder.component.css',
})
export class FilterBuilderComponent implements OnInit {
  private filters = inject(FilterService);
  private exporter = inject(ExportService);

  /** The frontend layer registry: the only place layer colours and pt-BR names live. */
  @Input() layers: LayerMetaItem[] = [];
  @Output() previewRequested = new EventEmitter<FilterDefinition>();

  isOpen = false;
  catalog: CatalogLayer[] = [];
  catalogError = '';

  blocks: FilterBlock[] = [];
  freeText = '';

  preview: PreviewResult | null = null;
  previewing = false;
  previewError = '';

  saved: SavedFilter[] = [];
  saveName = '';
  saveError = '';
  busy = false;

  grouping: 'layer' | 'feature' = 'layer';
  exporting = false;
  exportError = '';

  /** Distinct values per `layer.field`, used to offer a datalist instead of free typing. */
  valueOptions: Record<string, string[]> = {};

  private previewTrigger = new Subject<FilterDefinition>();

  ngOnInit(): void {
    this.filters.catalog().subscribe({
      next: res => this.catalog = res.layers,
      error: () => this.catalogError = 'Não foi possível carregar os campos. A API de busca está no ar?',
    });
    this.reloadSaved();

    // Editing a condition re-counts without hammering a query that can take ~1 s.
    this.previewTrigger.pipe(
      debounceTime(400),
      distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
      switchMap(definition => {
        this.previewing = true;
        this.previewError = '';
        return this.filters.preview(definition).pipe(catchError(err => {
          this.previewError = err?.error?.detail ?? 'Falha ao pré-visualizar.';
          return of(null);
        }));
      }),
    ).subscribe(result => {
      this.previewing = false;
      this.preview = result;
    });
  }

  // ------------------------------------------------------------------ panel

  toggleOpen() { this.isOpen = !this.isOpen; }

  get hasBlocks(): boolean { return this.blocks.length > 0; }

  layerName(id: string): string {
    return this.layers.find(l => l.id === id)?.name ?? id;
  }

  layerColor(id: string): string {
    return this.layers.find(l => l.id === id)?.fillColor ?? '#64748b';
  }

  /** Only layers present in the search index can be filtered. */
  get filterableLayers(): LayerMetaItem[] {
    const ids = new Set(this.catalog.map(c => c.id));
    const known = this.layers.filter(l => ids.has(l.id));
    const extra = this.catalog
      .filter(c => !this.layers.some(l => l.id === c.id))
      .map(c => ({ id: c.id, name: c.id, fillColor: '#64748b', borderColor: '#475569' }));
    return [...known, ...extra];
  }

  // ------------------------------------------------------------------ building

  addBlock() {
    const first = this.filterableLayers[0];
    if (!first) return;
    this.blocks.push({ layer: first.id, match: 'all', conditions: [], spatial: [] });
    this.schedulePreview();
  }

  removeBlock(index: number) {
    this.blocks.splice(index, 1);
    this.schedulePreview();
  }

  onBlockLayerChange(block: FilterBlock) {
    // Fields belong to a layer, so changing it invalidates every condition.
    block.conditions = [];
    this.schedulePreview();
  }

  fieldsFor(layerId: string): CatalogField[] {
    return this.catalog.find(c => c.id === layerId)?.fields ?? [];
  }

  addCondition(block: FilterBlock) {
    const field = this.fieldsFor(block.layer)[0];
    if (!field) return;
    const op = OPERATORS[field.kind][0].op;
    block.conditions.push({ field: field.name, op, value: '' });
    this.loadValues(block.layer, field.name);
    this.schedulePreview();
  }

  removeCondition(block: FilterBlock, index: number) {
    block.conditions.splice(index, 1);
    this.schedulePreview();
  }

  kindOf(block: FilterBlock, condition: FilterCondition): 'text' | 'number' | 'date' {
    return this.fieldsFor(block.layer).find(f => f.name === condition.field)?.kind ?? 'text';
  }

  operatorsFor(block: FilterBlock, condition: FilterCondition) {
    return OPERATORS[this.kindOf(block, condition)];
  }

  arityOf(block: FilterBlock, condition: FilterCondition): number {
    const op = this.operatorsFor(block, condition).find(o => o.op === condition.op);
    return op?.arity ?? 1;
  }

  onFieldChange(block: FilterBlock, condition: FilterCondition) {
    const operators = this.operatorsFor(block, condition);
    condition.op = operators[0].op;
    condition.value = '';
    this.loadValues(block.layer, condition.field);
    this.schedulePreview();
  }

  optionsKey(layer: string, field: string) { return `${layer}.${field}`; }

  optionsFor(block: FilterBlock, condition: FilterCondition): string[] {
    return this.valueOptions[this.optionsKey(block.layer, condition.field)] ?? [];
  }

  private loadValues(layer: string, field: string) {
    const key = this.optionsKey(layer, field);
    if (this.valueOptions[key]) return;
    this.filters.fieldValues(layer, field, 60).subscribe({
      // A truncated list would be misleading as a dropdown, so fall back to free text.
      next: res => this.valueOptions[key] = res.truncated ? [] : res.values.map(v => v.value),
      error: () => this.valueOptions[key] = [],
    });
  }

  // ------------------------------------------------------------------ spatial

  addSpatial(block: FilterBlock) {
    const target = this.filterableLayers.find(l => l.id !== block.layer);
    if (!target) return;
    block.spatial.push({ relation: 'intersects', layer: target.id });
    this.schedulePreview();
  }

  removeSpatial(block: FilterBlock, index: number) {
    block.spatial.splice(index, 1);
    this.schedulePreview();
  }

  // ------------------------------------------------------------------ preview

  buildDefinition(): FilterDefinition {
    const definition: FilterDefinition = {
      version: 1,
      blocks: this.blocks.map(b => ({
        layer: b.layer,
        match: b.match,
        conditions: b.conditions
          .filter(c => this.arityOf(b, c) === 0 || c.value !== '' && c.value != null)
          .map(c => ({ ...c, value: this.coerce(b, c) })),
        spatial: [...b.spatial],
      })),
    };
    if (this.freeText.trim()) definition.text = this.freeText.trim();
    return definition;
  }

  private coerce(block: FilterBlock, condition: FilterCondition): any {
    if (this.kindOf(block, condition) !== 'number') return condition.value;
    if (Array.isArray(condition.value)) return condition.value.map(Number);
    return Number(condition.value);
  }

  schedulePreview() {
    if (!this.hasBlocks) { this.preview = null; return; }
    const definition = this.buildDefinition();
    this.previewRequested.emit(definition);
    this.previewTrigger.next(definition);
  }

  capFor(grouping: 'layer' | 'feature') { return CAPS[grouping]; }

  overCap(grouping: 'layer' | 'feature'): boolean {
    return !!this.preview && this.preview.total > CAPS[grouping];
  }

  get byLayerEntries(): { layer: string; total: number }[] {
    if (!this.preview) return [];
    return Object.entries(this.preview.by_layer).map(([layer, total]) => ({ layer, total }));
  }

  // ------------------------------------------------------------------ persistence

  reloadSaved() {
    this.filters.list().subscribe({ next: list => this.saved = list, error: () => this.saved = [] });
  }

  save() {
    const name = this.saveName.trim();
    if (!name || !this.hasBlocks) return;
    this.busy = true;
    this.saveError = '';
    this.filters.create(name, null, this.buildDefinition()).subscribe({
      next: () => { this.busy = false; this.saveName = ''; this.reloadSaved(); },
      error: err => {
        this.busy = false;
        this.saveError = err?.status === 409
          ? 'Já existe um filtro com este nome.'
          : (err?.error?.detail ?? 'Não foi possível salvar.');
      },
    });
  }

  load(filter: SavedFilter) {
    const definition = filter.definition;
    this.blocks = (definition.blocks ?? []).map(b => ({
      layer: b.layer,
      match: b.match ?? 'all',
      conditions: (b.conditions ?? []).map(c => ({ ...c })),
      spatial: (b.spatial ?? []).map(s => ({ ...s })),
    }));
    this.freeText = definition.text ?? '';
    this.saveName = filter.name;
    for (const block of this.blocks) {
      for (const condition of block.conditions) this.loadValues(block.layer, condition.field);
    }
    this.schedulePreview();
  }

  remove(filter: SavedFilter, event: Event) {
    event.stopPropagation();
    this.filters.remove(filter.id).subscribe({ next: () => this.reloadSaved() });
  }

  // ------------------------------------------------------------------ export

  exportNow() {
    if (!this.hasBlocks || this.overCap(this.grouping)) return;
    this.exporting = true;
    this.exportError = '';

    const style: Record<string, LayerStyle> = {};
    for (const layer of this.layers) {
      style[layer.id] = { name: layer.name, fill: layer.fillColor, border: layer.borderColor };
    }
    const filename = (this.saveName.trim() || 'filtro').toLowerCase().replace(/\s+/g, '-');

    this.exporter.exportFilter(this.buildDefinition(), this.grouping, style, filename).subscribe({
      next: () => this.exporting = false,
      error: err => {
        this.exporting = false;
        this.exportError = err?.status === 413
          ? 'O resultado excede o limite deste agrupamento.'
          : 'Falha ao exportar.';
      },
    });
  }
}

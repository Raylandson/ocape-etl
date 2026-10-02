import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { FeatureVisibilityService, StackEntry } from '../services/feature-visibility.service';

/**
 * Lists every feature under the last click and everything currently hidden.
 *
 * Deliberately a panel rather than an extension of the map popup: hiding the feature whose
 * popup is open has to close that popup, which is exactly when the user wants to reach the
 * next feature down. A list living inside the popup would die at that moment.
 */
@Component({
  selector: 'app-overlap-stack-panel',
  standalone: true,
  imports: [],
  templateUrl: './overlap-stack-panel.component.html',
  styleUrl: './overlap-stack-panel.component.css'
})
export class OverlapStackPanelComponent {
  private visibility = inject(FeatureVisibilityService);

  @Input() stack: StackEntry[] = [];
  @Input() activeEntry: StackEntry | null = null;

  @Output() featureSelected = new EventEmitter<StackEntry>();
  @Output() featureHidden = new EventEmitter<StackEntry>();
  @Output() featureAddRequested = new EventEmitter<StackEntry>();
  @Output() featureRestored = new EventEmitter<StackEntry>();
  @Output() stackCleared = new EventEmitter<void>();
  /** GeoJSON geometry of the row under the pointer, or null when the pointer leaves. */
  @Output() featureHovered = new EventEmitter<any | null>();

  isOpen = true;
  showHidden = true;

  get isVisible(): boolean {
    return this.stack.length > 0 || this.hiddenTotal > 0;
  }

  get hiddenTotal(): number {
    return this.visibility.hiddenTotal;
  }

  hiddenLayerIds(): string[] {
    return this.visibility.hiddenLayerIds();
  }

  hiddenFor(layerId: string) {
    return this.visibility.hiddenFor(layerId);
  }

  layerName(layerId: string): string {
    return this.visibility.layerName(layerId);
  }

  layerColor(layerId: string): string {
    return this.visibility.layerColor(layerId);
  }

  toggleOpen() {
    this.isOpen = !this.isOpen;
    // A collapsed panel must not leave an orphaned outline on the map.
    if (!this.isOpen) this.featureHovered.emit(null);
  }

  onHoverEnter(geometry: any | null) {
    this.featureHovered.emit(geometry ?? null);
  }

  onHoverLeave() {
    this.featureHovered.emit(null);
  }

  toggleHidden(event: Event) {
    event.stopPropagation();
    this.showHidden = !this.showHidden;
  }

  onAdd(entry: StackEntry, event: Event) {
    event.stopPropagation();
    this.featureAddRequested.emit(entry);
  }

  onSelect(entry: StackEntry, event: Event) {
    event.stopPropagation();
    this.featureSelected.emit(entry);
  }

  /** True when this row's feature is currently filtered off the map. */
  isEntryHidden(entry: StackEntry): boolean {
    return entry.key !== null && this.visibility.isHidden(entry.baseLayerId, entry.key);
  }

  /** One control toggles both ways, so a row never disappears out from under the pointer. */
  onToggleHide(entry: StackEntry, event: Event) {
    event.stopPropagation();
    if (!entry.canHide) return;
    if (this.isEntryHidden(entry)) {
      this.featureRestored.emit(entry);
    } else {
      this.featureHidden.emit(entry);
    }
    this.featureHovered.emit(null);
  }

  onClearStack(event: Event) {
    event.stopPropagation();
    this.stackCleared.emit();
  }

  restore(layerId: string, key: string, event: Event) {
    event.stopPropagation();
    this.visibility.restore(layerId, key);
    this.featureHovered.emit(null);
  }

  restoreLayer(layerId: string, event: Event) {
    event.stopPropagation();
    this.visibility.restoreLayer(layerId);
    this.featureHovered.emit(null);
  }

  restoreAll(event: Event) {
    event.stopPropagation();
    this.visibility.restoreAll();
    this.featureHovered.emit(null);
  }

  hideTooltip(entry: StackEntry): string {
    if (!entry.canHide) {
      return 'Esta camada não possui identificador por feição; use a ordenação de camadas';
    }
    if (this.isEntryHidden(entry)) {
      return 'Restaurar esta feição';
    }
    if (entry.shared) {
      return 'Ocultar — feições que compartilham este código são ocultadas em conjunto';
    }
    return 'Ocultar esta feição';
  }
}

import { Component, Input, Output, EventEmitter } from '@angular/core';

export interface SigefPhaseItem {
  id: string;
  version: string;
  date: string;
  color: string;
  borderColor: string;
  checked: boolean;
}

@Component({
  selector: 'app-sigef-batateiras-filter',
  standalone: true,
  imports: [],
  templateUrl: './sigef-batateiras-filter.component.html',
  styleUrl: './sigef-batateiras-filter.component.css'
})
export class SigefBatateirasFilterComponent {
  @Input() isVisible: boolean = false;
  @Output() filterChanged = new EventEmitter<string[]>();

  isOpen: boolean = true;

  phases: SigefPhaseItem[] = [
    {
      id: 'AV-17-73',
      version: 'AV-17-73',
      date: '08/07/2020',
      color: '#3b82f6',
      borderColor: '#1d4ed8',
      checked: true
    },
    {
      id: 'AV-19-73',
      version: 'AV-19-73',
      date: '08/09/2020',
      color: '#f59e0b',
      borderColor: '#b45309',
      checked: true
    },
    {
      id: 'AV-23-73',
      version: 'AV-23-73',
      date: '04/02/2021',
      color: '#ef4444',
      borderColor: '#b91c1c',
      checked: true
    },
    {
      id: 'SIGEF Atual',
      version: 'SIGEF Atual',
      date: '14/06/2021',
      color: '#8b5cf6',
      borderColor: '#6d28d9',
      checked: true
    }
  ];

  toggleOpen() {
    this.isOpen = !this.isOpen;
  }

  togglePhase(phase: SigefPhaseItem, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    phase.checked = !phase.checked;
    this.emitFilter();
  }

  onCheckboxChange(phase: SigefPhaseItem, event: Event) {
    event.stopPropagation();
    const input = event.target as HTMLInputElement;
    phase.checked = input.checked;
    this.emitFilter();
  }

  selectAll(event?: Event) {
    if (event) event.stopPropagation();
    this.phases.forEach(p => p.checked = true);
    this.emitFilter();
  }

  deselectAll(event?: Event) {
    if (event) event.stopPropagation();
    this.phases.forEach(p => p.checked = false);
    this.emitFilter();
  }

  getSelectedCount(): number {
    return this.phases.filter(p => p.checked).length;
  }

  private emitFilter() {
    const selectedIds = this.phases.filter(p => p.checked).map(p => p.id);
    this.filterChanged.emit(selectedIds);
  }
}

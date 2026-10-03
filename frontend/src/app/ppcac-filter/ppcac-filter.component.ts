import { Component, EventEmitter, Input, OnInit, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PpcacService, PpcacArea, PpcacStats } from '../services/ppcac.service';

@Component({
  selector: 'app-ppcac-filter',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ppcac-filter.component.html',
  styleUrl: './ppcac-filter.component.css'
})
export class PpcacFilterComponent implements OnInit {
  private ppcacService = inject(PpcacService);

  @Input() isVisible: boolean = true;
  @Output() areaSelected = new EventEmitter<PpcacArea>();
  @Output() isolationToggled = new EventEmitter<boolean>();

  isOpen: boolean = false;
  isLoading: boolean = false;
  isIsolating: boolean = false;

  areas: PpcacArea[] = [];
  filteredAreas: PpcacArea[] = [];
  stats: PpcacStats | null = null;

  selectedStatus: 'ALL' | 'ATIVO' | 'ARQUIVADO' = 'ALL';
  searchQuery: string = '';
  selectedAreaId: number | null = null;

  ngOnInit() {
    this.loadAreas();
  }

  toggleOpen() {
    this.isOpen = !this.isOpen;
    if (this.isOpen && this.areas.length === 0) {
      this.loadAreas();
    }
  }

  loadAreas() {
    this.isLoading = true;
    this.ppcacService.getAreas().subscribe({
      next: res => {
        this.areas = res.areas;
        this.stats = res.stats;
        this.applyFilter();
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  setStatus(status: 'ALL' | 'ATIVO' | 'ARQUIVADO') {
    this.selectedStatus = status;
    this.applyFilter();
  }

  onSearchChange() {
    this.applyFilter();
  }

  applyFilter() {
    const q = this.searchQuery.trim().toLowerCase();
    this.filteredAreas = this.areas.filter(a => {
      const matchStatus =
        this.selectedStatus === 'ALL' || a.situacao.toUpperCase() === this.selectedStatus;
      if (!matchStatus) return false;

      if (!q) return true;
      const inName = a.nome_area.toLowerCase().includes(q);
      const inMun = a.municipio.toLowerCase().includes(q);
      const inOwner = (a.proprietario || '').toLowerCase().includes(q);
      const inMov = (a.movimento_social || '').toLowerCase().includes(q);
      return inName || inMun || inOwner || inMov;
    });
  }

  toggleIsolation() {
    this.isIsolating = !this.isIsolating;
    this.isolationToggled.emit(this.isIsolating);
  }

  selectArea(area: PpcacArea) {
    this.selectedAreaId = area.id;
    this.areaSelected.emit(area);
  }

  clearSelection(event?: Event) {
    if (event) event.stopPropagation();
    this.selectedAreaId = null;
  }
}

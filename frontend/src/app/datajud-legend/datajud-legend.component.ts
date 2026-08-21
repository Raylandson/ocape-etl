import { Component, Input } from '@angular/core';

export interface DatajudCategory {
  id: string;
  name: string;
  color: string;
  borderColor: string;
}

@Component({
  selector: 'app-datajud-legend',
  standalone: true,
  imports: [],
  templateUrl: './datajud-legend.component.html',
  styleUrl: './datajud-legend.component.css'
})
export class DatajudLegendComponent {
  @Input() isVisible: boolean = false;

  isOpen: boolean = true;

  categories: DatajudCategory[] = [
    {
      id: 'reintegracao',
      name: 'Reintegração e Conflito de Posse',
      color: '#8b5cf6',
      borderColor: '#6d28d9'
    },
    {
      id: 'reforma_agraria',
      name: 'Reforma Agrária & Desapropriação',
      color: '#f59e0b',
      borderColor: '#d97706'
    },
    {
      id: 'indigenas_quilombolas',
      name: 'Povos Indígenas & Quilombolas',
      color: '#ef4444',
      borderColor: '#dc2626'
    },
    {
      id: 'terras_devolutas',
      name: 'Terras Devolutas & Discriminatórias',
      color: '#3b82f6',
      borderColor: '#2563eb'
    },
    {
      id: 'usucapiao',
      name: 'Usucapião e Regularização de Posse',
      color: '#10b981',
      borderColor: '#059669'
    },
    {
      id: 'conflito_coletivo',
      name: 'Conflito Coletivo Rural & Agrário',
      color: '#ec4899',
      borderColor: '#db2777'
    }
  ];

  toggleOpen() {
    this.isOpen = !this.isOpen;
  }
}

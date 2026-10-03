import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PpcacFilterComponent } from './ppcac-filter.component';
import { PpcacService, PpcacResponse, PpcacArea } from '../services/ppcac.service';
import { of } from 'rxjs';

describe('PpcacFilterComponent', () => {
  let component: PpcacFilterComponent;
  let fixture: ComponentFixture<PpcacFilterComponent>;
  let mockPpcacService: jasmine.SpyObj<PpcacService>;

  const sampleArea: PpcacArea = {
    id: 1,
    nome_area: 'Engenho Barro Branco',
    municipio: 'Jaqueira',
    municipio_ibge: 2607901,
    proprietario: 'Sociedade Negócios Imobiliários',
    movimento_social: 'CPT',
    processos_judiciais: ['0000082-63.2018.8.17.2940'],
    processos_mppe: ['02054.000.004/2020'],
    processos_sei: ['0031200020.002238/2020-05'],
    ano_referencia: 2026,
    situacao: 'ATIVO',
    observacoes: null,
    datajud_processos: ['0000082-63.2018.8.17.2940'],
    despejo_zero_ids: [],
    tem_geometria_exata: true,
    centroid_lat: -8.723,
    centroid_lon: -35.801,
    bbox: [-35.82, -8.74, -35.78, -8.70]
  };

  const sampleArchivedArea: PpcacArea = {
    id: 2,
    nome_area: 'Engenho Mulatinha',
    municipio: 'Catende',
    municipio_ibge: 2604205,
    proprietario: null,
    movimento_social: null,
    processos_judiciais: [],
    processos_mppe: ['02054.000.010/2021'],
    processos_sei: ['0031200020.001000/2021-00'],
    ano_referencia: null,
    situacao: 'ARQUIVADO',
    observacoes: null,
    datajud_processos: [],
    despejo_zero_ids: [],
    tem_geometria_exata: false,
    centroid_lat: -8.667,
    centroid_lon: -35.717,
    bbox: [-35.75, -8.70, -35.68, -8.63]
  };

  const mockResponse: PpcacResponse = {
    total: 2,
    stats: {
      ativos: 1,
      arquivados: 1,
      com_geometria_exata: 1,
      total_processos_judiciais: 1,
      total_procedimentos_mppe: 2,
      total_processos_sei: 2
    },
    areas: [sampleArea, sampleArchivedArea]
  };

  beforeEach(async () => {
    mockPpcacService = jasmine.createSpyObj('PpcacService', ['getAreas', 'getFilterKeys']);
    mockPpcacService.getAreas.and.returnValue(of(mockResponse));

    await TestBed.configureTestingModule({
      imports: [PpcacFilterComponent],
      providers: [
        { provide: PpcacService, useValue: mockPpcacService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PpcacFilterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and load areas on init', () => {
    expect(component).toBeTruthy();
    expect(component.areas.length).toBe(2);
    expect(component.filteredAreas.length).toBe(2);
    expect(component.stats?.ativos).toBe(1);
  });

  it('should filter by status', () => {
    component.setStatus('ATIVO');
    expect(component.filteredAreas.length).toBe(1);
    expect(component.filteredAreas[0].nome_area).toBe('Engenho Barro Branco');

    component.setStatus('ARQUIVADO');
    expect(component.filteredAreas.length).toBe(1);
    expect(component.filteredAreas[0].nome_area).toBe('Engenho Mulatinha');

    component.setStatus('ALL');
    expect(component.filteredAreas.length).toBe(2);
  });

  it('should filter by search query', () => {
    component.searchQuery = 'Catende';
    component.onSearchChange();
    expect(component.filteredAreas.length).toBe(1);
    expect(component.filteredAreas[0].nome_area).toBe('Engenho Mulatinha');
  });

  it('should emit areaSelected when area is clicked', () => {
    spyOn(component.areaSelected, 'emit');
    component.selectArea(sampleArea);
    expect(component.selectedAreaId).toBe(sampleArea.id);
    expect(component.areaSelected.emit).toHaveBeenCalledWith(sampleArea);
  });

  it('should toggle isolation and emit event', () => {
    spyOn(component.isolationToggled, 'emit');
    component.toggleIsolation();
    expect(component.isIsolating).toBeTrue();
    expect(component.isolationToggled.emit).toHaveBeenCalledWith(true);

    component.toggleIsolation();
    expect(component.isIsolating).toBeFalse();
    expect(component.isolationToggled.emit).toHaveBeenCalledWith(false);
  });
});

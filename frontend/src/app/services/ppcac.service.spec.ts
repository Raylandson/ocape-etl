import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PpcacService, PpcacResponse, PpcacFilterKeys } from './ppcac.service';
import { SEARCH_API_URL } from './search.service';

describe('PpcacService', () => {
  let service: PpcacService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        PpcacService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ]
    });
    service = TestBed.inject(PpcacService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch areas with parameters', () => {
    const mockResponse: PpcacResponse = {
      total: 1,
      stats: {
        ativos: 1,
        arquivados: 0,
        com_geometria_exata: 1,
        total_processos_judiciais: 2,
        total_procedimentos_mppe: 1,
        total_processos_sei: 1
      },
      areas: [
        {
          id: 1,
          nome_area: 'Engenho Barro Branco',
          municipio: 'Jaqueira',
          municipio_ibge: 2607901,
          proprietario: 'Sociedade Imobiliária',
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
        }
      ]
    };

    service.getAreas('ATIVO', 'barro', 'Jaqueira').subscribe(res => {
      expect(res.total).toBe(1);
      expect(res.areas[0].nome_area).toBe('Engenho Barro Branco');
    });

    const req = httpMock.expectOne(req =>
      req.url === `${SEARCH_API_URL}/ppcac/areas` &&
      req.params.get('situacao') === 'ATIVO' &&
      req.params.get('q') === 'barro' &&
      req.params.get('municipio') === 'Jaqueira'
    );
    expect(req.request.method).toBe('GET');
    req.flush(mockResponse);
  });

  it('should fetch filter keys', () => {
    const mockKeys: PpcacFilterKeys = {
      processos_conflitos_judiciais: ['0000082-63.2018.8.17.2940'],
      despejo_zero_pe: ['DZ-PE-10']
    };

    service.getFilterKeys().subscribe(keys => {
      expect(keys.processos_conflitos_judiciais.length).toBe(1);
      expect(keys.despejo_zero_pe.length).toBe(1);
    });

    const req = httpMock.expectOne(`${SEARCH_API_URL}/ppcac/filter-keys`);
    expect(req.request.method).toBe('GET');
    req.flush(mockKeys);
  });
});

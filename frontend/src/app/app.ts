import { Component, AfterViewInit, inject, ViewEncapsulation } from '@angular/core';
import { Map, Popup, AttributionControl } from 'maplibre-gl';
import { DatajudLegendComponent } from './datajud-legend/datajud-legend.component';
import { SigefBatateirasFilterComponent } from './sigef-batateiras-filter/sigef-batateiras-filter.component';
import { KmlExportService, KmlExportItem } from './services/kml-export.service';

interface LayerConfig {
  id: string;
  name: string;
  sourceUrl: string;
  sourceLayer: string;
  fillColor: string;
  borderColor: string;
  visible: boolean;
}

export interface EnrichedCarInfo {
  nome_imovel: string;
  declarante: string;
  cpf_declarante: string;
  codigo_protocolo: string;
  origem_documento: string;
  sobreposicao_sigef: string;
  matricula_cartorio: string;
  conflito_judicial: string;
}

export const ENRICHED_CAR_DATA: Record<string, EnrichedCarInfo> = {
  'PE-2609204-F2B44463BC594543B17A9ABA928157F9': {
    nome_imovel: 'Sítio Batateira',
    declarante: 'Odílio Severino Nogueira',
    cpf_declarante: '047.523.274-73',
    codigo_protocolo: 'PE-2609204-E56F.4FDF.BD22.C8FF.50AC.984A.F223.1F4A',
    origem_documento: 'CAR - Odílio.pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  },
  'PE-2609204-AFDF317B8B3B4F00B25E9F067BE40CD2': {
    nome_imovel: 'Sítio Batateiras',
    declarante: 'Edvania Maria Cordeiro da Silva / José Carlos Cordeiro da Silva',
    cpf_declarante: '085.208.194-43 / 030.019.314-93',
    codigo_protocolo: 'PE-2609204-0CBA.7C0E.01A1.623F.F4EE.986B.4E88.5FCF',
    origem_documento: 'CAR - Sítio Batateiras (Março de 2018).pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  },
  'PE-2609204-691BBA8767C14AAFB43E205CEDBA4E43': {
    nome_imovel: 'Sítio Batateiras',
    declarante: 'Cícera Maria da Conceição / Francisco Zeferino',
    cpf_declarante: '632.869.554-34 / 047.523.274-73',
    codigo_protocolo: 'PE-2609204-F06D.AB18.5132.FDB0.FA18.FCEF.D567.5B4C',
    origem_documento: 'CAR Francisco Zeferino.pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  },
  'PE-2609204-C26EA32D98EC43E3A35991D594FF27C2': {
    nome_imovel: 'Sítio Saputi',
    declarante: 'Joselito Nogueira',
    cpf_declarante: '973.717.694-49 / 081.109.184-84',
    codigo_protocolo: 'PE-2609204-5C1D.7F1D.DFE8.A68C.25C6.9046.2E60.C5C8',
    origem_documento: 'CAR Joselito.pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  },
  'PE-2609204-791D8AA9F2B14CD5A5BC5F051A4AEA63': {
    nome_imovel: 'Sítio Flora Clara',
    declarante: 'José Manoel da Silva',
    cpf_declarante: '924.954.274-72 / 127.826.724-79',
    codigo_protocolo: 'PE-2609204-E4CB.7754.8184.A0AF.393C.CD0D.A7D0.C5E1',
    origem_documento: 'CAR José Manoel.pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  },
  'PE-2609204-F07F205EA4CE4657A77D0BDD2BE9B890': {
    nome_imovel: 'Sítio Batateirinha',
    declarante: 'Luiz Cândido da Silva / Kleiton',
    cpf_declarante: '409.063.024-04',
    codigo_protocolo: 'PE-2609204-1289.FD8B.6C3C.7719.9A0C.CB30.976B.E223',
    origem_documento: 'CAR Kleiton.pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  },
  'PE-2609204-7B3D2CC5D90C406B968CB72C195793A8': {
    nome_imovel: 'Sítio Riachão',
    declarante: 'José Joaquim Antonio Wanderley / Severino Wanderley',
    cpf_declarante: '328.331.214-15 / 033.832.594-80',
    codigo_protocolo: 'PE-2609204-74EF.EFA8.0C3A.D8AD.620B.79F6.3A0D.4B3C',
    origem_documento: 'CAR Severino Wanderley.pdf',
    sobreposicao_sigef: 'FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73',
    matricula_cartorio: 'Matrícula 73 (Livro 02, RGI Maraial) - 960,90 ha',
    conflito_judicial: 'TJPE Maraial 0000263-83.2026.8.17.2940 (Esbulho Possessório)'
  }
};

@Component({
  selector: 'app-root',
  imports: [DatajudLegendComponent, SigefBatateirasFilterComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
  encapsulation: ViewEncapsulation.None
})
export class App implements AfterViewInit {
  private kmlExportService = inject(KmlExportService);

  map!: Map;
  isPanelOpen: boolean = true;
  selectedSigefPhases: string[] = ['AV-17-73', 'AV-19-73', 'AV-23-73', 'SIGEF Atual'];
  currentBasemap: 'vector' | 'satellite' = 'vector';

  // Active clicked feature state
  activeSelectedFeatureItem: KmlExportItem | null = null;

  readonly priorityOrder: string[] = [
    'land_overlaps_points_symbol',
    'processos_conflitos_judiciais_circle',
    'moradia_legal_processos_pe_circle',
    'autos_infracao_icmbio_circle',
    'car_casos_analisados_fill',
    'sigef_casos_analisados_fill',
    'moradia_legal_pe_fill',
    'iterpe_glebas_pe_fill',
    'iterpe_malha_posses_pe_fill',
    'land_overlaps_fill',
    'alerts_with_intersections_fill',
    'car_with_alerts_and_intersections_fill',
    'assentamentos_incra_pe_fill',
    'ucs_estaduais_cprh_pe_fill',
    'processos_minerarios_pe_fill',
    'ibge_favelas_comunidades_pe_fill',
    'tis_poligonais_fill',
    'areas_de_quilombolas_pe_fill',
    'embargos_icmbio_fill',
    'limiteucsfederais_a_fill',
    'sigef_privado_pe_fill',
    'sigef_publico_pe_fill',
    'imovel_certificado_snci_privado_pe_fill',
    'imovel_certificado_snci_publico_pe_fill',
    'area_imovel_1_fill'
  ];

  togglePanel() {
    this.isPanelOpen = !this.isPanelOpen;
  }

  setBasemap(mode: 'vector' | 'satellite') {
    if (this.currentBasemap === mode) return;
    this.currentBasemap = mode;

    if (!this.map) return;

    const visibility = mode === 'satellite' ? 'visible' : 'none';
    if (this.map.getLayer('satellite-layer')) {
      this.map.setLayoutProperty('satellite-layer', 'visibility', visibility);
    }
    if (this.map.getLayer('satellite-boundary-state')) {
      this.map.setLayoutProperty('satellite-boundary-state', 'visibility', visibility);
    }
    if (this.map.getLayer('satellite-boundary-county')) {
      this.map.setLayoutProperty('satellite-boundary-county', 'visibility', visibility);
    }
  }

  getActiveLayersCount(): number {
    return this.layers.filter(l => l.visible).length;
  }

  isDataJudVisible(): boolean {
    return this.layers.find(l => l.id === 'processos_conflitos_judiciais')?.visible ?? false;
  }

  isSigefCasosAnalisadosVisible(): boolean {
    return this.layers.find(l => l.id === 'sigef_casos_analisados')?.visible ?? false;
  }

  onSigefFilterChanged(selectedFases: string[]) {
    this.selectedSigefPhases = selectedFases;
    this.applySigefFilter();
  }

  applySigefFilter() {
    if (!this.map) return;

    let filterExpr: any;
    if (this.selectedSigefPhases.length === 0) {
      filterExpr = ['==', ['get', 'fase'], '__none__'];
    } else if (this.selectedSigefPhases.length === 4) {
      filterExpr = null;
    } else {
      filterExpr = ['any', ...this.selectedSigefPhases.map(f => ['==', ['get', 'fase'], f])];
    }

    if (this.map.getLayer('sigef_casos_analisados_fill')) {
      this.map.setFilter('sigef_casos_analisados_fill', filterExpr);
    }
    if (this.map.getLayer('sigef_casos_analisados_line')) {
      this.map.setFilter('sigef_casos_analisados_line', filterExpr);
    }
  }

  layers: LayerConfig[] = [
    {
      id: 'tis_poligonais',
      name: 'Terras Indígenas (FUNAI)',
      sourceUrl: 'http://localhost:3000/tis_poligonais',
      sourceLayer: 'tis_poligonais',
      fillColor: '#ef4444',
      borderColor: '#b91c1c',
      visible: false
    },
    {
      id: 'areas_de_quilombolas_pe',
      name: 'Terras Quilombolas',
      sourceUrl: 'http://localhost:3000/areas_de_quilombolas_pe',
      sourceLayer: 'areas_de_quilombolas_pe',
      fillColor: '#a855f7',
      borderColor: '#7e22ce',
      visible: false
    },
    {
      id: 'sigef_privado_pe',
      name: 'SIGEF Privado',
      sourceUrl: 'http://localhost:3000/sigef_privado_pe',
      sourceLayer: 'sigef_privado_pe',
      fillColor: '#f59e0b',
      borderColor: '#b45309',
      visible: false
    },
    {
      id: 'sigef_publico_pe',
      name: 'SIGEF Público',
      sourceUrl: 'http://localhost:3000/sigef_publico_pe',
      sourceLayer: 'sigef_publico_pe',
      fillColor: '#6366f1',
      borderColor: '#4338ca',
      visible: false
    },
    {
      id: 'imovel_certificado_snci_privado_pe',
      name: 'SNCI Privado',
      sourceUrl: 'http://localhost:3000/imovel_certificado_snci_privado_pe',
      sourceLayer: 'imovel_certificado_snci_privado_pe',
      fillColor: '#10b981',
      borderColor: '#047857',
      visible: false
    },
    {
      id: 'imovel_certificado_snci_publico_pe',
      name: 'SNCI Público',
      sourceUrl: 'http://localhost:3000/imovel_certificado_snci_publico_pe',
      sourceLayer: 'imovel_certificado_snci_publico_pe',
      fillColor: '#14b8a6',
      borderColor: '#0f766e',
      visible: false
    },
    {
      id: 'car_casos_analisados',
      name: 'CAR - Casos Analisados (Batateiras)',
      sourceUrl: 'http://localhost:3000/car_casos_analisados',
      sourceLayer: 'car_casos_analisados',
      fillColor: '#0284c7',
      borderColor: '#0369a1',
      visible: false
    },
    {
      id: 'sigef_casos_analisados',
      name: 'SIGEF - Casos Analisados (Batateiras)',
      sourceUrl: 'http://localhost:3000/sigef_casos_analisados',
      sourceLayer: 'sigef_casos_analisados',
      fillColor: '#8b5cf6',
      borderColor: '#6d28d9',
      visible: false
    },
    {
      id: 'area_imovel_1',
      name: 'CAR - Imóveis Cadastrados',
      sourceUrl: 'http://localhost:3000/area_imovel_1',
      sourceLayer: 'area_imovel_1',
      fillColor: '#84cc16',
      borderColor: '#4d7c0f',
      visible: false
    },
    {
      id: 'apps_1',
      name: 'CAR - APPs Declaradas',
      sourceUrl: 'http://localhost:3000/apps_1',
      sourceLayer: 'apps_1',
      fillColor: '#06b6d4',
      borderColor: '#0891b2',
      visible: false
    },
    {
      id: 'reserva_legal_1',
      name: 'CAR - Reserva Legal',
      sourceUrl: 'http://localhost:3000/reserva_legal_1',
      sourceLayer: 'reserva_legal_1',
      fillColor: '#15803d',
      borderColor: '#14532d',
      visible: false
    },
    {
      id: 'vegetacao_nativa_1',
      name: 'CAR - Vegetação Nativa',
      sourceUrl: 'http://localhost:3000/vegetacao_nativa_1',
      sourceLayer: 'vegetacao_nativa_1',
      fillColor: '#22c55e',
      borderColor: '#16a34a',
      visible: false
    },
    {
      id: 'limiteucsfederais_a',
      name: 'ICMBio - Unidades de Conservação',
      sourceUrl: 'http://localhost:3000/limiteucsfederais_a',
      sourceLayer: 'limiteucsfederais_a',
      fillColor: '#059669',
      borderColor: '#065f46',
      visible: false
    },
    {
      id: 'embargos_icmbio',
      name: 'ICMBio - Áreas Embargadas',
      sourceUrl: 'http://localhost:3000/embargos_icmbio',
      sourceLayer: 'embargos_icmbio',
      fillColor: '#f97316',
      borderColor: '#c2410c',
      visible: false
    },
    {
      id: 'autos_infracao_icmbio',
      name: 'ICMBio - Autos de Infração (Pontos)',
      sourceUrl: 'http://localhost:3000/autos_infracao_icmbio',
      sourceLayer: 'autos_infracao_icmbio',
      fillColor: '#eab308',
      borderColor: '#78350f',
      visible: false
    },
    {
      id: 'processos_conflitos_judiciais',
      name: 'DataJud TJPE/TRF5',
      sourceUrl: 'http://localhost:3000/processos_conflitos_judiciais',
      sourceLayer: 'processos_conflitos_judiciais',
      fillColor: '#8b5cf6',
      borderColor: '#4c1d95',
      visible: false
    },
    {
      id: 'alerts_with_intersections',
      name: 'MapBiomas - Alertas de Desmatamento',
      sourceUrl: 'http://localhost:3000/alerts_with_intersections',
      sourceLayer: 'alerts_with_intersections',
      fillColor: '#ea580c',
      borderColor: '#9a3412',
      visible: false
    },
    {
      id: 'car_with_alerts_and_intersections',
      name: 'MapBiomas - Imóveis CAR com Alertas',
      sourceUrl: 'http://localhost:3000/car_with_alerts_and_intersections',
      sourceLayer: 'car_with_alerts_and_intersections',
      fillColor: '#f59e0b',
      borderColor: '#b45309',
      visible: false
    },
    {
      id: 'assentamentos_incra_pe',
      name: 'INCRA - Assentamentos (SIPRA)',
      sourceUrl: 'http://localhost:3000/assentamentos_incra_pe',
      sourceLayer: 'assentamentos_incra_pe',
      fillColor: '#ea580c',
      borderColor: '#c2410c',
      visible: false
    },
    {
      id: 'ucs_estaduais_cprh_pe',
      name: 'CPRH - UCs Estaduais',
      sourceUrl: 'http://localhost:3000/ucs_estaduais_cprh_pe',
      sourceLayer: 'ucs_estaduais_cprh_pe',
      fillColor: '#10b981',
      borderColor: '#047857',
      visible: false
    },
    {
      id: 'processos_minerarios_pe',
      name: 'ANM - Processos Minerários',
      sourceUrl: 'http://localhost:3000/processos_minerarios_pe',
      sourceLayer: 'processos_minerarios_pe',
      fillColor: '#eab308',
      borderColor: '#a16207',
      visible: false
    },
    {
      id: 'ibge_favelas_comunidades_pe',
      name: 'IBGE - Favelas e Comunidades (2022)',
      sourceUrl: 'http://localhost:3000/ibge_favelas_comunidades_pe',
      sourceLayer: 'ibge_favelas_comunidades_pe',
      fillColor: '#ec4899',
      borderColor: '#be185d',
      visible: false
    },
    {
      id: 'moradia_legal_pe',
      name: 'TJPE - Moradia Legal (REURB)',
      sourceUrl: 'http://localhost:3000/moradia_legal_pe',
      sourceLayer: 'moradia_legal_pe',
      fillColor: '#10b981',
      borderColor: '#047857',
      visible: false
    },
    {
      id: 'moradia_legal_processos_pe',
      name: 'TJPE - Usucapião (Moradia Legal)',
      sourceUrl: 'http://localhost:3000/moradia_legal_processos_pe',
      sourceLayer: 'moradia_legal_processos_pe',
      fillColor: '#059669',
      borderColor: '#064e3b',
      visible: false
    },
    {
      id: 'iterpe_glebas_pe',
      name: 'ITERPE - Glebas Públicas Estaduais',
      sourceUrl: 'http://localhost:3000/iterpe_glebas_pe',
      sourceLayer: 'iterpe_glebas_pe',
      fillColor: '#d97706',
      borderColor: '#b45309',
      visible: false
    },
    {
      id: 'iterpe_malha_posses_pe',
      name: 'ITERPE - Malha de Posses Rurais',
      sourceUrl: 'http://localhost:3000/iterpe_malha_posses_pe',
      sourceLayer: 'iterpe_malha_posses_pe',
      fillColor: '#a16207',
      borderColor: '#713f12',
      visible: false
    },
    // {
    //   id: 'land_overlaps',
    //   name: '⚠️ Áreas de Conflito (Sobreposições)',
    //   sourceUrl: 'http://localhost:3000/land_overlaps',
    //   sourceLayer: 'land_overlaps',
    //   fillColor: '#ec4899', // neon hot pink
    //   borderColor: '#be185d',
    //   visible: false
    // },
    // {
    //   id: 'land_overlaps_points',
    //   name: '📍 Centros de Conflito (Pontos)',
    //   sourceUrl: 'http://localhost:3000/land_overlaps_points',
    //   sourceLayer: 'land_overlaps_points',
    //   fillColor: '#ef4444', // Red
    //   borderColor: '#ffffff',
    //   visible: false
    // }
  ];

  ngAfterViewInit() {
    // Global handler for copy and KML export buttons inside map popups
    document.addEventListener('click', (e: MouseEvent) => {
      const kmlBtn = (e.target as HTMLElement).closest('[data-action="export-single-kml"]') as HTMLButtonElement | null;
      if (kmlBtn && this.activeSelectedFeatureItem) {
        e.preventDefault();
        e.stopPropagation();
        this.kmlExportService.exportSingleFeature(this.activeSelectedFeatureItem);
        return;
      }

      const target = (e.target as HTMLElement).closest('.popup-copy-btn') as HTMLButtonElement | null;
      if (!target) return;
      const textToCopy = target.getAttribute('data-copy');
      if (!textToCopy) return;

      const setSuccess = () => {
        target.classList.add('copied');
        const span = target.querySelector('.copy-label') || target;
        const originalText = span.textContent;
        span.textContent = 'Copiado!';
        setTimeout(() => {
          target.classList.remove('copied');
          span.textContent = originalText;
        }, 2000);
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy)
          .then(setSuccess)
          .catch(() => {
            this.fallbackCopyText(textToCopy);
            setSuccess();
          });
      } else {
        this.fallbackCopyText(textToCopy);
        setSuccess();
      }
    });

    this.map = new Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-37.5, -8.5], // Pernambuco
      zoom: 7,
      attributionControl: false
    });

    const attribControl = new AttributionControl({ compact: true });
    attribControl._updateCompact = () => {
      const container = (attribControl as any)._container;
      if (!container) return;
      container.classList.add('maplibregl-compact');
      if (!container.classList.contains('maplibregl-compact-show')) {
        container.removeAttribute('open');
      }
    };
    this.map.addControl(attribControl, 'bottom-right');

    const collapseAttribution = () => {
      const el = this.map?.getContainer()?.querySelector('.maplibregl-ctrl-attrib');
      if (el) {
        el.classList.add('maplibregl-compact');
        el.classList.remove('maplibregl-compact-show');
        el.removeAttribute('open');
      }
    };
    collapseAttribution();

    this.map.on('load', () => {
      collapseAttribution();
      // Find the first symbol/label layer in the basemap style so that data layers
      // (polygons, lines, and point circles) are rendered underneath city/place names and road labels.
      const styleLayers = this.map.getStyle().layers;
      let firstLabelId: string | undefined;
      if (styleLayers) {
        for (const l of styleLayers) {
          if (
            l.type === 'symbol' &&
            (l.id.startsWith('place_') ||
              l.id.startsWith('watername_') ||
              l.id.startsWith('roadname_') ||
              l.id.startsWith('poi_'))
          ) {
            firstLabelId = l.id;
            break;
          }
        }

        // Highlight city, town, village, and road labels with strong contrast and thick halos
        // so municipal names pop out clearly and legibly over dense point clusters and polygons.
        for (const l of styleLayers) {
          if (l.type === 'symbol') {
            if (l.id.startsWith('place_')) {
              this.map.setPaintProperty(l.id, 'text-color', '#0f172a'); // Deep high-contrast dark slate
              this.map.setPaintProperty(l.id, 'text-halo-color', '#ffffff'); // Solid bright white halo
              this.map.setPaintProperty(l.id, 'text-halo-width', 2.5); // Thick protective badge halo
              this.map.setPaintProperty(l.id, 'text-halo-blur', 0.5);
            } else if (l.id.startsWith('roadname_')) {
              this.map.setPaintProperty(l.id, 'text-color', '#334155');
              this.map.setPaintProperty(l.id, 'text-halo-color', '#ffffff');
              this.map.setPaintProperty(l.id, 'text-halo-width', 1.8);
            }
          }
        }
      }

      // 1. Create a beautiful red pin image programmatically
      const width = 32;
      const height = 40;
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        // Draw pin shadow
        ctx.beginPath();
        ctx.ellipse(16, 38, 6, 2, 0, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.fill();

        // Draw pin outer boundary (red teardrop shape)
        ctx.beginPath();
        ctx.moveTo(16, 40); // Tip at the bottom center
        ctx.bezierCurveTo(11, 30, 4, 23, 4, 16);
        ctx.arc(16, 16, 12, Math.PI, 0, false);
        ctx.bezierCurveTo(28, 23, 21, 30, 16, 40);
        ctx.closePath();

        // Fill with bright red
        ctx.fillStyle = '#ef4444';
        ctx.fill();

        // White border around the pin body
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2.5;
        ctx.stroke();

        // Draw the inner white dot/eye
        ctx.beginPath();
        ctx.arc(16, 16, 4.5, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        const imageData = ctx.getImageData(0, 0, width, height);
        this.map.addImage('red-pin', imageData);
      }

      // Add Satellite raster source (ESRI World Imagery - high resolution aerial/satellite photography)
      this.map.addSource('satellite-source', {
        type: 'raster',
        tiles: [
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        ],
        tileSize: 256,
        maxzoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and GIS User Community'
      });

      // Add Satellite raster layer directly before firstLabelId and before custom data layers
      this.map.addLayer(
        {
          id: 'satellite-layer',
          type: 'raster',
          source: 'satellite-source',
          layout: {
            visibility: this.currentBasemap === 'satellite' ? 'visible' : 'none'
          },
          paint: {
            'raster-opacity': 1.0,
            'raster-fade-duration': 300
          }
        },
        firstLabelId
      );

      // State boundary line overlay for Satellite view
      this.map.addLayer(
        {
          id: 'satellite-boundary-state',
          type: 'line',
          source: 'carto',
          'source-layer': 'boundary',
          minzoom: 4,
          filter: ['all', ['==', 'admin_level', 4], ['==', 'maritime', 0]],
          layout: {
            visibility: this.currentBasemap === 'satellite' ? 'visible' : 'none'
          },
          paint: {
            'line-color': '#ffffff',
            'line-width': 1.4,
            'line-dasharray': [3, 2],
            'line-opacity': 0.75
          }
        },
        firstLabelId
      );

      // Municipal boundary line overlay for Satellite view
      this.map.addLayer(
        {
          id: 'satellite-boundary-county',
          type: 'line',
          source: 'carto',
          'source-layer': 'boundary',
          minzoom: 8,
          filter: ['all', ['==', 'admin_level', 6], ['==', 'maritime', 0]],
          layout: {
            visibility: this.currentBasemap === 'satellite' ? 'visible' : 'none'
          },
          paint: {
            'line-color': '#ffffff',
            'line-width': 0.8,
            'line-dasharray': [2, 2],
            'line-opacity': 0.45
          }
        },
        firstLabelId
      );

      this.layers.forEach(layer => {
        // Add vector tile source
        this.map.addSource(layer.id, {
          type: 'vector',
          url: layer.sourceUrl
        });

        if (layer.id === 'land_overlaps_points') {
          // Add symbol layer for conflict points
          this.map.addLayer({
            id: `${layer.id}_symbol`,
            type: 'symbol',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            layout: {
              'icon-image': 'red-pin',
              'icon-size': 1.0,
              'icon-anchor': 'bottom',
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
              'visibility': layer.visible ? 'visible' : 'none'
            }
          });
        } else if (layer.id === 'autos_infracao_icmbio' || layer.id === 'processos_conflitos_judiciais' || layer.id === 'moradia_legal_processos_pe') {
          // Add circle layer for points (ICMBio infractions, DataJud lawsuits, or Moradia Legal usucapião) below city labels
          const circleColor: any = layer.id === 'processos_conflitos_judiciais'
            ? [
                'match',
                ['get', 'categoria_conflito'],
                'Reintegração e Conflito de Posse', '#8b5cf6',
                'Reforma Agrária & Desapropriação', '#f59e0b',
                'Povos Indígenas & Territórios Quilombolas', '#ef4444',
                'Terras Devolutas & Ações Discriminatórias', '#3b82f6',
                'Usucapião e Regularização de Posse', '#10b981',
                'Conflito Coletivo Rural & Agrário', '#ec4899',
                /* default */ '#8b5cf6'
              ]
            : layer.fillColor;

          this.map.addLayer({
            id: `${layer.id}_circle`,
            type: 'circle',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            paint: {
              'circle-color': circleColor,
              'circle-radius': (layer.id === 'processos_conflitos_judiciais' || layer.id === 'moradia_legal_processos_pe')
                ? ['interpolate', ['linear'], ['zoom'], 6, 4.5, 10, 6.5, 14, 9]
                : 4.5,
              'circle-stroke-width': 1.6,
              'circle-stroke-color': '#ffffff',
              'circle-opacity': 0.9
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          }, firstLabelId);
        } else {
          // Add fill layer (translucent) below city labels
          const fillColor: any = layer.id === 'sigef_casos_analisados' ? ['get', 'cor_hex'] : layer.fillColor;
          const fillOpacity = layer.id === 'land_overlaps' ? 0.75 : (layer.id === 'sigef_casos_analisados' ? 0.18 : 0.4);

          this.map.addLayer({
            id: `${layer.id}_fill`,
            type: 'fill',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            paint: {
              'fill-color': fillColor,
              'fill-opacity': fillOpacity
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          }, firstLabelId);

          // Add line layer (borders) below city labels
          const lineColor: any = layer.id === 'sigef_casos_analisados' ? ['get', 'cor_hex'] : layer.borderColor;
          const lineWidth = layer.id === 'land_overlaps' ? 3.0 : (layer.id === 'sigef_casos_analisados' ? 2.5 : 1.5);

          this.map.addLayer({
            id: `${layer.id}_line`,
            type: 'line',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            paint: {
              'line-color': lineColor,
              'line-width': lineWidth
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          }, firstLabelId);
        }
      });

      this.applySigefFilter();

      // Add Sources and Layers for Selection & KML Export Features
      this.map.addSource('selected-feature-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });

      this.map.addLayer({
        id: 'selected-feature-fill',
        type: 'fill',
        source: 'selected-feature-source',
        filter: ['any', ['==', '$type', 'Polygon'], ['==', '$type', 'MultiPolygon']],
        paint: {
          'fill-color': '#2563eb',
          'fill-opacity': 0.18
        }
      }, firstLabelId);

      this.map.addLayer({
        id: 'selected-feature-line',
        type: 'line',
        source: 'selected-feature-source',
        filter: ['any', ['==', '$type', 'Polygon'], ['==', '$type', 'MultiPolygon'], ['==', '$type', 'LineString']],
        paint: {
          'line-color': '#2563eb',
          'line-width': 2.8,
          'line-dasharray': [3, 2]
        }
      }, firstLabelId);

      this.map.addLayer({
        id: 'selected-feature-circle',
        type: 'circle',
        source: 'selected-feature-source',
        filter: ['==', '$type', 'Point'],
        paint: {
          'circle-radius': 11,
          'circle-color': 'transparent',
          'circle-stroke-color': '#2563eb',
          'circle-stroke-width': 2.8
        }
      }, firstLabelId);

      // --- POPUP RENDERERS ---
      const openCustomPopup = (html: string, coordinates: any) => {
        const kmlBtnHtml = `
          <button type="button" class="popup-btn popup-btn-kml" data-action="export-single-kml" title="Exportar feição selecionada e metadados para KML">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>Baixar KML</span>
          </button>
        `;
        const enhancedHtml = html.includes('</div>')
          ? html.replace(/(<\/div>\s*)$/, `${kmlBtnHtml}$1`)
          : `${html}${kmlBtnHtml}`;

        const popup = new Popup({ closeButton: true, className: 'custom-popup' })
          .setLngLat(coordinates)
          .setHTML(enhancedHtml)
          .addTo(this.map);

        popup.on('close', () => {
          this.clearFeatureHighlight();
        });

        return popup;
      };

      // 1. Conflict Areas & Center Pins
      const renderConflictPopup = (properties: any, coordinates: any) => {
        const traditionalName = properties['traditional_name'] || 'N/A';
        const traditionalSource = properties['traditional_source'] || 'N/A';
        const propertyNames = (properties['property_name'] || 'N/A').split('; ');
        const propertyCodes = (properties['property_code'] || 'N/A').split('; ');
        const propertySources = (properties['property_source'] || 'N/A').split('; ');

        let traditionalLabel = 'Território';
        if (traditionalSource === 'tis_poligonais') {
          traditionalLabel = 'Terra Indígena (FUNAI)';
        } else if (traditionalSource === 'areas_de_quilombolas_pe') {
          traditionalLabel = 'Território Quilombola (INCRA)';
        } else if (traditionalSource === 'limiteucsfederais_a') {
          traditionalLabel = 'Unidade de Conservação (ICMBio)';
        } else if (traditionalSource === 'embargos_icmbio') {
          traditionalLabel = 'Área Embargada (ICMBio)';
        }

        let propertiesHtml = '';
        const maxLen = Math.max(propertyNames.length, propertyCodes.length, propertySources.length);
        for (let i = 0; i < maxLen; i++) {
          const pName = propertyNames[i] || 'N/A';
          const pCode = propertyCodes[i] || 'N/A';
          const pSource = propertySources[i] || '';
          const pLabel = pSource.includes('snci') ? 'SNCI' : (pSource.includes('sigef') ? 'SIGEF' : (pSource.includes('area_imovel') || pSource.includes('sicar') ? 'CAR' : 'Imóvel'));

          propertiesHtml += `
            <div style="${i > 0 ? 'margin-top: 6px; padding-top: 6px; border-top: 1px solid #e2e8f0;' : ''}">
              <div class="popup-section">
                <span class="popup-label">${pLabel}:</span>
                <span class="popup-value">${pName}</span>
              </div>
              <div class="popup-section" style="margin-top: 2px;">
                <span class="popup-label">Código:</span>
                <span class="popup-value-code">${pCode}</span>
              </div>
            </div>
          `;
        }

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Conflito Territorial</span>
              <span class="popup-badge">Sobreposição</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">${traditionalLabel}:</span>
              <span class="popup-value" style="font-weight: 600;">${traditionalName}</span>
            </div>
            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Imóveis Incidentes (${maxLen}):</div>
              <div class="popup-detail-box-content" style="max-height: 140px;">
                ${propertiesHtml}
              </div>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 2. Federal Conservation Units (ICMBio)
      const renderUcsPopup = (properties: any, coordinates: any) => {
        const nomeUc = properties['nomeuc'] || 'N/A';
        const categoria = properties['categoria_'] || properties['sigla_cate'] || 'N/A';
        const grupo = properties['grupouc'] || 'N/A';
        const criacao = properties['criacaoano'] || 'N/A';
        const esfera = properties['esferaadm'] || 'Federal';
        const areaHa = properties['areahaalb'] ? Number(properties['areahaalb']).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + ' ha' : 'N/A';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Unidade de Conservação</span>
              <span class="popup-badge">${esfera}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Nome:</span>
              <span class="popup-value" style="font-weight: 600;">${nomeUc}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Categoria / Grupo:</span>
              <span class="popup-value">${categoria} (${grupo})</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Ano de Criação:</span>
              <span class="popup-value">${criacao}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área Oficial:</span>
              <span class="popup-value">${areaHa}</span>
            </div>
          </div>
        `;
        openCustomPopup(html, coordinates);
      };

      // 3. ICMBio Embargoes
      const renderEmbargosPopup = (properties: any, coordinates: any) => {
        const numEmb = properties['numero_emb'] || 'N/A';
        const autuado = properties['autuado'] || 'N/A';
        const cpfCnpj = properties['cpf_cnpj'] || '';
        const tipoInfra = properties['tipo_infra'] || properties['desc_inf_1'] || 'N/A';
        const uc = properties['nome_uc'] || 'N/A';
        const local = `${properties['municipio'] || ''} - ${properties['uf'] || ''}`;

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Área Embargada</span>
              <span class="popup-badge">ICMBio</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Termo de Embargo:</span>
              <span class="popup-value-code">${numEmb}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Autuado:</span>
              <span class="popup-value" style="font-weight: 500;">${autuado} ${cpfCnpj ? `(${cpfCnpj})` : ''}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Tipo de Infração:</span>
              <span class="popup-value">${tipoInfra}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Localização:</span>
              <span class="popup-value">${uc} (${local})</span>
            </div>
          </div>
        `;
        openCustomPopup(html, coordinates);
      };

      // 4. ICMBio Infraction Notices
      const renderAutosPopup = (properties: any, coordinates: any) => {
        const numAi = properties['numero_ai'] || 'N/A';
        const autuado = properties['autuado'] || 'N/A';
        const valor = properties['valor_mult'] ? 'R$ ' + Number(properties['valor_mult']).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : 'N/A';
        const tipoInfra = properties['tipo_infra'] || properties['desc_ai_1'] || 'N/A';
        const uc = properties['nome_uc'] || 'N/A';
        const local = `${properties['municipio'] || ''} - ${properties['uf'] || ''}`;

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Auto de Infração</span>
              <span class="popup-badge">ICMBio</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Número do Auto:</span>
              <span class="popup-value-code">${numAi}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Autuado:</span>
              <span class="popup-value" style="font-weight: 500;">${autuado}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Valor da Multa:</span>
              <span class="popup-value" style="font-weight: 600;">${valor}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Infração:</span>
              <span class="popup-value">${tipoInfra}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Localização:</span>
              <span class="popup-value">${uc} (${local})</span>
            </div>
          </div>
        `;
        openCustomPopup(html, coordinates);
      };

      // 5. DataJud Judicial Disputes (TJPE & TRF5)
      const renderDataJudPopup = (properties: any, coordinates: any) => {
        const rawNumProc = properties['numero_processo'] || 'N/A';
        const numProc = this.formatCNJ(rawNumProc);
        const tribunal = properties['tribunal'] || 'Judiciário';
        const grau = properties['grau'] || '1º Grau';
        const categoria = properties['categoria_conflito'] || 'Conflito Fundiário';
        const classe = properties['classe_nome'] ? `${properties['classe_nome']} (${properties['classe_codigo'] || ''})` : 'N/A';
        const assuntos = properties['assuntos_str'] || 'N/A';
        const orgao = properties['orgao_julgador_nome'] || 'N/A';
        const municipio = properties['municipio_nome'] || 'Pernambuco';
        const comarcaSede = properties['comarca_sede_nome'] || municipio;
        const municipiosAbrangidos = properties['municipios_abrangidos'] || '';
        const totalAbrangidos = properties['total_municipios_abrangidos'] || 1;
        const temFilhos = properties['tem_municipios_filhos'] === true || properties['tem_municipios_filhos'] === 'true' || totalAbrangidos > 1;
        const tipoJurisdicao = properties['tipo_jurisdicao'] || (tribunal === 'TJPE' ? 'Comarca Estadual (TJPE)' : 'Subseção Federal (JFPE)');
        const dataAjuiz = properties['data_ajuizamento'] ? new Date(properties['data_ajuizamento']).toLocaleDateString('pt-BR') : 'N/A';
        const ultimoMov = properties['ultimo_movimento'] || 'N/A';
        const dataUltimoMov = properties['data_ultimo_movimento'] ? new Date(properties['data_ultimo_movimento']).toLocaleDateString('pt-BR') : '';
        const totalMov = properties['total_movimentos'] || '1';
        const urlConsulta = properties['url_consulta_publica'] || '#';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Processo Judicial (${tribunal})</span>
              <span class="popup-badge">${grau}</span>
            </div>
            <div class="popup-section">
              <div class="popup-code-header">
                <span class="popup-label">Processo CNJ:</span>
                <button type="button" class="popup-copy-btn" data-copy="${numProc}" title="Copiar processo com pontuação padrão CNJ">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  <span class="copy-label">Copiar</span>
                </button>
              </div>
              <div class="popup-code-container">
                <span class="popup-value-code cnj-code select-all" title="Número do processo formatado com pontuação padrão CNJ">${numProc}</span>
              </div>
            </div>
            <div class="popup-section">
              <span class="popup-label">Classificação:</span>
              <span class="popup-value" style="font-weight: 500;">${categoria}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Vara / Órgão Julgador:</span>
              <span class="popup-value" style="font-weight: 500;">${orgao}</span>
              <span style="font-size: 0.72rem; color: #64748b; margin-top: 1px;">Sede: ${comarcaSede} (${tipoJurisdicao})</span>
              ${temFilhos ? `
                <div class="popup-detail-box">
                  <div class="popup-detail-box-title">Municípios sob Jurisdição (${totalAbrangidos}):</div>
                  <div class="popup-detail-box-content">${municipiosAbrangidos.split('; ').join(', ')}</div>
                  <div class="popup-detail-box-note">Abrange municípios sem comarca própria vinculados a esta sede.</div>
                </div>
              ` : ''}
            </div>
            <div class="popup-section">
              <span class="popup-label">Classe Processual:</span>
              <span class="popup-value">${classe}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Assuntos (TPU/CNJ):</span>
              <div class="popup-detail-box-content" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 5px 7px;">
                ${assuntos}
              </div>
            </div>
            <div class="popup-section" style="border-top: 1px solid #f1f5f9; padding-top: 6px; margin-top: 2px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748b;">
                <span>Ajuizamento: <strong style="color: #1e293b;">${dataAjuiz}</strong></span>
                <span>Movimentos: <strong style="color: #1e293b;">${totalMov}</strong></span>
              </div>
              <div style="font-size: 0.72rem; color: #64748b; margin-top: 2px;">
                <span>Último Andamento: <span style="color: #334155;">${ultimoMov}</span> ${dataUltimoMov ? `(${dataUltimoMov})` : ''}</span>
              </div>
            </div>
            <a href="${urlConsulta}" target="_blank" rel="noopener noreferrer" class="popup-btn">
              Consultar no PJe (${tribunal})
            </a>
          </div>
        `;
        openCustomPopup(html, coordinates);
      };

      // 6. MapBiomas Deforestation Alerts
      const renderAlertPopup = (props: any, coordinates: any) => {
        const code = props['alertcode'] || props['alertid'] || 'N/A';
        const areaHa = props['alertha'] ? Number(props['alertha']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ha' : 'N/A';
        const year = props['detectyear'] ? Math.round(props['detectyear']) : 'N/A';
        const detectDate = props['detectat'] ? new Date(props['detectat']).toLocaleDateString('pt-BR') : '';
        const imgBefore = props['beforimgdt'] ? String(props['beforimgdt']).split(' ')[0] : '';
        const imgAfter = props['afterimgdt'] ? String(props['afterimgdt']).split(' ')[0] : '';
        const pressure = props['alertclass'] || 'Desconhecido';
        const biome = props['biome'] || 'Caatinga / Mata Atlântica';
        const city = props['city'] || 'Pernambuco';
        const source = props['source'] || '';
        const sicar = props['cdsicar'] || '';
        const sigef = props['cdprisigef'] || props['cdpubsigef'] || '';
        const ucName = props['fedipname'] || props['fedsuname'] || props['staipname'] || props['stasuname'] || '';
        const tiName = props['inlandname'] || '';
        const quilName = props['quilname'] || '';

        let pressureLabel = pressure;
        if (pressure === 'agriculture') pressureLabel = 'Agropecuária / Agricultura';
        else if (pressure === 'urban_expansion') pressureLabel = 'Expansão Urbana';
        else if (pressure === 'renewable_energy_project') pressureLabel = 'Energia Renovável (Eólica/Solar)';
        else if (pressure.includes('mining')) pressureLabel = 'Mineração';
        else if (pressure === 'natural_cause') pressureLabel = 'Causa Natural';
        else if (pressure === 'others') pressureLabel = 'Outros Vetores de Supressão';

        let intersections = '';
        if (sicar) {
          const firstCar = sicar.split(',')[0];
          intersections += `<div style="font-size: 0.72rem; color: #374151; word-break: break-all;"><strong>CAR:</strong> <span class="popup-value-code">${firstCar}</span></div>`;
        }
        if (sigef) {
          intersections += `<div style="font-size: 0.72rem; color: #374151; margin-top: 2px;"><strong>SIGEF:</strong> <span class="popup-value-code">${sigef}</span></div>`;
        }
        if (ucName) {
          intersections += `<div style="font-size: 0.72rem; color: #334155; margin-top: 2px;"><strong>Unidade Conservação:</strong> ${ucName}</div>`;
        }
        if (tiName) {
          intersections += `<div style="font-size: 0.72rem; color: #334155; margin-top: 2px;"><strong>Terra Indígena:</strong> ${tiName}</div>`;
        }
        if (quilName) {
          intersections += `<div style="font-size: 0.72rem; color: #334155; margin-top: 2px;"><strong>Território Quilombola:</strong> ${quilName}</div>`;
        }

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Alerta de Desmatamento</span>
              <span class="popup-badge">${year}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Código do Alerta:</span>
              <span class="popup-value-code">#${code}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Vetor de Pressão:</span>
              <span class="popup-value" style="font-weight: 500;">${pressureLabel}</span>
            </div>
            <div class="popup-section" style="display: flex; flex-direction: row; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Área Desmatada:</span>
                <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
              </div>
              <div>
                <span class="popup-label">Bioma:</span>
                <span class="popup-value">${biome}</span>
              </div>
            </div>
            <div class="popup-section">
              <span class="popup-label">Localização:</span>
              <span class="popup-value">${city} - PE</span>
            </div>
            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              <div>Detecção: <strong>${detectDate}</strong> (${source})</div>
              ${imgBefore && imgAfter ? `<div>Período: ${imgBefore} a ${imgAfter}</div>` : ''}
            </div>
            ${intersections ? `
              <div class="popup-detail-box">
                <div class="popup-detail-box-title">Sobreposições Identificadas:</div>
                <div class="popup-detail-box-content">${intersections}</div>
              </div>
            ` : ''}
          </div>
        `;
        openCustomPopup(html, coordinates);
      };

      // 7. MapBiomas CAR with Deforestation Alerts
      const renderCarAlertPopup = (props: any, coordinates: any) => {
        const codSicar = props['codsicar'] || 'N/A';
        const alertCode = props['alertcode'] || props['alertid'] || 'N/A';
        const interHa = props['interha'] ? Number(props['interha']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ha' : 'N/A';
        const city = props['city'] || 'Pernambuco';
        const year = props['detectyear'] ? Math.round(props['detectyear']) : 'N/A';
        const alertClass = props['alertclass'] || 'Desconhecido';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Imóvel Rural com Alerta (CAR)</span>
              <span class="popup-badge">${year}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Código do Imóvel Rural (SICAR):</span>
              <span class="popup-value-code" style="word-break: break-all;">${codSicar}</span>
            </div>
            <div class="popup-section" style="display: flex; flex-direction: row; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Área Atingida no Imóvel:</span>
                <span class="popup-value" style="font-weight: 600;">${interHa}</span>
              </div>
              <div>
                <span class="popup-label">Alerta Associado:</span>
                <span class="popup-value-code">#${alertCode}</span>
              </div>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${city} - PE</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Vetor de Supressão:</span>
              <span class="popup-value">${alertClass}</span>
            </div>
          </div>
        `;
        openCustomPopup(html, coordinates);
      };

      // 8. CAR Properties (Both Analyzed Batateiras & General area_imovel_1)
      const renderCarPopup = (props: any, coordinates: any, underlyingSigefProps?: any) => {
        const rawCode = String(props['cod_imovel'] || '').trim();
        const cleanCode = rawCode.replace(/[\s\.]/g, '').toUpperCase();
        const enriched = ENRICHED_CAR_DATA[cleanCode] || {};

        const codImovel = rawCode || 'N/A';
        const nomeImovel = props['nome_imovel'] || enriched.nome_imovel || '';
        const declarante = props['declarante'] || enriched.declarante || '';
        const cpfDeclarante = props['cpf_declarante'] || enriched.cpf_declarante || '';
        const protocolo = props['codigo_protocolo'] || enriched.codigo_protocolo || '';
        const origemDoc = props['origem_documento'] || enriched.origem_documento || '';
        const sobreposicaoSigef = props['sobreposicao_sigef'] || enriched.sobreposicao_sigef || (underlyingSigefProps ? `${underlyingSigefProps['nome_area']} (Código: ${underlyingSigefProps['codigo_imo']})` : '');
        const matriculaCartorio = props['matricula_cartorio'] || enriched.matricula_cartorio || (underlyingSigefProps?.registro_m ? `Matrícula nº ${underlyingSigefProps.registro_m}` : '');
        const conflitoJudicial = props['conflito_judicial'] || enriched.conflito_judicial || '';

        const areaHa = (props['num_area'] !== undefined && props['num_area'] !== null && props['num_area'] !== '')
          ? Number(props['num_area']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' ha'
          : 'N/A';
        const modFiscal = (props['mod_fiscal'] !== undefined && props['mod_fiscal'] !== null && props['mod_fiscal'] !== '')
          ? Number(props['mod_fiscal']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
          : 'N/A';
        const status = props['ind_status'] || 'AT';
        const condic = props['des_condic'] || 'Aguardando análise';
        const municipio = props['municipio'] || 'Maraial';
        const dataCad = props['data_cadastro'] || props['dat_criaca'] || '';

        const badge = nomeImovel ? 'Análise Fundiária' : 'SICAR';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Imóvel Rural (CAR)</span>
              <span class="popup-badge">${badge}</span>
            </div>

            ${nomeImovel ? `
              <div class="popup-section">
                <span class="popup-label">Nome do Imóvel:</span>
                <span class="popup-value" style="font-weight: 600;">${nomeImovel}</span>
              </div>
            ` : ''}

            ${declarante ? `
              <div class="popup-section">
                <span class="popup-label">Declarante / Titular:</span>
                <span class="popup-value" style="font-weight: 500;">${declarante}</span>
                ${cpfDeclarante ? `<span style="font-size: 0.72rem; color: #64748b;">CPF: ${cpfDeclarante}</span>` : ''}
              </div>
            ` : ''}

            <div class="popup-section">
              <span class="popup-label">Código CAR (SICAR):</span>
              <span class="popup-value-code" style="word-break: break-all;">${codImovel}</span>
            </div>

            ${protocolo ? `
              <div class="popup-section">
                <span class="popup-label">Código do Protocolo:</span>
                <span class="popup-value-code" style="word-break: break-all;">${protocolo}</span>
              </div>
            ` : ''}

            <div class="popup-section" style="display: flex; flex-direction: row; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Área Declarada:</span>
                <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
              </div>
              <div>
                <span class="popup-label">Módulos Fiscais:</span>
                <span class="popup-value">${modFiscal}</span>
              </div>
            </div>

            <div class="popup-section">
              <span class="popup-label">Situação Cadastral:</span>
              <span class="popup-value">${status} (${condic})</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${municipio} - PE</span>
            </div>

            ${dataCad ? `
              <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
                <div>Cadastro: <strong>${dataCad}</strong></div>
                ${origemDoc ? `<div style="margin-top: 2px;">Documento: ${origemDoc}</div>` : ''}
              </div>
            ` : ''}

            ${sobreposicaoSigef ? `
              <div class="popup-detail-box">
                <div class="popup-detail-box-title">Sobreposição Fundiária:</div>
                <div class="popup-detail-box-content">${sobreposicaoSigef}</div>
                ${matriculaCartorio ? `<div class="popup-detail-box-note">${matriculaCartorio}</div>` : ''}
              </div>
            ` : ''}

            ${conflitoJudicial ? `
              <div class="popup-detail-box">
                <div class="popup-detail-box-title">Conflito Judicial na Comarca:</div>
                <div class="popup-detail-box-content">${conflitoJudicial}</div>
              </div>
            ` : ''}
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 9. SIGEF Properties (Privado e Público)
      const renderSigefPopup = (props: any, coordinates: any, isPublic: boolean) => {
        const nomeArea = props['nome_area'] || 'Imóvel Certificado';
        const codigoImo = props['codigo_imo'] || 'N/A';
        const status = props['status'] || 'REGISTRADA';
        const registroMatricula = props['registro_m'] || '';
        const registroData = props['registro_d'] ? new Date(props['registro_d']).toLocaleDateString('pt-BR') : '';
        const dataAprov = props['data_aprov'] ? new Date(props['data_aprov']).toLocaleDateString('pt-BR') : '';
        const dataSubmi = props['data_submi'] ? new Date(props['data_submi']).toLocaleDateString('pt-BR') : '';
        const municipioNome = props['municipio_nome'] || '';
        const municipioIbge = props['municipio'] || '';
        const localizacao = municipioNome ? `${municipioNome} - PE` : (municipioIbge ? `Município IBGE ${municipioIbge}` : 'Pernambuco');
        const rt = props['rt'] || '';
        const art = props['art'] || '';
        const parcelaId = props['parcela_co'] || '';

        const areaHa = (props['num_area'] !== undefined && props['num_area'] !== null && props['num_area'] !== '')
          ? Number(props['num_area']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ha'
          : 'N/A';

        const isBatateiras = codigoImo === '9510994953100' || (registroMatricula === '73' && (String(municipioIbge) === '2609204' || municipioNome.toLowerCase() === 'maraial'));

        const badge = isPublic ? 'SIGEF Público' : 'SIGEF Privado';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Imóvel Certificado (SIGEF)</span>
              <span class="popup-badge">${badge}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Nome da Propriedade:</span>
              <span class="popup-value" style="font-weight: 600;">${nomeArea}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Código INCRA / SIGEF:</span>
              <span class="popup-value-code">${codigoImo}</span>
            </div>

            <div class="popup-section" style="display: flex; flex-direction: row; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Área Certificada:</span>
                <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
              </div>
              <div>
                <span class="popup-label">Situação:</span>
                <span class="popup-value">${status}</span>
              </div>
            </div>

            <div class="popup-section">
              <span class="popup-label">Localização:</span>
              <span class="popup-value">${localizacao}</span>
            </div>

            ${registroMatricula ? `
              <div class="popup-section">
                <span class="popup-label">Registro Cartorial (RGI):</span>
                <span class="popup-value">Matrícula nº ${registroMatricula} ${registroData ? `(${registroData})` : ''}</span>
              </div>
            ` : ''}

            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              ${dataAprov ? `<div>Aprovação: <strong>${dataAprov}</strong></div>` : ''}
              ${dataSubmi && dataSubmi !== dataAprov ? `<div>Submissão: ${dataSubmi}</div>` : ''}
              ${rt || art ? `<div style="margin-top: 2px;">RT: ${rt} ${art ? `• ART: ${art}` : ''}</div>` : ''}
            </div>

            ${isBatateiras ? `
              <div class="popup-detail-box">
                <div class="popup-code-header">
                  <span class="popup-detail-box-title">Litígio Judicial:</span>
                  <button type="button" class="popup-copy-btn" data-copy="0000263-83.2026.8.17.2940" title="Copiar processo com pontuação padrão CNJ">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span class="copy-label">Copiar</span>
                  </button>
                </div>
                <div class="popup-detail-box-content">
                  Área com conflito fundiário e sobreposição sobre posses rurais da agricultura familiar.
                </div>
                <div class="popup-detail-box-note select-all">Ação TJPE Maraial nº 0000263-83.2026.8.17.2940</div>
              </div>
            ` : ''}

            ${parcelaId ? `
              <a href="https://sigef.incra.gov.br/consultar/parcela/${parcelaId}" target="_blank" rel="noopener noreferrer" class="popup-btn">
                Consultar no Portal SIGEF
              </a>
            ` : ''}
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 9b. SIGEF Casos Analisados (Histórico Batateiras / Fazenda 2 Irmãos)
      const renderSigefHistoricoPopup = (props: any, coordinates: any) => {
        const fase = props['fase'] || 'AV-23-73';
        const dataAverbacao = props['data_averbacao'] || '';
        const nomeImovel = props['nome_imovel'] || 'FAZENDA 2 IRMÃOS (Engenho Batateiras)';
        const codigoImo = props['codigo_imo'] || '9510994953100';
        const matriculaCartorio = props['matricula_cartorio'] || 'Matrícula nº 73 (Livro 02, RGI Maraial)';
        const proprietaria = props['proprietaria'] || '';
        const variacaoDescricao = props['variacao_descricao'] || '';
        const descricao = props['descricao'] || '';
        const corHex = props['cor_hex'] || '#8b5cf6';
        const parcelaCodigo = props['parcela_codigo'] || (codigoImo === '9510994953100' ? '21971a92-35e1-4f18-bda1-85bd31ccb13b' : '');

        const areaHa = (props['num_area'] !== undefined && props['num_area'] !== null && props['num_area'] !== '')
          ? Number(props['num_area']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + ' ha'
          : 'N/A';
        const perimetroM = (props['perimetro_m'] !== undefined && props['perimetro_m'] !== null && props['perimetro_m'] !== '')
          ? Number(props['perimetro_m']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' m'
          : 'N/A';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Histórico SIGEF (Evolução)</span>
              <span class="popup-badge" style="border-color: ${corHex}; color: ${corHex}; font-weight: 600;">${fase}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Imóvel Analisado:</span>
              <span class="popup-value" style="font-weight: 600;">${nomeImovel}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Código INCRA / SIGEF:</span>
              <span class="popup-value-code">${codigoImo}</span>
            </div>

            <div class="popup-section" style="display: flex; flex-direction: row; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Área Desta Fase:</span>
                <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
              </div>
              <div>
                <span class="popup-label">Perímetro:</span>
                <span class="popup-value">${perimetroM}</span>
              </div>
            </div>

            <div class="popup-section">
              <span class="popup-label">Proprietária Cadastrada:</span>
              <span class="popup-value" style="font-weight: 500;">${proprietaria}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Registro Cartorial / Data:</span>
              <span class="popup-value">${matriculaCartorio} • ${dataAverbacao}</span>
            </div>

            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Evolução Territorial (${fase}):</div>
              <div class="popup-detail-box-content">
                <strong>Variação:</strong> ${variacaoDescricao}
              </div>
              <div class="popup-detail-box-note" style="margin-top: 4px;">
                ${descricao}
              </div>
            </div>

            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Cronologia das 4 Fases (917 ha → 978 ha):</div>
              <div class="popup-detail-box-content" style="font-size: 0.72rem; line-height: 1.45;">
                <div style="padding: 2px 0; border-bottom: 1px dashed #e2e8f0; ${fase === 'AV-17-73' ? 'font-weight:700; color:#1d4ed8;' : ''}">
                  <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#3b82f6; margin-right:4px;"></span>
                  <strong>AV-17-73 (08/07/2020):</strong> 917,81 ha (Marco originário)
                </div>
                <div style="padding: 2px 0; border-bottom: 1px dashed #e2e8f0; ${fase === 'AV-19-73' ? 'font-weight:700; color:#b45309;' : ''}">
                  <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#f59e0b; margin-right:4px;"></span>
                  <strong>AV-19-73 (08/09/2020):</strong> 940,45 ha (+22,64 ha)
                </div>
                <div style="padding: 2px 0; border-bottom: 1px dashed #e2e8f0; ${fase === 'AV-23-73' ? 'font-weight:700; color:#b91c1c;' : ''}">
                  <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#ef4444; margin-right:4px;"></span>
                  <strong>AV-23-73 (04/02/2021):</strong> 977,78 ha (+37,33 ha)
                </div>
                <div style="padding: 2px 0; ${fase === 'SIGEF Atual' ? 'font-weight:700; color:#6d28d9;' : ''}">
                  <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#8b5cf6; margin-right:4px;"></span>
                  <strong>SIGEF Atual (19/05/2021):</strong> 978,93 ha (+61,13 ha total)
                </div>
              </div>
            </div>

            <div class="popup-detail-box">
              <div class="popup-code-header">
                <span class="popup-detail-box-title">Litígio Judicial:</span>
                <button type="button" class="popup-copy-btn" data-copy="0000263-83.2026.8.17.2940" title="Copiar processo com pontuação padrão CNJ">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  <span class="copy-label">Copiar</span>
                </button>
              </div>
              <div class="popup-detail-box-content">
                Área com conflito fundiário e sobreposição sobre posses rurais da agricultura familiar.
              </div>
              <div class="popup-detail-box-note select-all">Ação TJPE Maraial nº 0000263-83.2026.8.17.2940</div>
            </div>

            ${parcelaCodigo ? `
              <a href="https://sigef.incra.gov.br/consultar/parcela/${parcelaCodigo}" target="_blank" rel="noopener noreferrer" class="popup-btn">
                Consultar Parcela Atual no SIGEF
              </a>
            ` : ''}
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 10. SNCI Properties (Privado e Público)
      const renderSnciPopup = (props: any, coordinates: any, isPublic: boolean) => {
        const nomeImovel = props['nome_imove'] || 'Imóvel Certificado (SNCI)';
        const codImovel = props['cod_imovel'] || 'N/A';
        const numCertif = props['num_certif'] || 'N/A';
        const numProces = props['num_proces'] || 'N/A';
        const dataCerti = props['data_certi'] ? new Date(props['data_certi']).toLocaleDateString('pt-BR') : '';
        const areaHa = props['qtd_area_p'] ? Number(props['qtd_area_p']).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ha' : 'N/A';
        const sr = props['sr'] ? `SR-${props['sr']} (${props['sr'] === '03' ? 'Petrolina/PE' : 'Recife/PE'})` : 'INCRA';
        const credenciado = props['cod_profis'] || '';
        const municipioNome = props['municipio_nome'] || props['uf_municip'] || 'Pernambuco';

        const badge = isPublic ? 'SNCI Público' : 'SNCI Privado';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Imóvel Certificado (SNCI)</span>
              <span class="popup-badge">${badge}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Nome do Imóvel:</span>
              <span class="popup-value" style="font-weight: 600;">${nomeImovel}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Código SNCI (INCRA):</span>
              <span class="popup-value-code">${codImovel}</span>
            </div>

            <div class="popup-section" style="display: flex; flex-direction: row; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Área Certificada:</span>
                <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
              </div>
              <div>
                <span class="popup-label">Superintendência:</span>
                <span class="popup-value">${sr}</span>
              </div>
            </div>

            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${municipioNome} - PE</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Certificação INCRA:</span>
              <span class="popup-value-code">Nº ${numCertif}</span>
            </div>

            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              ${numProces && numProces !== 'N/A' ? `<div>Processo: ${numProces}</div>` : ''}
              ${dataCerti ? `<div>Certificação em: <strong>${dataCerti}</strong></div>` : ''}
              ${credenciado ? `<div>Credenciado: ${credenciado}</div>` : ''}
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 10. Assentamentos INCRA (SIPRA)
      const renderAssentamentoPopup = (properties: any, coordinates: any) => {
        const nomeProjeto = properties['no_projeto'] || 'Assentamento Rural';
        const cdSipra = properties['cd_sipra'] || 'N/A';
        const modalidade = properties['sg_modalidade'] || 'PA';
        const municipio = properties['no_municipio'] || 'Pernambuco';
        const capacidade = properties['nu_capacidade'] ? `${properties['nu_capacidade']} famílias` : 'N/A';
        const beneficio = properties['nu_beneficio'] ? `${properties['nu_beneficio']} beneficiários` : 'N/A';
        const areaHa = properties['nu_area_ha'] ? `${Number(properties['nu_area_ha']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A';
        const formaObtencao = properties['ds_forma_obtencao'] || 'N/A';
        const dataCriacao = properties['dt_criacao'] || properties['nu_ano_criacao'] || '';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${nomeProjeto}</span>
              <span class="popup-badge">${modalidade}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Código SIPRA:</span>
              <span class="popup-value-code">${cdSipra}</span>
            </div>
            <div class="popup-section" style="display: flex; justify-content: space-between; gap: 8px;">
              <div>
                <span class="popup-label">Capacidade:</span>
                <span class="popup-value">${capacidade}</span>
              </div>
              <div>
                <span class="popup-label">Beneficiários:</span>
                <span class="popup-value">${beneficio}</span>
              </div>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área Total:</span>
              <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${municipio} - PE</span>
            </div>
            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              <div>Obtenção: ${formaObtencao}</div>
              ${dataCriacao ? `<div>Criação: <strong>${dataCriacao}</strong></div>` : ''}
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 11. CPRH - Unidades de Conservação Estaduais
      const renderUcsEstadualPopup = (properties: any, coordinates: any) => {
        const nomeUc = properties['nome_uc'] || 'Unidade de Conservação Estadual';
        const categoria = properties['categoria'] || 'UC Estadual';
        const grupo = properties['grupo'] || 'Proteção Integral';
        const orgGestor = properties['org_gestor'] || 'CPRH / PE';
        const areaHa = properties['ha_total'] ? `${Number(properties['ha_total']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : (properties['area_ha'] ? `${Number(properties['area_ha']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A');
        const municipio = properties['municipio'] || 'Pernambuco';
        const cdCnuc = properties['cd_cnuc'] || 'N/A';
        const criaAto = properties['cria_ato'] || properties['cria_ano'] || '';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${nomeUc}</span>
              <span class="popup-badge">${categoria}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Código CNUC:</span>
              <span class="popup-value-code">${cdCnuc}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Grupo de Manejo:</span>
              <span class="popup-value">${grupo}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área da Unidade:</span>
              <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Órgão Gestor:</span>
              <span class="popup-value">${orgGestor}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${municipio}</span>
            </div>
            ${criaAto ? `
            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              <div>Ato Legal: ${criaAto}</div>
            </div>` : ''}
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 12. ANM - Processos Minerários
      const renderMineracaoPopup = (properties: any, coordinates: any) => {
        const processo = properties['processo'] || properties['dsprocesso'] || 'N/A';
        const fase = properties['fase'] || 'Processo Minerário';
        const subs = properties['subs'] || 'Substância Mineral';
        const nome = properties['nome'] || 'Titular Não Informado';
        const areaHa = properties['area_ha'] ? `${Number(properties['area_ha']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A';
        const ultEvento = properties['ult_evento'] || '';
        const ano = properties['ano'] || '';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Processo ANM</span>
              <span class="popup-badge">${fase}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Nº do Processo:</span>
              <span class="popup-value-code">${processo}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Substância:</span>
              <span class="popup-value" style="font-weight: 600;">${subs}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Requerente / Titular:</span>
              <span class="popup-value">${nome}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área Outorgada:</span>
              <span class="popup-value">${areaHa}</span>
            </div>
            ${ultEvento ? `
            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              <div>Último Evento: ${ultEvento}</div>
              ${ano ? `<div>Ano: ${ano}</div>` : ''}
            </div>` : ''}
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 13. IBGE - Favelas e Comunidades Urbanas (2022)
      const renderFavelasPopup = (properties: any, coordinates: any) => {
        const nomeComunidade = properties['nm_fcu'] || properties['nm_aglom'] || 'Comunidade Urbana';
        const municipio = properties['nm_mun'] || 'Pernambuco';
        const bairro = properties['nm_bairro'] || 'Não Informado';
        const cdSetor = properties['cd_setor'] || 'N/A';
        const cdFcu = properties['cd_fcu'] || properties['cd_aglom'] || 'N/A';
        const areaKm2 = properties['area_km2'] ? `${Number(properties['area_km2']).toLocaleString('pt-BR', { maximumFractionDigits: 3 })} km²` : 'N/A';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${nomeComunidade}</span>
              <span class="popup-badge">Favela / Comunidade</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Código FCU:</span>
              <span class="popup-value-code">${cdFcu}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Setor Censitário:</span>
              <span class="popup-value-code">${cdSetor}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value" style="font-weight: 600;">${municipio} - PE</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Bairro:</span>
              <span class="popup-value">${bairro}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área do Setor:</span>
              <span class="popup-value">${areaKm2}</span>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 14. Moradia Legal - REURB Polygons (TJPE)
      const renderMoradiaLegalPopup = (properties: any, coordinates: any) => {
        const nome = properties['nome'] || 'Área de Regularização';
        const municipio = properties['municipio'] || 'Pernambuco';
        const comunidade = properties['comunidade'] || nome;
        const tipo = properties['tipo'] || 'REURB / Regularização Fundiária';
        const origem = properties['origem'] || 'TJPE - Moradia Legal (NUREF)';
        const areaHa = properties['area_ha'] ? `${Number(properties['area_ha']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${comunidade}</span>
              <span class="popup-badge">REURB / TJPE</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Programa:</span>
              <span class="popup-value" style="font-weight: 600;">${origem}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value" style="font-weight: 500;">${municipio} - PE</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área do Núcleo:</span>
              <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Enquadramento:</span>
              <span class="popup-value">${tipo}</span>
            </div>
            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Garantia Dominial:</div>
              <div class="popup-detail-box-content">
                Área sob procedimento de regularização fundiária urbana/rural chancelada pela CGJ/TJPE.
              </div>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 15. Moradia Legal - Processos de Usucapião (TJPE)
      const renderMoradiaProcessoPopup = (properties: any, coordinates: any) => {
        const rawProc = properties['numero_processo'] || 'N/A';
        const numProc = this.formatCNJ(rawProc);
        const orgao = properties['orgao_judiciario'] || 'Vara Não Informada';
        const cidade = properties['cidade'] || 'Pernambuco';
        const bairro = properties['bairro'] || '';
        const logradouro = properties['logradouro'] || '';
        const numero = properties['numero'] || '';
        const cep = properties['cep'] || '';
        const obs = properties['observacao'] || '';
        const responsavel = properties['nome_responsavel'] || '';
        const dtCad = properties['data_cadastro'] || '';

        const enderecoCompleto = [logradouro, numero, bairro, cidade, cep ? `CEP ${cep}` : ''].filter(Boolean).join(', ');

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Usucapião / Moradia Legal</span>
              <span class="popup-badge">TJPE</span>
            </div>
            <div class="popup-section">
              <div class="popup-code-header">
                <span class="popup-label">Processo Judicial:</span>
                <button type="button" class="popup-copy-btn" data-copy="${numProc}" title="Copiar processo com pontuação padrão CNJ">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  <span class="copy-label">Copiar</span>
                </button>
              </div>
              <div class="popup-code-container">
                <span class="popup-value-code cnj-code select-all">${numProc}</span>
              </div>
            </div>
            <div class="popup-section">
              <span class="popup-label">Órgão Julgador:</span>
              <span class="popup-value" style="font-weight: 500;">${orgao}</span>
              <span style="font-size: 0.72rem; color: #64748b;">Comarca: ${cidade}</span>
            </div>
            ${enderecoCompleto ? `
            <div class="popup-section">
              <span class="popup-label">Imóvel Cadastrado:</span>
              <span class="popup-value">${enderecoCompleto}</span>
            </div>` : ''}
            ${obs ? `
            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Observações do Cadastro:</div>
              <div class="popup-detail-box-content">${obs}</div>
            </div>` : ''}
            ${responsavel ? `
            <div class="popup-section" style="font-size: 0.72rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              <div>Responsável: <strong>${responsavel}</strong></div>
              ${dtCad ? `<div>Cadastro: ${dtCad}</div>` : ''}
            </div>` : ''}
            <a href="https://pje.tjpe.jus.br/1g/ConsultaPublica/listView.seam" target="_blank" rel="noopener noreferrer" class="popup-btn">
              Consultar no PJe (TJPE)
            </a>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 16. ITERPE - Glebas Públicas Estaduais e Quilombos
      const renderIterpeGlebaPopup = (properties: any, coordinates: any) => {
        const nome = properties['nome'] || 'Gleba Estadual';
        const municipio = properties['municipio'] || 'Pernambuco';
        const tipo = properties['tipo'] || 'Gleba Estadual Arrecadada';
        const origem = properties['origem'] || 'ITERPE - Gerência de Ações Fundiárias (GERAF)';
        const areaHa = properties['area_ha'] ? `${Number(properties['area_ha']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A';

        const isQuilombo = String(tipo).toLowerCase().includes('quilombola');
        const badge = isQuilombo ? 'Quilombo Estadual' : 'Gleba Estadual';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${nome}</span>
              <span class="popup-badge">${badge}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Classificação:</span>
              <span class="popup-value" style="font-weight: 600;">${tipo}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value" style="font-weight: 500;">${municipio} - PE</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Área Discriminada/Arrecadada:</span>
              <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Órgão Fundiário:</span>
              <span class="popup-value">${origem}</span>
            </div>
            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Status Dominial:</div>
              <div class="popup-detail-box-content">
                Patrimônio territorial do Estado de Pernambuco discriminado para destinação fundiária e comunitária.
              </div>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 17. ITERPE - Malha de Posses Rurais
      const renderIterpePossePopup = (properties: any, coordinates: any) => {
        const numLote = properties['num_lote'] || 'N/A';
        const comarca = properties['comarca'] || properties['municipio'] || 'Pernambuco';
        const municipio = properties['municipio'] || comarca;
        const decreto = properties['decreto'] || 'N/A';
        const matricula = properties['matricula'] || 'N/A';
        const livro = properties['livro'] || '';
        const folha = properties['folha'] || '';
        const registro = properties['registro'] || '';
        const areaHa = properties['area_ha'] ? `${Number(properties['area_ha']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A';

        let cartorioStr = '';
        if (matricula && matricula !== 'N/A') {
          cartorioStr = `Matrícula nº ${matricula}`;
          if (livro) cartorioStr += ` (Livro ${livro}`;
          if (folha) cartorioStr += `, Fls. ${folha}`;
          if (livro) cartorioStr += `)`;
          if (registro) cartorioStr += ` - R-${registro}`;
        }

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>Lote ${numLote} (Posse Rural)</span>
              <span class="popup-badge">ITERPE</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Comarca / Município:</span>
              <span class="popup-value" style="font-weight: 600;">${municipio} (Comarca de ${comarca})</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Decreto de Arrecadação:</span>
              <span class="popup-value-code">${decreto}</span>
            </div>
            ${cartorioStr ? `
            <div class="popup-section">
              <span class="popup-label">Registro Imobiliário (RGI):</span>
              <span class="popup-value">${cartorioStr}</span>
            </div>` : ''}
            <div class="popup-section">
              <span class="popup-label">Área da Posse:</span>
              <span class="popup-value" style="font-weight: 600;">${areaHa}</span>
            </div>
            <div class="popup-detail-box">
              <div class="popup-detail-box-title">Agricultura Familiar:</div>
              <div class="popup-detail-box-content">
                Posse rural cadastrada na malha de terras devolutas e regularização agrária do ITERPE.
              </div>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 18. Terras Indígenas (FUNAI)
      const renderTiPopup = (props: any, coordinates: any) => {
        const terraiNom = props['terrai_nom'] || 'Terra Indígena';
        const etnia = props['etnia_nome'] || 'Não informada';
        const faseTi = props['fase_ti'] || 'Homologada / Regularizada';
        const modalidade = props['modalidade'] || 'Tradicionalmente Ocupada';
        const municipio = props['municipio_'] || 'Pernambuco';
        const superficie = props['superficie'] ? `${Number(props['superficie']).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : 'N/A';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${terraiNom}</span>
              <span class="popup-badge">FUNAI</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Povo / Etnia:</span>
              <span class="popup-value" style="font-weight: 600;">${etnia}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Fase de Demarcação:</span>
              <span class="popup-value">${faseTi} (${modalidade})</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Superfície Declarada:</span>
              <span class="popup-value" style="font-weight: 600;">${superficie}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${municipio} - PE</span>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // 19. Áreas de Quilombolas (INCRA)
      const renderQuilomboPopup = (props: any, coordinates: any) => {
        const comunidade = props['nm_comunid'] || 'Território Quilombola';
        const municipio = props['nm_municip'] || 'Pernambuco';
        const fase = props['fase'] || 'Certificado / Titulado';
        const processo = props['nr_process'] || 'N/A';
        const codigo = props['cd_quilomb'] || 'N/A';

        const html = `
          <div class="popup-card">
            <div class="popup-title">
              <span>${comunidade}</span>
              <span class="popup-badge">INCRA</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Código Quilombo:</span>
              <span class="popup-value-code">${codigo}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Fase do Processo:</span>
              <span class="popup-value" style="font-weight: 600;">${fase}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Nº Processo Administrativo:</span>
              <span class="popup-value-code">${processo}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Município:</span>
              <span class="popup-value">${municipio} - PE</span>
            </div>
          </div>
        `;

        openCustomPopup(html, coordinates);
      };

      // --- UNIFIED PRIORITY CLICK DISPATCHER ---
      // Setup hover cursor on all interactive layers
      this.priorityOrder.forEach(layerId => {
        if (this.map.getLayer(layerId)) {
          this.map.on('mouseenter', layerId, () => {
            this.map.getCanvas().style.cursor = 'pointer';
          });
          this.map.on('mouseleave', layerId, () => {
            this.map.getCanvas().style.cursor = '';
          });
        }
      });

      // Single click listener: queries visible layers and selects the top-priority feature
      this.map.on('click', (e) => {

        const activeLayers = this.priorityOrder.filter(id => {
          return this.map.getLayer(id) && this.map.getLayoutProperty(id, 'visibility') !== 'none';
        });

        if (activeLayers.length === 0) return;

        const rendered = this.map.queryRenderedFeatures(e.point, { layers: activeLayers });
        if (!rendered || rendered.length === 0) return;

        // Sort rendered features by priority order
        const sorted = rendered.sort((a, b) => {
          const idxA = this.priorityOrder.indexOf(a.layer.id);
          const idxB = this.priorityOrder.indexOf(b.layer.id);
          return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
        });

        const topFeature = sorted[0];
        const layerId = topFeature.layer.id;
        const props = topFeature.properties;
        if (!props) return;

        // Track selected feature for KML export & highlight on map
        const layerInfo = this.getLayerInfoForFeature(layerId);
        this.activeSelectedFeatureItem = {
          feature: topFeature,
          layerId: layerInfo.id,
          layerName: layerInfo.name,
          fillColor: layerInfo.fillColor,
          borderColor: layerInfo.borderColor
        };
        this.highlightFeature(topFeature);

        if (layerId === 'land_overlaps_points_symbol' || layerId === 'land_overlaps_fill') {
          renderConflictPopup(props, e.lngLat);
        } else if (layerId === 'processos_conflitos_judiciais_circle') {
          renderDataJudPopup(props, e.lngLat);
        } else if (layerId === 'moradia_legal_processos_pe_circle') {
          renderMoradiaProcessoPopup(props, e.lngLat);
        } else if (layerId === 'autos_infracao_icmbio_circle') {
          renderAutosPopup(props, e.lngLat);
        } else if (layerId === 'moradia_legal_pe_fill') {
          renderMoradiaLegalPopup(props, e.lngLat);
        } else if (layerId === 'iterpe_glebas_pe_fill') {
          renderIterpeGlebaPopup(props, e.lngLat);
        } else if (layerId === 'iterpe_malha_posses_pe_fill') {
          renderIterpePossePopup(props, e.lngLat);
        } else if (layerId === 'car_casos_analisados_fill' || layerId === 'area_imovel_1_fill') {
          // If clicking on CAR, also check if there is an underlying SIGEF parcel to reference in the detail box
          const sigefFeature = sorted.find(f => f.layer.id === 'sigef_privado_pe_fill' || f.layer.id === 'sigef_publico_pe_fill' || f.layer.id === 'sigef_casos_analisados_fill');
          renderCarPopup(props, e.lngLat, sigefFeature?.properties);
        } else if (layerId === 'sigef_casos_analisados_fill') {
          renderSigefHistoricoPopup(props, e.lngLat);
        } else if (layerId === 'alerts_with_intersections_fill') {
          renderAlertPopup(props, e.lngLat);
        } else if (layerId === 'car_with_alerts_and_intersections_fill') {
          renderCarAlertPopup(props, e.lngLat);
        } else if (layerId === 'assentamentos_incra_pe_fill') {
          renderAssentamentoPopup(props, e.lngLat);
        } else if (layerId === 'ucs_estaduais_cprh_pe_fill') {
          renderUcsEstadualPopup(props, e.lngLat);
        } else if (layerId === 'processos_minerarios_pe_fill') {
          renderMineracaoPopup(props, e.lngLat);
        } else if (layerId === 'ibge_favelas_comunidades_pe_fill') {
          renderFavelasPopup(props, e.lngLat);
        } else if (layerId === 'tis_poligonais_fill') {
          renderTiPopup(props, e.lngLat);
        } else if (layerId === 'areas_de_quilombolas_pe_fill') {
          renderQuilomboPopup(props, e.lngLat);
        } else if (layerId === 'embargos_icmbio_fill') {
          renderEmbargosPopup(props, e.lngLat);
        } else if (layerId === 'limiteucsfederais_a_fill') {
          renderUcsPopup(props, e.lngLat);
        } else if (layerId === 'sigef_privado_pe_fill') {
          renderSigefPopup(props, e.lngLat, false);
        } else if (layerId === 'sigef_publico_pe_fill') {
          renderSigefPopup(props, e.lngLat, true);
        } else if (layerId === 'imovel_certificado_snci_privado_pe_fill') {
          renderSnciPopup(props, e.lngLat, false);
        } else if (layerId === 'imovel_certificado_snci_publico_pe_fill') {
          renderSnciPopup(props, e.lngLat, true);
        }
      });
    });
  }



  highlightFeature(feature: any) {
    if (!this.map) return;
    const source = this.map.getSource('selected-feature-source') as any;
    if (source) {
      source.setData({
        type: 'FeatureCollection',
        features: [feature]
      });
    }
  }

  clearFeatureHighlight() {
    if (!this.map) return;
    this.activeSelectedFeatureItem = null;
    const source = this.map.getSource('selected-feature-source') as any;
    if (source) {
      source.setData({
        type: 'FeatureCollection',
        features: []
      });
    }
  }

  getLayerInfoForFeature(renderedLayerId: string): { id: string; name: string; fillColor: string; borderColor: string } {
    const baseId = renderedLayerId
      .replace(/_fill$/, '')
      .replace(/_line$/, '')
      .replace(/_circle$/, '')
      .replace(/_symbol$/, '');

    const found = this.layers.find(l => l.id === baseId);
    if (found) {
      return {
        id: found.id,
        name: found.name,
        fillColor: found.fillColor,
        borderColor: found.borderColor
      };
    }

    if (renderedLayerId.startsWith('land_overlaps')) {
      return {
        id: 'land_overlaps',
        name: 'Áreas de Conflito (Sobreposições)',
        fillColor: '#ef4444',
        borderColor: '#b91c1c'
      };
    }

    return {
      id: renderedLayerId,
      name: 'Feição Territorial',
      fillColor: '#3b82f6',
      borderColor: '#1d4ed8'
    };
  }



  focusBatateiras(event?: MouseEvent) {
    if (event) event.stopPropagation();
    if (this.map) {
      this.map.flyTo({
        center: [-35.73, -8.81],
        zoom: 13.5,
        essential: true
      });
    }
  }

  toggleLayer(layer: LayerConfig) {
    layer.visible = !layer.visible;
    const visibility = layer.visible ? 'visible' : 'none';
    if (this.map) {
      if (this.map.getLayer(`${layer.id}_fill`)) {
        this.map.setLayoutProperty(`${layer.id}_fill`, 'visibility', visibility);
      }
      if (this.map.getLayer(`${layer.id}_line`)) {
        this.map.setLayoutProperty(`${layer.id}_line`, 'visibility', visibility);
      }
      if (this.map.getLayer(`${layer.id}_symbol`)) {
        this.map.setLayoutProperty(`${layer.id}_symbol`, 'visibility', visibility);
      }
      if (this.map.getLayer(`${layer.id}_circle`)) {
        this.map.setLayoutProperty(`${layer.id}_circle`, 'visibility', visibility);
      }

      if (layer.id === 'sigef_casos_analisados' && layer.visible) {
        this.applySigefFilter();
      }
    }
  }

  formatCNJ(raw: string | null | undefined): string {
    if (!raw || raw === 'N/A') return 'N/A';
    const clean = String(raw).replace(/\D/g, '');
    if (clean.length === 20) {
      return `${clean.slice(0, 7)}-${clean.slice(7, 9)}.${clean.slice(9, 13)}.${clean.slice(13, 14)}.${clean.slice(14, 16)}.${clean.slice(16, 20)}`;
    }
    if (clean.length >= 15 && clean.length < 20) {
      const padded = clean.padStart(20, '0');
      return `${padded.slice(0, 7)}-${padded.slice(7, 9)}.${padded.slice(9, 13)}.${padded.slice(13, 14)}.${padded.slice(14, 16)}.${padded.slice(16, 20)}`;
    }
    return String(raw);
  }

  private fallbackCopyText(text: string) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Fallback copy failed', err);
    }
    document.body.removeChild(textArea);
  }
}

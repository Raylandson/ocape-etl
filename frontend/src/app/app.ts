import { Component, AfterViewInit } from '@angular/core';
import { Map, Popup } from 'maplibre-gl';
import { DatajudLegendComponent } from './datajud-legend/datajud-legend.component';

interface LayerConfig {
  id: string;
  name: string;
  sourceUrl: string;
  sourceLayer: string;
  fillColor: string;
  borderColor: string;
  visible: boolean;
}

@Component({
  selector: 'app-root',
  imports: [DatajudLegendComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements AfterViewInit {
  map!: Map;
  isPanelOpen: boolean = true;

  togglePanel() {
    this.isPanelOpen = !this.isPanelOpen;
  }

  getActiveLayersCount(): number {
    return this.layers.filter(l => l.visible).length;
  }

  isDataJudVisible(): boolean {
    return this.layers.find(l => l.id === 'processos_conflitos_judiciais')?.visible ?? false;
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
    this.map = new Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-37.5, -8.5], // Pernambuco
      zoom: 7
    });

    this.map.on('load', () => {
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
        } else if (layer.id === 'autos_infracao_icmbio' || layer.id === 'processos_conflitos_judiciais') {
          // Add circle layer for points (ICMBio infractions or DataJud judicial processes) below city labels
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
              'circle-radius': layer.id === 'processos_conflitos_judiciais' 
                ? ['interpolate', ['linear'], ['zoom'], 6, 5, 10, 7.5, 14, 10]
                : 4.5,
              'circle-stroke-width': 1.8,
              'circle-stroke-color': '#ffffff',
              'circle-opacity': 0.9
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          }, firstLabelId);
        } else {
          // Add fill layer (translucent) below city labels
          this.map.addLayer({
            id: `${layer.id}_fill`,
            type: 'fill',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            paint: {
              'fill-color': layer.fillColor,
              'fill-opacity': layer.id === 'land_overlaps' ? 0.75 : 0.4
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          }, firstLabelId);

          // Add line layer (borders) below city labels
          this.map.addLayer({
            id: `${layer.id}_line`,
            type: 'line',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            paint: {
              'line-color': layer.borderColor,
              'line-width': layer.id === 'land_overlaps' ? 3.0 : 1.5
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          }, firstLabelId);
        }
      });

      // Add popup interaction for conflict areas (polygons) and pins
      const setupConflictPopup = (layerId: string) => {
        this.map.on('click', layerId, (e) => {
          const coordinates = e.lngLat;
          const properties = e.features?.[0]?.properties;
          if (!properties) return;

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

          new Popup({ closeButton: true, className: 'custom-popup' })
            .setLngLat(coordinates)
            .setHTML(html)
            .addTo(this.map);
        });

        this.map.on('mouseenter', layerId, () => {
          this.map.getCanvas().style.cursor = 'pointer';
        });
        this.map.on('mouseleave', layerId, () => {
          this.map.getCanvas().style.cursor = '';
        });
      };

      setupConflictPopup('land_overlaps_fill');
      setupConflictPopup('land_overlaps_points_symbol');

      // Popup handler for Federal Conservation Units (ICMBio)
      this.map.on('click', 'limiteucsfederais_a_fill', (e) => {
        const properties = e.features?.[0]?.properties;
        if (!properties) return;
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
        new Popup({ closeButton: true, className: 'custom-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'limiteucsfederais_a_fill', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'limiteucsfederais_a_fill', () => { this.map.getCanvas().style.cursor = ''; });

      // Popup handler for ICMBio Embargoes
      this.map.on('click', 'embargos_icmbio_fill', (e) => {
        const properties = e.features?.[0]?.properties;
        if (!properties) return;
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
        new Popup({ closeButton: true, className: 'custom-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'embargos_icmbio_fill', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'embargos_icmbio_fill', () => { this.map.getCanvas().style.cursor = ''; });

      // Popup handler for ICMBio Autos de Infração
      this.map.on('click', 'autos_infracao_icmbio_circle', (e) => {
        const properties = e.features?.[0]?.properties;
        if (!properties) return;
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
        new Popup({ closeButton: true, className: 'custom-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'autos_infracao_icmbio_circle', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'autos_infracao_icmbio_circle', () => { this.map.getCanvas().style.cursor = ''; });

      // Popup handler for DataJud Judicial Conflict Lawsuits (TJPE & TRF5)
      this.map.on('click', 'processos_conflitos_judiciais_circle', (e) => {
        const properties = e.features?.[0]?.properties;
        if (!properties) return;

        const numProc = properties['numero_processo'] || 'N/A';
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
              <span class="popup-label">Processo CNJ:</span>
              <span class="popup-value-code">${numProc}</span>
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
        new Popup({ closeButton: true, className: 'custom-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'processos_conflitos_judiciais_circle', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'processos_conflitos_judiciais_circle', () => { this.map.getCanvas().style.cursor = ''; });

      // Popup handler for MapBiomas Alertas de Desmatamento (alerts_with_intersections)
      this.map.on('click', 'alerts_with_intersections_fill', (e) => {
        const props = e.features?.[0]?.properties;
        if (!props) return;

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

        // Portuguese translation for pressure classes without emojis
        let pressureLabel = pressure;
        if (pressure === 'agriculture') pressureLabel = 'Agropecuária / Agricultura';
        else if (pressure === 'urban_expansion') pressureLabel = 'Expansão Urbana';
        else if (pressure === 'renewable_energy_project') pressureLabel = 'Energia Renovável (Eólica/Solar)';
        else if (pressure.includes('mining')) pressureLabel = 'Mineração';
        else if (pressure === 'natural_cause') pressureLabel = 'Causa Natural';
        else if (pressure === 'others') pressureLabel = 'Outros Vetores de Supressão';

        // Intersections builder
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

        new Popup({ closeButton: true, className: 'custom-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'alerts_with_intersections_fill', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'alerts_with_intersections_fill', () => { this.map.getCanvas().style.cursor = ''; });

      // Popup handler for MapBiomas CAR Imóveis com Alertas (car_with_alerts_and_intersections)
      this.map.on('click', 'car_with_alerts_and_intersections_fill', (e) => {
        const props = e.features?.[0]?.properties;
        if (!props) return;

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

        new Popup({ closeButton: true, className: 'custom-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'car_with_alerts_and_intersections_fill', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'car_with_alerts_and_intersections_fill', () => { this.map.getCanvas().style.cursor = ''; });
    });
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
    }
  }
}

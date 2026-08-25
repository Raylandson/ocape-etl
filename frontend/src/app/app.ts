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
      id: 'land_overlaps',
      name: '⚠️ Áreas de Conflito (Sobreposições)',
      sourceUrl: 'http://localhost:3000/land_overlaps',
      sourceLayer: 'land_overlaps',
      fillColor: '#ec4899', // neon hot pink
      borderColor: '#be185d',
      visible: false
    },
    {
      id: 'land_overlaps_points',
      name: '📍 Centros de Conflito (Pontos)',
      sourceUrl: 'http://localhost:3000/land_overlaps_points',
      sourceLayer: 'land_overlaps_points',
      fillColor: '#ef4444', // Red
      borderColor: '#ffffff',
      visible: false
    }
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
              <div class="popup-property-item" style="${i > 0 ? 'margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(229, 231, 235, 0.6);' : ''}">
                <div class="popup-section">
                  <span class="popup-label">${pLabel}:</span>
                  <span class="popup-value">${pName}</span>
                </div>
                <div class="popup-section" style="margin-top: 2px;">
                  <span class="popup-label" style="font-size: 0.65rem;">Código:</span>
                  <span class="popup-value-code">${pCode}</span>
                </div>
              </div>
            `;
          }

          const html = `
            <div class="popup-card">
              <div class="popup-title">⚠️ Conflito Territorial / Ambiental</div>
              <div class="popup-section" style="margin-bottom: 4px;">
                <span class="popup-label">${traditionalLabel}:</span>
                <span class="popup-value" style="font-weight: 700;">${traditionalName}</span>
              </div>
              <div class="popup-properties-container" style="max-height: 180px; overflow-y: auto; background: rgba(0, 0, 0, 0.02); padding: 8px; border-radius: 8px; border: 1px solid rgba(0, 0, 0, 0.04);">
                ${propertiesHtml}
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
            <div class="popup-title" style="color: #047857;">🌲 Unidade de Conservação (ICMBio)</div>
            <div class="popup-section">
              <span class="popup-label">Nome:</span>
              <span class="popup-value" style="font-weight: 700;">${nomeUc}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Categoria / Grupo:</span>
              <span class="popup-value">${categoria} (${grupo})</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Esfera / Ano:</span>
              <span class="popup-value">${esfera} • ${criacao}</span>
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
            <div class="popup-title" style="color: #c2410c;">🚫 Área Embargada (ICMBio)</div>
            <div class="popup-section">
              <span class="popup-label">Termo de Embargo:</span>
              <span class="popup-value-code">${numEmb}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Autuado:</span>
              <span class="popup-value" style="font-weight: 600;">${autuado}</span>
              ${cpfCnpj ? `<span style="font-size: 0.7rem; color: #6b7280;">(${cpfCnpj})</span>` : ''}
            </div>
            <div class="popup-section">
              <span class="popup-label">Tipo de Infração:</span>
              <span class="popup-value">${tipoInfra}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">UC / Localidade:</span>
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
            <div class="popup-title" style="color: #b45309;">⚡ Auto de Infração Ambiental (ICMBio)</div>
            <div class="popup-section">
              <span class="popup-label">Número do Auto:</span>
              <span class="popup-value-code">${numAi}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Autuado:</span>
              <span class="popup-value" style="font-weight: 600;">${autuado}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Valor da Multa:</span>
              <span class="popup-value" style="color: #b91c1c; font-weight: 700;">${valor}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">Infração:</span>
              <span class="popup-value">${tipoInfra}</span>
            </div>
            <div class="popup-section">
              <span class="popup-label">UC / Município:</span>
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
        const dataAjuiz = properties['data_ajuizamento'] ? new Date(properties['data_ajuizamento']).toLocaleDateString('pt-BR') : 'N/A';
        const ultimoMov = properties['ultimo_movimento'] || 'N/A';
        const dataUltimoMov = properties['data_ultimo_movimento'] ? new Date(properties['data_ultimo_movimento']).toLocaleDateString('pt-BR') : '';
        const totalMov = properties['total_movimentos'] || '1';
        const urlConsulta = properties['url_consulta_publica'] || '#';

        // Badge color mapping
        let catColor = '#8b5cf6';
        if (categoria.includes('Reforma Agrária')) catColor = '#f59e0b';
        else if (categoria.includes('Indígenas') || categoria.includes('Quilombolas')) catColor = '#ef4444';
        else if (categoria.includes('Devolutas') || categoria.includes('Discriminatória')) catColor = '#3b82f6';
        else if (categoria.includes('Usucapião')) catColor = '#10b981';
        else if (categoria.includes('Coletivo')) catColor = '#ec4899';

        const html = `
          <div class="popup-card">
            <div class="popup-title" style="color: #6d28d9; display: flex; align-items: center; justify-content: space-between;">
              <span>⚖️ Conflito na Justiça (${tribunal})</span>
              <span style="font-size: 0.65rem; background: rgba(109, 40, 217, 0.12); color: #6d28d9; padding: 2px 6px; border-radius: 9999px; font-weight: 700;">${grau}</span>
            </div>
            
            <div class="popup-section" style="margin-bottom: 2px;">
              <span class="popup-label">Processo CNJ:</span>
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 6px;">
                <span class="popup-value-code" style="font-weight: 700; color: #1e1b4b; background: #ede9fe;">${numProc}</span>
              </div>
            </div>

            <div style="display: inline-block; margin: 3px 0; padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; background-color: ${catColor}15; color: ${catColor}; border: 1px solid ${catColor}40;">
              ${categoria}
            </div>

            <div class="popup-section">
              <span class="popup-label">Vara / Comarca:</span>
              <span class="popup-value" style="font-size: 0.8rem; font-weight: 600;">${orgao}</span>
              <span style="font-size: 0.72rem; color: #6b7280;">Município: <strong>${municipio}</strong></span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Classe Processual:</span>
              <span class="popup-value" style="font-size: 0.78rem;">${classe}</span>
            </div>

            <div class="popup-section">
              <span class="popup-label">Assuntos (TPU/CNJ):</span>
              <div style="font-size: 0.74rem; color: #374151; max-height: 55px; overflow-y: auto; background: rgba(0,0,0,0.02); padding: 4px 6px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.05);">
                ${assuntos}
              </div>
            </div>

            <div class="popup-section" style="border-top: 1px dashed rgba(209, 213, 219, 0.8); padding-top: 6px; margin-top: 2px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #6b7280;">
                <span>Ajuizamento: <strong>${dataAjuiz}</strong></span>
                <span>Movimentos: <strong>${totalMov}</strong></span>
              </div>
              <div style="font-size: 0.72rem; color: #4b5563; margin-top: 2px;">
                <span>Último Andamento: <em>${ultimoMov}</em> ${dataUltimoMov ? `(${dataUltimoMov})` : ''}</span>
              </div>
            </div>

            <div style="margin-top: 6px; text-align: center;">
              <a href="${urlConsulta}" target="_blank" rel="noopener noreferrer" style="display: block; width: 100%; box-sizing: border-box; text-decoration: none; background: #6d28d9; color: #ffffff; padding: 6px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; transition: background 0.2s ease;">
                Consultar no PJe (${tribunal}) ↗
              </a>
            </div>
          </div>
        `;
        new Popup({ closeButton: true, className: 'custom-popup judicial-popup' }).setLngLat(e.lngLat).setHTML(html).addTo(this.map);
      });
      this.map.on('mouseenter', 'processos_conflitos_judiciais_circle', () => { this.map.getCanvas().style.cursor = 'pointer'; });
      this.map.on('mouseleave', 'processos_conflitos_judiciais_circle', () => { this.map.getCanvas().style.cursor = ''; });
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

import { Component, AfterViewInit } from '@angular/core';
import { Map, Popup } from 'maplibre-gl';

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
  imports: [],
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

  layers: LayerConfig[] = [
    {
      id: 'tis_poligonais',
      name: 'Terras Indígenas (FUNAI)',
      sourceUrl: 'http://localhost:3000/tis_poligonais',
      sourceLayer: 'tis_poligonais',
      fillColor: '#ef4444',
      borderColor: '#b91c1c',
      visible: true
    },
    {
      id: 'areas_de_quilombolas_pe',
      name: 'Terras Quilombolas',
      sourceUrl: 'http://localhost:3000/areas_de_quilombolas_pe',
      sourceLayer: 'areas_de_quilombolas_pe',
      fillColor: '#a855f7',
      borderColor: '#7e22ce',
      visible: true
    },
    {
      id: 'sigef_privado_pe',
      name: 'SIGEF Privado',
      sourceUrl: 'http://localhost:3000/sigef_privado_pe',
      sourceLayer: 'sigef_privado_pe',
      fillColor: '#f59e0b',
      borderColor: '#b45309',
      visible: true
    },
    {
      id: 'sigef_publico_pe',
      name: 'SIGEF Público',
      sourceUrl: 'http://localhost:3000/sigef_publico_pe',
      sourceLayer: 'sigef_publico_pe',
      fillColor: '#6366f1',
      borderColor: '#4338ca',
      visible: true
    },
    {
      id: 'imovel_certificado_snci_privado_pe',
      name: 'SNCI Privado',
      sourceUrl: 'http://localhost:3000/imovel_certificado_snci_privado_pe',
      sourceLayer: 'imovel_certificado_snci_privado_pe',
      fillColor: '#10b981',
      borderColor: '#047857',
      visible: true
    },
    {
      id: 'imovel_certificado_snci_publico_pe',
      name: 'SNCI Público',
      sourceUrl: 'http://localhost:3000/imovel_certificado_snci_publico_pe',
      sourceLayer: 'imovel_certificado_snci_publico_pe',
      fillColor: '#14b8a6',
      borderColor: '#0f766e',
      visible: true
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
      visible: true
    },
    {
      id: 'embargos_icmbio',
      name: 'ICMBio - Áreas Embargadas',
      sourceUrl: 'http://localhost:3000/embargos_icmbio',
      sourceLayer: 'embargos_icmbio',
      fillColor: '#f97316',
      borderColor: '#c2410c',
      visible: true
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
      id: 'land_overlaps',
      name: '⚠️ Áreas de Conflito (Sobreposições)',
      sourceUrl: 'http://localhost:3000/land_overlaps',
      sourceLayer: 'land_overlaps',
      fillColor: '#ec4899', // neon hot pink
      borderColor: '#be185d',
      visible: true
    },
    {
      id: 'land_overlaps_points',
      name: '📍 Centros de Conflito (Pontos)',
      sourceUrl: 'http://localhost:3000/land_overlaps_points',
      sourceLayer: 'land_overlaps_points',
      fillColor: '#ef4444', // Red
      borderColor: '#ffffff',
      visible: true
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
        } else if (layer.id === 'autos_infracao_icmbio') {
          // Add circle layer for infraction notice points
          this.map.addLayer({
            id: `${layer.id}_circle`,
            type: 'circle',
            source: layer.id,
            'source-layer': layer.sourceLayer,
            paint: {
              'circle-color': layer.fillColor,
              'circle-radius': 4.5,
              'circle-stroke-width': 1.5,
              'circle-stroke-color': layer.borderColor,
              'circle-opacity': 0.85
            },
            layout: {
              visibility: layer.visible ? 'visible' : 'none'
            }
          });
        } else {
          // Add fill layer (translucent)
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
          });

          // Add line layer (borders)
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
          });
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

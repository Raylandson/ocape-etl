import { Component, AfterViewInit } from '@angular/core';
import { Map } from 'maplibre-gl';

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
      this.layers.forEach(layer => {
        // Add vector tile source
        this.map.addSource(layer.id, {
          type: 'vector',
          url: layer.sourceUrl
        });

        // Add fill layer (translucent)
        this.map.addLayer({
          id: `${layer.id}_fill`,
          type: 'fill',
          source: layer.id,
          'source-layer': layer.sourceLayer,
          paint: {
            'fill-color': layer.fillColor,
            'fill-opacity': 0.4
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
            'line-width': 1.5
          },
          layout: {
            visibility: layer.visible ? 'visible' : 'none'
          }
        });
      });
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
    }
  }
}

import { Component, AfterViewInit } from '@angular/core';
import { Map } from 'maplibre-gl';

@Component({
  selector: 'app-root',
  imports: [],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements AfterViewInit {
  map!: Map;

  ngAfterViewInit() {
    this.map = new Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-37.5, -8.5], // Pernambuco geographic center approx
      zoom: 7
    });

    this.map.on('load', () => {
      // 1. Add sigef_privado_pe source
      this.map.addSource('sigef_privado_pe', {
        type: 'vector',
        url: 'http://localhost:3000/sigef_privado_pe'
      });

      // 2. Add sigef_privado_pe fill layer (translucent yellow)
      this.map.addLayer({
        id: 'sigef_privado_fill',
        type: 'fill',
        source: 'sigef_privado_pe',
        'source-layer': 'sigef_privado_pe',
        paint: {
          'fill-color': '#ffff00',
          'fill-opacity': 0.4
        }
      });

      // 3. Add sigef_privado_pe line layer (orange border)
      this.map.addLayer({
        id: 'sigef_privado_line',
        type: 'line',
        source: 'sigef_privado_pe',
        'source-layer': 'sigef_privado_pe',
        paint: {
          'line-color': '#ff8c00',
          'line-width': 1.5
        }
      });

      // 4. Add tis_poligonais source
      this.map.addSource('tis_poligonais', {
        type: 'vector',
        url: 'http://localhost:3000/tis_poligonais'
      });

      // 5. Add tis_poligonais fill layer (translucent red)
      this.map.addLayer({
        id: 'tis_poligonais_fill',
        type: 'fill',
        source: 'tis_poligonais',
        'source-layer': 'tis_poligonais',
        paint: {
          'fill-color': '#ff0000',
          'fill-opacity': 0.4
        }
      });

      // 6. Add tis_poligonais line layer (solid red border)
      this.map.addLayer({
        id: 'tis_poligonais_line',
        type: 'line',
        source: 'tis_poligonais',
        'source-layer': 'tis_poligonais',
        paint: {
          'line-color': '#ff0000',
          'line-width': 2
        }
      });
    });
  }
}

import { Injectable } from '@angular/core';

export interface KmlExportItem {
  feature: any; // GeoJSON.Feature
  layerId?: string;
  layerName?: string;
  fillColor?: string;
  borderColor?: string;
}

@Injectable({
  providedIn: 'root'
})
export class KmlExportService {

  /**
   * Translates a standard CSS hex color (#RRGGBB or #RRGGBBAA)
   * to Google Earth KML color format (AABBGGRR).
   */
  hexToKmlColor(hex: string, defaultAlphaHex = 'ff'): string {
    if (!hex) return 'ff000000';
    let clean = hex.replace('#', '').trim();
    if (clean.length === 3) {
      clean = clean.split('').map(c => c + c).join('');
    }
    let r = '00', g = '00', b = '00', a = defaultAlphaHex;
    if (clean.length === 6) {
      r = clean.slice(0, 2);
      g = clean.slice(2, 4);
      b = clean.slice(4, 6);
    } else if (clean.length === 8) {
      r = clean.slice(0, 2);
      g = clean.slice(2, 4);
      b = clean.slice(4, 6);
      a = clean.slice(6, 8);
    }
    return `${a}${b}${g}${r}`.toLowerCase();
  }

  /**
   * Sanitizes text strings for safe embedding into XML tags.
   */
  escapeXml(unsafe: any): string {
    if (unsafe === null || unsafe === undefined) return '';
    return String(unsafe)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  /**
   * Sanitizes filenames for local disk saving.
   */
  sanitizeFilename(name: string): string {
    return name
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // remove accents
      .replace(/[^a-zA-Z0-9_\-\.]/g, '_')
      .replace(/_+/g, '_')
      .toLowerCase();
  }

  /**
   * Extracts a representative human-friendly title for a feature.
   */
  getFeatureTitle(properties: Record<string, any>, layerName = 'Feição'): string {
    if (!properties) return layerName;
    return properties['nome_imovel'] ||
           properties['nome_area'] ||
           properties['nome_imove'] ||
           properties['no_projeto'] ||
           properties['nome_uc'] ||
           properties['nomeuc'] ||
           properties['nm_fcu'] ||
           properties['comunidade'] ||
           properties['nome'] ||
           properties['traditional_name'] ||
           (properties['numero_processo'] ? `Processo CNJ ${properties['numero_processo']}` : null) ||
           (properties['processo'] ? `Processo ANM ${properties['processo']}` : null) ||
           (properties['cod_imovel'] ? `CAR ${properties['cod_imovel']}` : null) ||
           (properties['codigo_imo'] ? `SIGEF ${properties['codigo_imo']}` : null) ||
           (properties['alertcode'] ? `Alerta #${properties['alertcode']}` : null) ||
           (properties['numero_ai'] ? `Auto #${properties['numero_ai']}` : null) ||
           (properties['numero_emb'] ? `Embargo #${properties['numero_emb']}` : null) ||
           `${layerName} (ID: ${properties['id'] || properties['objectid'] || properties['fid'] || '1'})`;
  }

  /**
   * Builds an institutional HTML table description for Google Earth balloon popups.
   */
  buildHtmlDescription(title: string, layerName: string, properties: Record<string, any>): string {
    const rows: string[] = [];

    // Fields to exclude or handle specially
    const skipFields = new Set([
      'geometry', 'geom', 'the_geom', 'shape', 'cor_hex', 'id', 'ogc_fid', 'objectid'
    ]);

    // Format key attributes nicely
    for (const [key, value] of Object.entries(properties)) {
      if (skipFields.has(key.toLowerCase()) || value === null || value === undefined || value === '') {
        continue;
      }
      
      let label = key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
      
      let displayVal = String(value);

      // Nicely format known keys
      if (key.includes('area') && !isNaN(Number(value))) {
        displayVal = `${Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 4 })} ha`;
      } else if (key.includes('data') && !isNaN(Date.parse(value))) {
        displayVal = new Date(value).toLocaleDateString('pt-BR');
      }

      rows.push(`
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 4px 6px; font-size: 11px; font-weight: 600; color: #475569; width: 38%;">${this.escapeXml(label)}:</td>
          <td style="padding: 4px 6px; font-size: 11px; color: #0f172a; word-break: break-word;">${this.escapeXml(displayVal)}</td>
        </tr>
      `);
    }

    return `<![CDATA[
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 360px; color: #1e293b;">
        <div style="background-color: #0f172a; color: #ffffff; padding: 8px 12px; border-radius: 6px 6px 0 0;">
          <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.85;">${this.escapeXml(layerName)}</div>
          <div style="font-size: 14px; font-weight: 600; margin-top: 2px;">${this.escapeXml(title)}</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-top: none; border-radius: 0 0 6px 6px; padding: 8px;">
          <table style="width: 100%; border-collapse: collapse;">
            <tbody>
              ${rows.join('\n')}
            </tbody>
          </table>
          <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: right;">
            Plataforma de Mapeamento de Conflitos Agrários • PE
          </div>
        </div>
      </div>
    ]]>`;
  }

  /**
   * Builds structured <ExtendedData> for QGIS/ArcGIS attribute table parsing.
   */
  buildExtendedData(properties: Record<string, any>): string {
    const dataTags: string[] = [];
    for (const [key, value] of Object.entries(properties)) {
      if (value === null || value === undefined) continue;
      const strVal = typeof value === 'object' ? JSON.stringify(value) : String(value);
      dataTags.push(`      <Data name="${this.escapeXml(key)}"><value>${this.escapeXml(strVal)}</value></Data>`);
    }
    return `    <ExtendedData>\n${dataTags.join('\n')}\n    </ExtendedData>`;
  }

  /**
   * Converts GeoJSON Coordinates into KML coordinate string.
   */
  coordinatesToKml(coords: number[][]): string {
    return coords
      .map(pt => `${pt[0]},${pt[1]},${pt[2] ?? 0}`)
      .join(' ');
  }

  /**
   * Converts GeoJSON geometry into KML geometry XML tags.
   */
  geometryToKml(geom: any): string {
    if (!geom) return '';

    switch (geom.type) {
      case 'Point': {
        const c = geom.coordinates;
        return `<Point><coordinates>${c[0]},${c[1]},${c[2] ?? 0}</coordinates></Point>`;
      }
      case 'LineString': {
        return `<LineString><coordinates>${this.coordinatesToKml(geom.coordinates)}</coordinates></LineString>`;
      }
      case 'MultiLineString': {
        const lines = geom.coordinates.map((lineCoords: number[][]) =>
          `<LineString><coordinates>${this.coordinatesToKml(lineCoords)}</coordinates></LineString>`
        ).join('');
        return `<MultiGeometry>${lines}</MultiGeometry>`;
      }
      case 'Polygon': {
        const outer = geom.coordinates[0];
        const inners = geom.coordinates.slice(1);
        let kml = `<Polygon><outerBoundaryIs><LinearRing><coordinates>${this.coordinatesToKml(outer)}</coordinates></LinearRing></outerBoundaryIs>`;
        for (const inner of inners) {
          kml += `<innerBoundaryIs><LinearRing><coordinates>${this.coordinatesToKml(inner)}</coordinates></LinearRing></innerBoundaryIs>`;
        }
        kml += `</Polygon>`;
        return kml;
      }
      case 'MultiPolygon': {
        const polys = geom.coordinates.map((polyCoords: number[][][]) => {
          const outer = polyCoords[0];
          const inners = polyCoords.slice(1);
          let p = `<Polygon><outerBoundaryIs><LinearRing><coordinates>${this.coordinatesToKml(outer)}</coordinates></LinearRing></outerBoundaryIs>`;
          for (const inner of inners) {
            p += `<innerBoundaryIs><LinearRing><coordinates>${this.coordinatesToKml(inner)}</coordinates></LinearRing></innerBoundaryIs>`;
          }
          p += `</Polygon>`;
          return p;
        }).join('');
        return `<MultiGeometry>${polys}</MultiGeometry>`;
      }
      default:
        console.warn(`Unsupported geometry type for KML conversion: ${geom.type}`);
        return '';
    }
  }

  /**
   * Builds a single Placemark XML block.
   */
  buildPlacemarkXml(item: KmlExportItem, styleId?: string): string {
    const properties = item.feature.properties || {};
    const layerName = item.layerName || 'Feição Territorial';
    const title = this.getFeatureTitle(properties, layerName);
    const geomXml = this.geometryToKml(item.feature.geometry);
    const extendedDataXml = this.buildExtendedData(properties);
    const descriptionHtml = this.buildHtmlDescription(title, layerName, properties);

    return `
    <Placemark>
      <name>${this.escapeXml(title)}</name>
      ${styleId ? `<styleUrl>#${styleId}</styleUrl>` : ''}
      <description>${descriptionHtml}</description>
${extendedDataXml}
      ${geomXml}
    </Placemark>`;
  }

  /**
   * Generates a complete OGC KML 2.2 XML document string for a list of items.
   */
  generateKmlDocument(documentName: string, items: KmlExportItem[]): string {
    // Generate unique styles based on layer / color configurations
    const styleMap = new Map<string, { id: string; stroke: string; fill: string }>();
    let styleCounter = 1;

    items.forEach(item => {
      const key = `${item.layerId || 'default'}_${item.fillColor || '#3b82f6'}_${item.borderColor || '#1d4ed8'}`;
      if (!styleMap.has(key)) {
        styleMap.set(key, {
          id: `style_${item.layerId || 'layer'}_${styleCounter++}`,
          stroke: this.hexToKmlColor(item.borderColor || '#1d4ed8', 'ff'),
          fill: this.hexToKmlColor(item.fillColor || '#3b82f6', '66') // 40% translucent fill
        });
      }
    });

    // Build <Style> definitions
    const stylesXml = Array.from(styleMap.values()).map(s => `
    <Style id="${s.id}">
      <LineStyle>
        <color>${s.stroke}</color>
        <width>2.2</width>
      </LineStyle>
      <PolyStyle>
        <color>${s.fill}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
      <IconStyle>
        <color>${s.stroke}</color>
        <scale>1.1</scale>
      </IconStyle>
    </Style>`).join('');

    // Group items by layer into <Folder> elements
    const layerGroups = new Map<string, KmlExportItem[]>();
    items.forEach(item => {
      const groupName = item.layerName || 'Feições Selecionadas';
      if (!layerGroups.has(groupName)) {
        layerGroups.set(groupName, []);
      }
      layerGroups.get(groupName)!.push(item);
    });

    const foldersXml = Array.from(layerGroups.entries()).map(([layerName, groupItems]) => {
      const placemarks = groupItems.map(item => {
        const key = `${item.layerId || 'default'}_${item.fillColor || '#3b82f6'}_${item.borderColor || '#1d4ed8'}`;
        const styleId = styleMap.get(key)?.id;
        return this.buildPlacemarkXml(item, styleId);
      }).join('');

      return `
    <Folder>
      <name>${this.escapeXml(layerName)} (${groupItems.length})</name>
      ${placemarks}
    </Folder>`;
    }).join('\n');

    return `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>${this.escapeXml(documentName)}</name>
    <description><![CDATA[Exportação KML gerada pela Plataforma de Mapeamento de Conflitos Agrários de Pernambuco.]]></description>
${stylesXml}
${foldersXml}
  </Document>
</kml>`;
  }

  /**
   * Triggers an immediate browser download of the generated KML file.
   */
  downloadKml(kmlContent: string, filename: string): void {
    const finalFilename = filename.endsWith('.kml') ? filename : `${filename}.kml`;
    const blob = new Blob([kmlContent], { type: 'application/vnd.google-earth.kml+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = this.sanitizeFilename(finalFilename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Convenience method to export a single inspected feature.
   */
  exportSingleFeature(item: KmlExportItem, customFilename?: string): void {
    const properties = item.feature.properties || {};
    const title = this.getFeatureTitle(properties, item.layerName || 'feicao');
    const docName = `${item.layerName || 'Feição'} - ${title}`;
    const filename = customFilename || `${this.sanitizeFilename(title)}.kml`;
    const kml = this.generateKmlDocument(docName, [item]);
    this.downloadKml(kml, filename);
  }

  /**
   * Convenience method to export multiple features from a selected area.
   */
  exportMultipleFeatures(items: KmlExportItem[], documentName = 'Área Selecionada - Exportação KML'): void {
    if (!items || items.length === 0) return;
    const dateStr = new Date().toISOString().slice(0, 10);
    const filename = `area_selecionada_conflitos_${dateStr}_${items.length}_feicoes.kml`;
    const kml = this.generateKmlDocument(documentName, items);
    this.downloadKml(kml, filename);
  }
}

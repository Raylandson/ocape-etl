/**
 * Human-friendly title for a feature, from a priority chain of property names.
 *
 * Moved out of the retired KmlExportService: KML is now generated server-side, but the overlap
 * stack panel still needs a label for each row.
 *
 * The chain has no rung for several layers (`terrai_nom` on `tis_poligonais`, for one), so
 * those land on the `"<Layer> (ID: n)"` fallback. Server-side exports prefer
 * `search_index.label` instead, which every layer declares in SEARCH_SOURCES.
 */
export function getFeatureTitle(properties: Record<string, any>, layerName = 'Feição'): string {
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

// Aliased: the maplibre `Map` type would otherwise shadow the global Map constructor.
import type { Map as MapLibreMap } from 'maplibre-gl';

/**
 * Central registry of every PostGIS layer published as a Martin vector-tile source.
 *
 * `id` is load-bearing and identical across four systems: the PostGIS table name, the Martin
 * source name, the `search_index.layer_id` value, and the frontend layer id.
 */

/**
 * How reliably `keyColumns` identifies a single feature. Drives whether the hide control is
 * offered and what the UI tells the user.
 *
 * - `unique`  — measured 1:1 against the live database.
 * - `shared`  — measured collisions; hiding one feature also hides those sharing its key.
 * - `none`    — no usable per-feature identity. Hiding must be disabled.
 */
export type KeyStability = 'unique' | 'shared' | 'none';

export interface LayerConfig {
  id: string;
  /**
   * Columns joined to form a per-feature identity key. ALL listed columns are used, never
   * probed in order — several layers have no single unique column (see docs/specs §3.1).
   * Empty means the layer has no usable key.
   *
   * Must only ever name text or integer columns: `String(x)` and MapLibre `to-string` agree on
   * those but diverge on floats, which would desync the JS key from the filter expression.
   */
  keyColumns: string[];
  keyStability: KeyStability;
  name: string;
  sourceUrl: string;
  sourceLayer: string;
  fillColor: string;
  borderColor: string;
  visible: boolean;
  // Rendering mode; layers without it keep the default fill + outline (or their id-specific style)
  geometry?: 'fill' | 'line' | 'circle';
}

export const LAYERS: readonly LayerConfig[] = [
  {
    id: 'tis_poligonais',
    keyColumns: ['gid'],
    keyStability: 'unique',
    name: 'Terras Indígenas (FUNAI)',
    sourceUrl: 'http://localhost:3000/tis_poligonais',
    sourceLayer: 'tis_poligonais',
    fillColor: '#ef4444',
    borderColor: '#b91c1c',
    visible: false
  },
  {
    id: 'areas_de_quilombolas_pe',
    keyColumns: ['nr_process', 'nm_comunid'],
    keyStability: 'unique',
    name: 'Terras Quilombolas',
    sourceUrl: 'http://localhost:3000/areas_de_quilombolas_pe',
    sourceLayer: 'areas_de_quilombolas_pe',
    fillColor: '#a855f7',
    borderColor: '#7e22ce',
    visible: false
  },
  {
    id: 'sigef_privado_pe',
    keyColumns: ['parcela_co'],
    keyStability: 'unique',
    name: 'SIGEF Privado',
    sourceUrl: 'http://localhost:3000/sigef_privado_pe',
    sourceLayer: 'sigef_privado_pe',
    fillColor: '#f59e0b',
    borderColor: '#b45309',
    visible: false
  },
  {
    id: 'sigef_publico_pe',
    keyColumns: ['parcela_co'],
    keyStability: 'unique',
    name: 'SIGEF Público',
    sourceUrl: 'http://localhost:3000/sigef_publico_pe',
    sourceLayer: 'sigef_publico_pe',
    fillColor: '#6366f1',
    borderColor: '#4338ca',
    visible: false
  },
  {
    id: 'imovel_certificado_snci_privado_pe',
    keyColumns: ['cod_imovel', 'num_certif'],
    keyStability: 'unique',
    name: 'SNCI Privado',
    sourceUrl: 'http://localhost:3000/imovel_certificado_snci_privado_pe',
    sourceLayer: 'imovel_certificado_snci_privado_pe',
    fillColor: '#10b981',
    borderColor: '#047857',
    visible: false
  },
  {
    id: 'imovel_certificado_snci_publico_pe',
    keyColumns: ['cod_imovel'],
    keyStability: 'unique',
    name: 'SNCI Público',
    sourceUrl: 'http://localhost:3000/imovel_certificado_snci_publico_pe',
    sourceLayer: 'imovel_certificado_snci_publico_pe',
    fillColor: '#14b8a6',
    borderColor: '#0f766e',
    visible: false
  },
  {
    id: 'car_casos_analisados',
    keyColumns: ['cod_imovel'],
    keyStability: 'unique',
    name: 'CAR - Casos Analisados (Batateiras)',
    sourceUrl: 'http://localhost:3000/car_casos_analisados',
    sourceLayer: 'car_casos_analisados',
    fillColor: '#0284c7',
    borderColor: '#0369a1',
    visible: false
  },
  {
    id: 'sigef_casos_analisados',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'SIGEF - Casos Analisados (Batateiras)',
    sourceUrl: 'http://localhost:3000/sigef_casos_analisados',
    sourceLayer: 'sigef_casos_analisados',
    fillColor: '#8b5cf6',
    borderColor: '#6d28d9',
    visible: false
  },
  {
    id: 'area_imovel_1',
    keyColumns: ['cod_imovel'],
    keyStability: 'shared',
    name: 'CAR - Imóveis Cadastrados',
    sourceUrl: 'http://localhost:3000/area_imovel_1',
    sourceLayer: 'area_imovel_1',
    fillColor: '#84cc16',
    borderColor: '#4d7c0f',
    visible: false
  },
  {
    id: 'apps_1',
    keyColumns: [],
    keyStability: 'none',
    name: 'CAR - APPs Declaradas',
    sourceUrl: 'http://localhost:3000/apps_1',
    sourceLayer: 'apps_1',
    fillColor: '#06b6d4',
    borderColor: '#0891b2',
    visible: false
  },
  {
    id: 'reserva_legal_1',
    keyColumns: [],
    keyStability: 'none',
    name: 'CAR - Reserva Legal',
    sourceUrl: 'http://localhost:3000/reserva_legal_1',
    sourceLayer: 'reserva_legal_1',
    fillColor: '#15803d',
    borderColor: '#14532d',
    visible: false
  },
  {
    id: 'vegetacao_nativa_1',
    keyColumns: [],
    keyStability: 'none',
    name: 'CAR - Vegetação Nativa',
    sourceUrl: 'http://localhost:3000/vegetacao_nativa_1',
    sourceLayer: 'vegetacao_nativa_1',
    fillColor: '#22c55e',
    borderColor: '#16a34a',
    visible: false
  },
  {
    id: 'limiteucsfederais_a',
    keyColumns: ['ogc_fid'],
    keyStability: 'unique',
    name: 'ICMBio - Unidades de Conservação',
    sourceUrl: 'http://localhost:3000/limiteucsfederais_a',
    sourceLayer: 'limiteucsfederais_a',
    fillColor: '#059669',
    borderColor: '#065f46',
    visible: false
  },
  {
    id: 'embargos_icmbio',
    keyColumns: ['ogc_fid'],
    keyStability: 'unique',
    name: 'ICMBio - Áreas Embargadas',
    sourceUrl: 'http://localhost:3000/embargos_icmbio',
    sourceLayer: 'embargos_icmbio',
    fillColor: '#f97316',
    borderColor: '#c2410c',
    visible: false
  },
  {
    id: 'autos_infracao_icmbio',
    keyColumns: ['ogc_fid'],
    keyStability: 'unique',
    name: 'ICMBio - Autos de Infração (Pontos)',
    sourceUrl: 'http://localhost:3000/autos_infracao_icmbio',
    sourceLayer: 'autos_infracao_icmbio',
    fillColor: '#eab308',
    borderColor: '#78350f',
    visible: false
  },
  {
    id: 'processos_conflitos_judiciais',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'DataJud TJPE/TRF5',
    sourceUrl: 'http://localhost:3000/processos_conflitos_judiciais',
    sourceLayer: 'processos_conflitos_judiciais',
    fillColor: '#8b5cf6',
    borderColor: '#4c1d95',
    visible: false
  },
  {
    id: 'despejo_zero_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'Campanha Despejo Zero (Comunidades sob Risco)',
    sourceUrl: 'http://localhost:3000/despejo_zero_pe',
    sourceLayer: 'despejo_zero_pe',
    fillColor: '#dc2626',
    borderColor: '#7f1d1d',
    visible: false
  },
  {
    id: 'alerts_with_intersections',
    keyColumns: ['alertid'],
    keyStability: 'unique',
    name: 'MapBiomas - Alertas de Desmatamento',
    sourceUrl: 'http://localhost:3000/alerts_with_intersections',
    sourceLayer: 'alerts_with_intersections',
    fillColor: '#ea580c',
    borderColor: '#9a3412',
    visible: false
  },
  {
    id: 'car_with_alerts_and_intersections',
    keyColumns: ['codsicar', 'alertcode'],
    keyStability: 'unique',
    name: 'MapBiomas - Imóveis CAR com Alertas',
    sourceUrl: 'http://localhost:3000/car_with_alerts_and_intersections',
    sourceLayer: 'car_with_alerts_and_intersections',
    fillColor: '#f59e0b',
    borderColor: '#b45309',
    visible: false
  },
  {
    id: 'assentamentos_incra_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'INCRA - Assentamentos (SIPRA)',
    sourceUrl: 'http://localhost:3000/assentamentos_incra_pe',
    sourceLayer: 'assentamentos_incra_pe',
    fillColor: '#ea580c',
    borderColor: '#c2410c',
    visible: false
  },
  {
    id: 'ucs_estaduais_cprh_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'CPRH - UCs Estaduais',
    sourceUrl: 'http://localhost:3000/ucs_estaduais_cprh_pe',
    sourceLayer: 'ucs_estaduais_cprh_pe',
    fillColor: '#10b981',
    borderColor: '#047857',
    visible: false
  },
  {
    id: 'processos_minerarios_pe',
    keyColumns: ['id'],
    keyStability: 'shared',
    name: 'ANM - Processos Minerários',
    sourceUrl: 'http://localhost:3000/processos_minerarios_pe',
    sourceLayer: 'processos_minerarios_pe',
    fillColor: '#eab308',
    borderColor: '#a16207',
    visible: false
  },
  {
    id: 'ibge_favelas_comunidades_pe',
    keyColumns: ['cd_fcu', 'cd_setor'],
    keyStability: 'unique',
    name: 'IBGE - Favelas e Comunidades (2022)',
    sourceUrl: 'http://localhost:3000/ibge_favelas_comunidades_pe',
    sourceLayer: 'ibge_favelas_comunidades_pe',
    fillColor: '#ec4899',
    borderColor: '#be185d',
    visible: false
  },
  {
    id: 'moradia_legal_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'TJPE - Moradia Legal (REURB)',
    sourceUrl: 'http://localhost:3000/moradia_legal_pe',
    sourceLayer: 'moradia_legal_pe',
    fillColor: '#10b981',
    borderColor: '#047857',
    visible: false
  },
  {
    id: 'moradia_legal_processos_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'TJPE - Usucapião (Moradia Legal)',
    sourceUrl: 'http://localhost:3000/moradia_legal_processos_pe',
    sourceLayer: 'moradia_legal_processos_pe',
    fillColor: '#059669',
    borderColor: '#064e3b',
    visible: false
  },
  {
    id: 'iterpe_glebas_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ITERPE - Glebas Públicas Estaduais',
    sourceUrl: 'http://localhost:3000/iterpe_glebas_pe',
    sourceLayer: 'iterpe_glebas_pe',
    fillColor: '#d97706',
    borderColor: '#b45309',
    visible: false
  },
  {
    id: 'iterpe_malha_posses_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ITERPE - Malha de Posses Rurais',
    sourceUrl: 'http://localhost:3000/iterpe_malha_posses_pe',
    sourceLayer: 'iterpe_malha_posses_pe',
    fillColor: '#a16207',
    borderColor: '#713f12',
    visible: false
  },
  {
    id: 'aneel_sobreposicoes_territorios_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Sobreposições Energia × Territórios',
    sourceUrl: 'http://localhost:3000/aneel_sobreposicoes_territorios_pe',
    sourceLayer: 'aneel_sobreposicoes_territorios_pe',
    fillColor: '#c026d3',
    borderColor: '#86198f',
    visible: false
  },
  {
    id: 'aneel_dup_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - DUP (Servidões e Desapropriações)',
    sourceUrl: 'http://localhost:3000/aneel_dup_pe',
    sourceLayer: 'aneel_dup_pe',
    fillColor: '#be123c',
    borderColor: '#881337',
    visible: false
  },
  {
    id: 'epe_linhas_transmissao_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'EPE - Linhas de Transmissão (Rede Básica)',
    sourceUrl: 'http://localhost:3000/epe_linhas_transmissao_pe',
    sourceLayer: 'epe_linhas_transmissao_pe',
    fillColor: '#334155',
    borderColor: '#1e293b',
    visible: false,
    geometry: 'line'
  },
  {
    id: 'epe_subestacoes_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'EPE - Subestações',
    sourceUrl: 'http://localhost:3000/epe_subestacoes_pe',
    sourceLayer: 'epe_subestacoes_pe',
    fillColor: '#1e293b',
    borderColor: '#ffffff',
    visible: false,
    geometry: 'circle'
  },
  {
    id: 'aneel_lt_interesse_restrito_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Linhas de Interesse Restrito (Usinas)',
    sourceUrl: 'http://localhost:3000/aneel_lt_interesse_restrito_pe',
    sourceLayer: 'aneel_lt_interesse_restrito_pe',
    fillColor: '#0f766e',
    borderColor: '#115e59',
    visible: false,
    geometry: 'line'
  },
  {
    id: 'aneel_eol_parques_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Parques Eólicos (Polígonos)',
    sourceUrl: 'http://localhost:3000/aneel_eol_parques_pe',
    sourceLayer: 'aneel_eol_parques_pe',
    fillColor: '#0e7490',
    borderColor: '#164e63',
    visible: false
  },
  {
    id: 'aneel_eol_aerogeradores_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Aerogeradores',
    sourceUrl: 'http://localhost:3000/aneel_eol_aerogeradores_pe',
    sourceLayer: 'aneel_eol_aerogeradores_pe',
    fillColor: '#155e75',
    borderColor: '#ffffff',
    visible: false,
    geometry: 'circle'
  },
  {
    id: 'aneel_eol_usinas_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Usinas Eólicas (EOL)',
    sourceUrl: 'http://localhost:3000/aneel_eol_usinas_pe',
    sourceLayer: 'aneel_eol_usinas_pe',
    fillColor: '#0891b2',
    borderColor: '#ffffff',
    visible: false,
    geometry: 'circle'
  },
  {
    id: 'aneel_eol_interferencia_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Regiões de Interferência Eólica',
    sourceUrl: 'http://localhost:3000/aneel_eol_interferencia_pe',
    sourceLayer: 'aneel_eol_interferencia_pe',
    fillColor: '#67e8f9',
    borderColor: '#0e7490',
    visible: false
  },
  {
    id: 'aneel_ufv_parques_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Parques Solares (Polígonos)',
    sourceUrl: 'http://localhost:3000/aneel_ufv_parques_pe',
    sourceLayer: 'aneel_ufv_parques_pe',
    fillColor: '#ca8a04',
    borderColor: '#854d0e',
    visible: false
  },
  {
    id: 'aneel_ufv_paineis_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Arranjos de Painéis Solares',
    sourceUrl: 'http://localhost:3000/aneel_ufv_paineis_pe',
    sourceLayer: 'aneel_ufv_paineis_pe',
    fillColor: '#facc15',
    borderColor: '#a16207',
    visible: false
  },
  {
    id: 'aneel_ufv_subestacoes_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Subestações de Usinas Solares',
    sourceUrl: 'http://localhost:3000/aneel_ufv_subestacoes_pe',
    sourceLayer: 'aneel_ufv_subestacoes_pe',
    fillColor: '#713f12',
    borderColor: '#422006',
    visible: false
  },
  {
    id: 'aneel_ufv_usinas_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Usinas Solares (UFV)',
    sourceUrl: 'http://localhost:3000/aneel_ufv_usinas_pe',
    sourceLayer: 'aneel_ufv_usinas_pe',
    fillColor: '#eab308',
    borderColor: '#ffffff',
    visible: false,
    geometry: 'circle'
  },
  {
    id: 'aneel_ute_usinas_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Usinas Termelétricas (UTE)',
    sourceUrl: 'http://localhost:3000/aneel_ute_usinas_pe',
    sourceLayer: 'aneel_ute_usinas_pe',
    fillColor: '#78716c',
    borderColor: '#ffffff',
    visible: false,
    geometry: 'circle'
  },
  {
    id: 'aneel_hidro_reservatorios_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Reservatórios Hidrelétricos',
    sourceUrl: 'http://localhost:3000/aneel_hidro_reservatorios_pe',
    sourceLayer: 'aneel_hidro_reservatorios_pe',
    fillColor: '#3b82f6',
    borderColor: '#1d4ed8',
    visible: false
  },
  {
    id: 'aneel_hidro_aproveitamentos_pe',
    keyColumns: ['id'],
    keyStability: 'unique',
    name: 'ANEEL - Aproveitamentos Hidrelétricos (UHE/PCH/CGH)',
    sourceUrl: 'http://localhost:3000/aneel_hidro_aproveitamentos_pe',
    sourceLayer: 'aneel_hidro_aproveitamentos_pe',
    fillColor: '#1d4ed8',
    borderColor: '#ffffff',
    visible: false,
    geometry: 'circle'
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

/**
 * Click hit-test precedence, most specific first: small point targets lead so they stay
 * clickable, large background polygons trail.
 *
 * This is deliberately NOT the draw order and must stay frozen. Coupling it to the
 * user-controlled layer depth would make "send a point layer to the back" render that layer
 * unclickable. Depth lives in FeatureVisibilityService.drawOrder instead.
 *
 * Note `apps_1`, `reserva_legal_1` and `vegetacao_nativa_1` are absent: they render but are
 * not hit-tested, so they never reach the popup or the overlap stack.
 */
export const PRIORITY_ORDER: readonly string[] = [
  'land_overlaps_points_symbol',
  'processos_conflitos_judiciais_circle',
  'despejo_zero_pe_circle',
  'moradia_legal_processos_pe_circle',
  'autos_infracao_icmbio_circle',
  'aneel_eol_aerogeradores_pe_circle',
  'aneel_eol_usinas_pe_circle',
  'aneel_ufv_usinas_pe_circle',
  'aneel_ute_usinas_pe_circle',
  'aneel_hidro_aproveitamentos_pe_circle',
  'epe_subestacoes_pe_circle',
  'epe_linhas_transmissao_pe_line',
  'aneel_lt_interesse_restrito_pe_line',
  'car_casos_analisados_fill',
  'sigef_casos_analisados_fill',
  'aneel_sobreposicoes_territorios_pe_line',
  'aneel_sobreposicoes_territorios_pe_fill',
  'aneel_dup_pe_line',
  'aneel_dup_pe_fill',
  'aneel_ufv_subestacoes_pe_fill',
  'aneel_ufv_paineis_pe_fill',
  'aneel_ufv_parques_pe_fill',
  'aneel_eol_parques_pe_fill',
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
  'aneel_eol_interferencia_pe_fill',
  'aneel_hidro_reservatorios_pe_fill',
  'area_imovel_1_fill'
];

/** Suffixes appended to a layer id when its MapLibre layers are registered. */
export const RENDERED_SUFFIXES = ['_fill', '_line', '_circle', '_symbol'] as const;

/**
 * The MapLibre layer ids a config actually produced, which varies by geometry type: polygons
 * get `_fill` + `_line`, strips get `_line`, points get `_circle` or `_symbol`.
 *
 * Any operation applying to "the layer" (visibility, filters, reordering) must cover all of
 * them, so this is the single place that knowledge lives.
 */
export function renderedLayerIds(map: MapLibreMap, layerId: string): string[] {
  return RENDERED_SUFFIXES
    .map(suffix => `${layerId}${suffix}`)
    .filter(id => map.getLayer(id));
}

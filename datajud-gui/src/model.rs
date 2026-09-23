use serde::{Deserialize, Serialize};

/// Canonical agrarian and land conflict categories aligned with
/// the Land Conflict Mapping Platform (frontend and backend).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ConflictCategory {
    ReintegracaoPosse,
    ReformaAgraria,
    IndigenasQuilombolas,
    TerrasDevolutas,
    Usucapiao,
    ConflitoColetivo,
    Outros,
}

impl ConflictCategory {
    pub const ALL: [ConflictCategory; 6] = [
        ConflictCategory::ReintegracaoPosse,
        ConflictCategory::ReformaAgraria,
        ConflictCategory::IndigenasQuilombolas,
        ConflictCategory::TerrasDevolutas,
        ConflictCategory::Usucapiao,
        ConflictCategory::ConflitoColetivo,
    ];

    pub fn display_name(&self) -> &'static str {
        match self {
            Self::ReintegracaoPosse => "Reintegração e Conflito de Posse",
            Self::ReformaAgraria => "Reforma Agrária & Desapropriação",
            Self::IndigenasQuilombolas => "Povos Indígenas & Quilombolas",
            Self::TerrasDevolutas => "Terras Devolutas & Discriminatórias",
            Self::Usucapiao => "Usucapião e Regularização de Posse",
            Self::ConflitoColetivo => "Conflito Coletivo Rural & Agrário",
            Self::Outros => "Outros Conflitos Fundiários",
        }
    }

    /// Color hex matching frontend/src/app/datajud-legend/datajud-legend.component.ts
    pub fn color_rgb(&self) -> [u8; 3] {
        match self {
            Self::ReintegracaoPosse => [139, 92, 246],  // #8b5cf6
            Self::ReformaAgraria => [245, 158, 11],     // #f59e0b
            Self::IndigenasQuilombolas => [239, 68, 68], // #ef4444
            Self::TerrasDevolutas => [59, 130, 246],    // #3b82f6
            Self::Usucapiao => [16, 185, 129],          // #10b981
            Self::ConflitoColetivo => [236, 72, 153],   // #ec4899
            Self::Outros => [100, 116, 139],            // #64748b
        }
    }

    /// Default TPU Assunto codes associated with this category
    pub fn default_assunto_codes(&self) -> &'static [i64] {
        match self {
            Self::ReintegracaoPosse => &[10100, 10434, 10444, 10445, 10446, 7640, 3425],
            Self::ReformaAgraria => &[10124, 11873, 5995, 10185],
            Self::IndigenasQuilombolas => &[12031, 10104, 15114, 3647],
            Self::TerrasDevolutas => &[10094, 10451, 10453, 10105],
            Self::Usucapiao => &[10500, 10457, 10460, 10458, 10459],
            Self::ConflitoColetivo => &[11412, 11413, 9985],
            Self::Outros => &[],
        }
    }

    /// Default TPU Classe codes associated with this category
    pub fn default_classe_codes(&self) -> &'static [i64] {
        match self {
            Self::ReintegracaoPosse => &[1707, 1709],
            Self::ReformaAgraria => &[91, 90],
            Self::IndigenasQuilombolas => &[65, 63],
            Self::TerrasDevolutas => &[96, 34],
            Self::Usucapiao => &[49],
            Self::ConflitoColetivo => &[65, 63],
            Self::Outros => &[],
        }
    }
}

/// Categorizes a lawsuit into one of the 6 major agrarian/land conflict categories.
/// Logic mirrors src/etl_datajud.py:classify_conflict
pub fn classify_lawsuit(
    assuntos_codigos: &[i64],
    classe_codigo: Option<i64>,
    assuntos_nomes: &[String],
    classe_nome: &str,
) -> ConflictCategory {
    let full_text = format!("{} {}", assuntos_nomes.join(" "), classe_nome).to_lowercase();

    // 1. Povos Indígenas & Comunidades Quilombolas
    if assuntos_codigos.iter().any(|c| [12031, 10104, 15114, 3647].contains(c))
        || ["quilombola", "indígena", "indio", "xucuru", "funai"]
            .iter()
            .any(|k| full_text.contains(k))
    {
        return ConflictCategory::IndigenasQuilombolas;
    }

    // 2. Conflito Coletivo & Agrário
    if assuntos_codigos.iter().any(|c| [11412, 11413, 9985].contains(c))
        || ["conflito fundiário coletivo", "conflito agrário", "direito agrário"]
            .iter()
            .any(|k| full_text.contains(k))
    {
        return ConflictCategory::ConflitoColetivo;
    }

    // 3. Reforma Agrária & Desapropriação
    if assuntos_codigos.iter().any(|c| [10124, 11873, 5995, 10185].contains(c))
        || classe_codigo.is_some_and(|c| [91, 90].contains(&c))
        || ["reforma agrária", "dívida agrária", "tda", "desapropriação"]
            .iter()
            .any(|k| full_text.contains(k))
    {
        return ConflictCategory::ReformaAgraria;
    }

    // 4. Terras Devolutas & Ação Discriminatória
    if assuntos_codigos.iter().any(|c| [10094, 10451, 10453, 10105].contains(c))
        || classe_codigo.is_some_and(|c| [96, 34].contains(&c))
        || ["discriminatória", "terras devolutas", "demarcação"]
            .iter()
            .any(|k| full_text.contains(k))
    {
        return ConflictCategory::TerrasDevolutas;
    }

    // 5. Posse & Reintegração
    if assuntos_codigos.iter().any(|c| [10100, 10434, 10444, 10445, 10446, 7640, 3425].contains(c))
        || classe_codigo.is_some_and(|c| [1707, 1709].contains(&c))
        || ["reintegração", "esbulho", "turbação", "interdito proibitório", "imissão"]
            .iter()
            .any(|k| full_text.contains(k))
    {
        return ConflictCategory::ReintegracaoPosse;
    }

    // 6. Usucapião
    if assuntos_codigos.iter().any(|c| [10500, 10457, 10460, 10458, 10459].contains(c))
        || classe_codigo == Some(49)
        || full_text.contains("usucapião")
    {
        return ConflictCategory::Usucapiao;
    }

    ConflictCategory::Outros
}

/// Formats raw 20-digit CNJ process numbers into standard masked format:
/// NNNNNNN-DD.YYYY.J.TR.OOOO (mirrors format_cnj in src/etl_datajud.py)
pub fn format_cnj_mask(raw: &str) -> String {
    let digits: String = raw.chars().filter(|c| c.is_ascii_digit()).collect();
    if digits.len() == 20 {
        format!(
            "{}-{}.{}.{}.{}.{}",
            &digits[0..7],
            &digits[7..9],
            &digits[9..13],
            &digits[13..14],
            &digits[14..16],
            &digits[16..20]
        )
    } else {
        raw.trim().to_string()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessRecord {
    pub numero_processo: String,
    pub classe_codigo: Option<i64>,
    pub classe_nome: String,
    pub assuntos_codigos: Vec<i64>,
    pub assuntos_nomes: Vec<String>,
    pub orgao_julgador: String,
    pub municipio_ibge: Option<i64>,
    pub data_ajuizamento: String,
    pub grau: String,
    pub tribunal: String,
    pub categoria: ConflictCategory,
    pub raw_json: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct CsvExportRow<'a> {
    pub numero_processo: &'a str,
    pub tribunal: &'a str,
    pub categoria: &'a str,
    pub classe_codigo: Option<i64>,
    pub classe_nome: &'a str,
    pub assuntos_codigos: String,
    pub assuntos_nomes: String,
    pub orgao_julgador: &'a str,
    pub municipio_ibge: Option<i64>,
    pub data_ajuizamento: &'a str,
    pub grau: &'a str,
}

impl<'a> From<&'a ProcessRecord> for CsvExportRow<'a> {
    fn from(r: &'a ProcessRecord) -> Self {
        let assuntos_codigos_str = r
            .assuntos_codigos
            .iter()
            .map(|c| c.to_string())
            .collect::<Vec<_>>()
            .join("; ");
        let assuntos_nomes_str = r.assuntos_nomes.join("; ");

        Self {
            numero_processo: &r.numero_processo,
            tribunal: &r.tribunal,
            categoria: r.categoria.display_name(),
            classe_codigo: r.classe_codigo,
            classe_nome: &r.classe_nome,
            assuntos_codigos: assuntos_codigos_str,
            assuntos_nomes: assuntos_nomes_str,
            orgao_julgador: &r.orgao_julgador,
            municipio_ibge: r.municipio_ibge,
            data_ajuizamento: &r.data_ajuizamento,
            grau: &r.grau,
        }
    }
}

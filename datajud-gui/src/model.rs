use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub enum ConflictCategory {
    ReintegracaoPosse,
    Usucapiao,
    ReformaAgraria,
    TerrasDevolutas,
    IndigenasQuilombolas,
    ConflitoColetivo,
    Outros,
}

impl ConflictCategory {
    pub const ALL: [ConflictCategory; 7] = [
        ConflictCategory::ReintegracaoPosse,
        ConflictCategory::Usucapiao,
        ConflictCategory::ReformaAgraria,
        ConflictCategory::TerrasDevolutas,
        ConflictCategory::IndigenasQuilombolas,
        ConflictCategory::ConflitoColetivo,
        ConflictCategory::Outros,
    ];

    pub fn from_db(value: &str) -> Self {
        match value {
            "Reintegração e Conflito de Posse" => Self::ReintegracaoPosse,
            "Usucapião e Regularização de Posse" => Self::Usucapiao,
            "Reforma Agrária & Desapropriação" => Self::ReformaAgraria,
            "Terras Devolutas & Ações Discriminatórias" => Self::TerrasDevolutas,
            "Povos Indígenas & Territórios Quilombolas" => Self::IndigenasQuilombolas,
            "Conflito Coletivo Rural & Agrário" => Self::ConflitoColetivo,
            _ => Self::Outros,
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            Self::ReintegracaoPosse => "Reintegração e Conflito de Posse",
            Self::Usucapiao => "Usucapião e Regularização de Posse",
            Self::ReformaAgraria => "Reforma Agrária & Desapropriação",
            Self::TerrasDevolutas => "Terras Devolutas & Ações Discriminatórias",
            Self::IndigenasQuilombolas => "Povos Indígenas & Territórios Quilombolas",
            Self::ConflitoColetivo => "Conflito Coletivo Rural & Agrário",
            Self::Outros => "Outros Conflitos Fundiários",
        }
    }

    pub fn short_label(&self) -> &'static str {
        match self {
            Self::ReintegracaoPosse => "Posse / Reintegração",
            Self::Usucapiao => "Usucapião",
            Self::ReformaAgraria => "Reforma Agrária",
            Self::TerrasDevolutas => "Terras Devolutas",
            Self::IndigenasQuilombolas => "Indígenas / Quilombolas",
            Self::ConflitoColetivo => "Conflito Coletivo",
            Self::Outros => "Outros",
        }
    }

    /// Color hex matching frontend/src/app/datajud-legend/datajud-legend.component.ts
    pub fn color_rgb(&self) -> [u8; 3] {
        match self {
            Self::ReintegracaoPosse => [139, 92, 246],   // #8b5cf6
            Self::ReformaAgraria => [245, 158, 11],      // #f59e0b
            Self::IndigenasQuilombolas => [239, 68, 68], // #ef4444
            Self::TerrasDevolutas => [59, 130, 246],     // #3b82f6
            Self::Usucapiao => [16, 185, 129],           // #10b981
            Self::ConflitoColetivo => [236, 72, 153],    // #ec4899
            Self::Outros => [100, 116, 139],             // #64748b
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Tribunal {
    Tjpe,
    Trf5,
}

impl Tribunal {
    pub const ALL: [Tribunal; 2] = [Tribunal::Tjpe, Tribunal::Trf5];

    pub fn from_db(value: &str) -> Option<Self> {
        match value.trim().to_ascii_uppercase().as_str() {
            "TJPE" => Some(Self::Tjpe),
            "TRF5" => Some(Self::Trf5),
            _ => None,
        }
    }

    pub fn code(&self) -> &'static str {
        match self {
            Self::Tjpe => "TJPE",
            Self::Trf5 => "TRF5",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            Self::Tjpe => "Justiça Estadual",
            Self::Trf5 => "Justiça Federal (JFPE)",
        }
    }
}

pub fn grau_label(code: &str) -> &str {
    match code {
        "G1" => "1º grau",
        "G2" => "2º grau",
        "JE" => "Juizado Especial",
        "TR" => "Turma Recursal",
        "TRU" => "Turma Regional de Uniformização",
        other => other,
    }
}

pub fn parse_date(value: &str) -> Option<u32> {
    let b = value.as_bytes();
    if b.len() < 10 || b[4] != b'-' || b[7] != b'-' {
        return None;
    }
    let y: u32 = value.get(0..4)?.parse().ok()?;
    let m: u32 = value.get(5..7)?.parse().ok()?;
    let d: u32 = value.get(8..10)?.parse().ok()?;
    Some(y * 10_000 + m * 100 + d)
}

pub fn date_year(date: u32) -> u16 {
    (date / 10_000) as u16
}

pub fn format_date(date: Option<u32>) -> String {
    match date {
        Some(d) => format!("{:02}/{:02}/{:04}", d % 100, (d / 100) % 100, d / 10_000),
        None => "—".to_string(),
    }
}

pub fn format_date_iso(date: Option<u32>) -> String {
    match date {
        Some(d) => format!("{:04}-{:02}-{:02}", d / 10_000, (d / 100) % 100, d % 100),
        None => String::new(),
    }
}

pub fn format_count(n: usize) -> String {
    let digits = n.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (i, ch) in digits.chars().enumerate() {
        if i > 0 && (digits.len() - i).is_multiple_of(3) {
            out.push('.');
        }
        out.push(ch);
    }
    out
}

pub fn fold(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for ch in text.chars() {
        for lower in ch.to_lowercase() {
            out.push(match lower {
                'á' | 'à' | 'â' | 'ã' | 'ä' => 'a',
                'é' | 'è' | 'ê' | 'ë' => 'e',
                'í' | 'ì' | 'î' | 'ï' => 'i',
                'ó' | 'ò' | 'ô' | 'õ' | 'ö' => 'o',
                'ú' | 'ù' | 'û' | 'ü' => 'u',
                'ç' => 'c',
                'ñ' => 'n',
                other => other,
            });
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn category_roundtrip_from_db() {
        for cat in ConflictCategory::ALL {
            assert_eq!(ConflictCategory::from_db(cat.label()), cat);
        }
    }

    #[test]
    fn formats() {
        assert_eq!(format_count(93680), "93.680");
        assert_eq!(format_count(999), "999");
        assert_eq!(format_count(1_000_000), "1.000.000");
        assert_eq!(parse_date("2007-11-27"), Some(20071127));
        assert_eq!(parse_date("2026-08-25 10:18:21"), Some(20260825));
        assert_eq!(parse_date(""), None);
        assert_eq!(format_date(Some(20071127)), "27/11/2007");
        assert_eq!(fold("Reintegração ÚNICA"), "reintegracao unica");
    }
}

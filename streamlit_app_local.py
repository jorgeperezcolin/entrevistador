# streamlit_app_local.py
# Ejecuta: streamlit run streamlit_app_local.py
#
# Versión 100% local (sin API) — EXTENDIDA:
# Además del scoring, genera 3 entregables para el entrevistado:
# 1) Benchmark de la innovación (vs “cohorte” configurable)
# 2) Caso de éxito publicable (one-pager)
# 3) Caso de negocio para Consejo (board memo)
#
# Requisitos:
#   pip install streamlit

import json
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple, Optional

import streamlit as st

# ----------------------------
# Config
# ----------------------------
st.set_page_config(page_title="Jurado Local | Las Más Innovadoras", layout="wide")

DIMENSIONS = [
    "Impacto económico y operacional",
    "Evidencia y medición",
    "Gobernanza y riesgo",
    "Adopción y ejecución",
    "Novedad y diseño de la solución",
    "Reusabilidad y aprendizaje",
]

BLOCKS = [
    "Contexto Estratégico",
    "Diseño de la Solución",
    "Impacto Económico y Operativo",
    "Gobernanza y Riesgo",
    "Adopción y Escalamiento",
    "Reusabilidad y Aprendizaje",
]

QUESTIONS: List[Dict[str, str]] = [
    {"block": "Contexto Estratégico", "q": "¿Cuál era el problema estratégico que enfrentaban?"},
    {"block": "Contexto Estratégico", "q": "¿Qué consecuencias tenía no resolverlo?"},
    {"block": "Contexto Estratégico", "q": "¿Cuál era el baseline cuantitativo antes de la intervención? (unidad y fecha)"},
    {"block": "Contexto Estratégico", "q": "¿Qué hipótesis estratégica decidieron validar?"},
    {"block": "Diseño de la Solución", "q": "Describe la solución implementada (qué hicieron, para quién, en qué proceso)."},
    {"block": "Diseño de la Solución", "q": "¿Qué cambió en su modelo operativo? (roles, rituales, SLAs, governance)"},
    {"block": "Diseño de la Solución", "q": "¿Qué tecnología o arquitectura habilitó la solución? (alto nivel)"},
    {"block": "Diseño de la Solución", "q": "¿Qué trade-offs asumieron al diseñarla? (velocidad vs control, costo vs alcance, etc.)"},
    {"block": "Impacto Económico y Operativo", "q": "¿Cuáles fueron los KPIs impactados? (máximo 7)"},
    {"block": "Impacto Económico y Operativo", "q": "Para el KPI #1: baseline, resultado, periodo, método, fuente, responsable del KPI."},
    {"block": "Impacto Económico y Operativo", "q": "Para el KPI #2 (si aplica): baseline, resultado, periodo, método, fuente, responsable."},
    {"block": "Impacto Económico y Operativo", "q": "Para el KPI #3 (si aplica): baseline, resultado, periodo, método, fuente, responsable."},
    {"block": "Impacto Económico y Operativo", "q": "¿Cómo atribuyen el resultado a la intervención? ¿Qué alternativos descartaron?"},
    {"block": "Gobernanza y Riesgo", "q": "¿Qué riesgos identificaron (operativos, reputacionales, ciber, cumplimiento, datos/IA)? (máximo 7)"},
    {"block": "Gobernanza y Riesgo", "q": "¿Qué controles implementaron para esos riesgos? (máximo 7)"},
    {"block": "Gobernanza y Riesgo", "q": "¿Dónde podría fallar la solución? (casos borde / dependencia / degradación)"},
    {"block": "Gobernanza y Riesgo", "q": "¿Qué supuestos críticos podrían invalidar el resultado? (máximo 7)"},
    {"block": "Adopción y Escalamiento", "q": "¿Cuántos usuarios/áreas adoptaron la solución y desde cuándo?"},
    {"block": "Adopción y Escalamiento", "q": "¿Cómo gestionaron el cambio? (capacitaciones, incentivos, soporte)"},
    {"block": "Adopción y Escalamiento", "q": "¿Qué evidencia tienen de uso real? (usuarios activos, frecuencia, auditoría)"},
    {"block": "Adopción y Escalamiento", "q": "¿La solución es escalable? ¿Qué bloqueadores ven y cómo los gestionan?"},
    {"block": "Reusabilidad y Aprendizaje", "q": "¿Qué lecciones son replicables para otras empresas? (máximo 7)"},
    {"block": "Reusabilidad y Aprendizaje", "q": "¿Qué harían diferente si comenzaran hoy? (máximo 7)"},
    {"block": "Reusabilidad y Aprendizaje", "q": "¿Cuál fue el principal error cometido y cómo lo corrigieron?"},
    {"block": "Reusabilidad y Aprendizaje", "q": "¿Cuál fue el insight más valioso descubierto y cómo cambió decisiones posteriores?"},
]

# ----------------------------
# Heurísticas (regex)
# ----------------------------
PATTERNS = {
    "baseline": [
        r"\bbaseline\b", r"\blínea base\b", r"\bantes\b", r"\bprevio\b", r"\bpre[- ]?intervención\b",
        r"\bde\s+\d+(\.\d+)?\s*(%|pts|puntos|días|hrs|horas|mxn|usd|usd\$|\$|mdd|mdp|k|kpi)\b",
    ],
    "period": [
        r"\bperiodo\b", r"\bperíodo\b", r"\bentre\b\s+\d{4}", r"\b\d{4}\b", r"\bQ[1-4]\b",
        r"\b(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\b", r"\bsemana(s)?\b", r"\bmes(es)?\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    ],
    "source": [
        r"\bfuente\b", r"\borigen\b", r"\breporte\b", r"\bdashboard\b", r"\bbi\b", r"\bpower\s*bi\b",
        r"\bsap\b", r"\berp\b", r"\bcrm\b", r"\bsalesforce\b", r"\blog\b", r"\baudit\b", r"\bjira\b",
        r"\bservicenow\b", r"\bconfluence\b",
    ],
    "owner": [
        r"\bowner\b", r"\bresponsable\b", r"\bdata\s*owner\b", r"\bkpi\s*owner\b",
        r"\b(cfo|cio|ceo|cto|pmo)\b", r"\b(finanzas|operaciones|ventas|marketing|datos|analítica)\b",
    ],
    "method": [
        r"\bm[eé]todo\b", r"\bdefinici[oó]n\b", r"\bf[oó]rmula\b", r"\bc[aá]lculo\b",
        r"\bse\s+calcula\b", r"\bdenominador\b", r"\bnumerador\b",
    ],
    "impact": [
        r"\b(ahorro|cost(o|os)|margen|ingreso|ventas|utilidad|ebitda|capex|opex|roi|payback)\b",
        r"\b(\+|\-)\s*\d+(\.\d+)?\s*(%|mxn|usd|\$|mdd|mdp|días|hrs|horas)\b",
        r"\btiempo\b.*\b(ciclo|respuesta|resoluci[oó]n)\b",
    ],
    "governance": [
        r"\bpol[ií]tica\b", r"\bcontrol(es)?\b", r"\bauditor[ií]a\b", r"\bsox\b", r"\biso\b",
        r"\bseguridad\b", r"\bciber\b", r"\bprivacidad\b", r"\bcompliance\b", r"\briesgo(s)?\b",
        r"\bmodelo\s+de\s+gobierno\b", r"\bgovernance\b",
    ],
    "adoption": [
        r"\busuarios?\b", r"\badopci[oó]n\b", r"\buso\b", r"\bactive\b", r"\bfrecuencia\b", r"\bcapacitaci[oó]n\b",
        r"\broll[- ]?out\b", r"\bescalamiento\b", r"\bchange\b", r"\bgestion\s+del\s+cambio\b",
    ],
    "novelty": [
        r"\bnuevo\b", r"\binnovaci[oó]n\b", r"\bautomatizaci[oó]n\b", r"\b(i?a|ml|llm|rag|genai)\b",
        r"\bworkflow\b", r"\borquestaci[oó]n\b", r"\bintegraci[oó]n\b", r"\bapi\b", r"\bproducto\b",
    ],
    "reuse": [
        r"\breplicable\b", r"\breus(a|o)\b", r"\best[aá]ndar\b", r"\bplaybook\b", r"\blecci[oó]n\b",
        r"\banti[- ]?patr[oó]n\b", r"\bgu[ií]a\b", r"\bbuenas\s+pr[aá]cticas\b",
    ],
}

# ----------------------------
# Utilidades
# ----------------------------
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def today_plus(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()

def _has_any(text: str, patterns: List[str]) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t, flags=re.IGNORECASE) for p in patterns)

def evidence_check(text: str) -> Dict[str, bool]:
    return {
        "baseline": _has_any(text, PATTERNS["baseline"]),
        "period": _has_any(text, PATTERNS["period"]),
        "source": _has_any(text, PATTERNS["source"]),
        "owner": _has_any(text, PATTERNS["owner"]),
        "method": _has_any(text, PATTERNS["method"]),
    }

def evidence_gaps_list(chk: Dict[str, bool]) -> List[str]:
    gaps = []
    if not chk["baseline"]:
        gaps.append("Falta baseline explícito (o no detectable).")
    if not chk["period"]:
        gaps.append("Falta periodo/fechas de medición explícitas.")
    if not chk["source"]:
        gaps.append("Falta fuente del dato / sistema origen explícito.")
    if not chk["owner"]:
        gaps.append("Falta owner/responsable del KPI explícito.")
    if not chk["method"]:
        gaps.append("Falta método de cálculo / definición operacional.")
    return gaps[:7]

def score_1_to_5(points: int) -> int:
    if points <= 1:
        return 1
    if points <= 3:
        return 2
    if points <= 6:
        return 3
    if points <= 8:
        return 4
    return 5

# ----------------------------
# Estado / texto
# ----------------------------
def init_state():
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    if "answers" not in st.session_state:
        st.session_state.answers = []
    if "meta" not in st.session_state:
        st.session_state.meta = {
            "empresa": "",
            "categoria": "",
            "entrevistado": "",
            "rol": "",
            "fecha_inicio": now_iso(),
            "notas": "",
        }
    if "round_scores" not in st.session_state:
        st.session_state.round_scores = {"A": None, "B": None, "C": None}
    if "artifacts" not in st.session_state:
        st.session_state.artifacts = {
            "benchmark_md": "",
            "success_case_md": "",
            "board_case_md": "",
            "pack_md": "",
        }
    if "benchmark_config" not in st.session_state:
        # “Cohorte” configurable: medianas por dimensión (1..5) y rango de interpretación.
        st.session_state.benchmark_config = {
            "cohort_name": "Cohorte (referencia)",
            "medians": {d: 3 for d in DIMENSIONS},   # editable por usuario
            "band_width": 1,                        # 1 => +/-1 es “en línea”
        }
    if "publication_config" not in st.session_state:
        st.session_state.publication_config = {
            "public_audience": "CIOs y Consejos (B2B)",
            "anonymize": True,
            "anonymized_name": "Empresa X",
            "vendor_names_allowed": False,
        }

def ensure_answers_length():
    while len(st.session_state.answers) < len(QUESTIONS):
        j = len(st.session_state.answers)
        st.session_state.answers.append({
            "timestamp": now_iso(),
            "block": QUESTIONS[j]["block"],
            "question": QUESTIONS[j]["q"],
            "answer": "",
        })

def upsert_answer(i: int, text: str):
    ensure_answers_length()
    q = QUESTIONS[i]
    st.session_state.answers[i] = {
        "timestamp": now_iso(),
        "block": q["block"],
        "question": q["q"],
        "answer": (text or "").strip(),
    }

def current_question() -> Dict[str, str]:
    return QUESTIONS[st.session_state.idx]

def block_text(block: str, answers: List[Dict[str, Any]]) -> str:
    parts = []
    for a in answers:
        if a["block"] == block and (a["answer"] or "").strip():
            parts.append(a["answer"].strip())
    return "\n".join(parts).strip()

def full_text(answers: List[Dict[str, Any]]) -> str:
    parts = []
    for a in answers:
        if (a["answer"] or "").strip():
            parts.append(f"[{a['block']}] {a['answer'].strip()}")
    return "\n".join(parts).strip()

# ----------------------------
# Scoring determinístico
# ----------------------------
def dim_signals(answers: List[Dict[str, Any]]) -> Dict[str, int]:
    txt_all = full_text(answers)
    impact_block = block_text("Impacto Económico y Operativo", answers)
    gov_block = block_text("Gobernanza y Riesgo", answers)
    adoption_block = block_text("Adopción y Escalamiento", answers)
    design_block = block_text("Diseño de la Solución", answers)
    reuse_block = block_text("Reusabilidad y Aprendizaje", answers)
    context_block = block_text("Contexto Estratégico", answers)

    chk_all = evidence_check(txt_all)
    chk_impact = evidence_check(impact_block)

    pts = {d: 0 for d in DIMENSIONS}

    # 1) Impacto
    if _has_any(impact_block, PATTERNS["impact"]):
        pts[DIMENSIONS[0]] += 4
    if chk_impact["baseline"] and chk_impact["period"]:
        pts[DIMENSIONS[0]] += 2
    if _has_any(context_block, [r"\bconsecuencia(s)?\b", r"\bcosto\s+de\s+no\s+hacer\b", r"\bimpacto\b"]):
        pts[DIMENSIONS[0]] += 1
    if _has_any(impact_block, [r"\batribuci[oó]n\b", r"\bcontrafactual\b", r"\bcontrol\b", r"\bcausal\b", r"\ba\/b\b", r"\bexperimento\b"]):
        pts[DIMENSIONS[0]] += 3

    # 2) Evidencia y medición
    pts[DIMENSIONS[1]] += sum(1 for v in chk_all.values() if v)  # 0..5
    if impact_block and all(chk_impact.values()):
        pts[DIMENSIONS[1]] += 4
    elif impact_block:
        pts[DIMENSIONS[1]] += 1

    # 3) Gobernanza y riesgo
    if _has_any(gov_block, PATTERNS["governance"]):
        pts[DIMENSIONS[2]] += 6
    if _has_any(gov_block, [r"\bfall(a|o)\b", r"\bcasos?\s+borde\b", r"\bdegradaci[oó]n\b", r"\bmonitor(eo|ing)\b"]):
        pts[DIMENSIONS[2]] += 2
    if _has_any(gov_block, [r"\bresponsable\b", r"\brol\b", r"\bcomit[eé]\b"]):
        pts[DIMENSIONS[2]] += 2

    # 4) Adopción y ejecución
    if _has_any(adoption_block, PATTERNS["adoption"]):
        pts[DIMENSIONS[3]] += 6
    if _has_any(adoption_block, [r"\busuarios?\s+activos\b", r"\bDAU\b", r"\bMAU\b", r"\buso\s+real\b"]):
        pts[DIMENSIONS[3]] += 2
    if _has_any(design_block, [r"\bSLA\b", r"\britual(es)?\b", r"\boperating\s+model\b", r"\bmodelo\s+operativo\b"]):
        pts[DIMENSIONS[3]] += 2

    # 5) Novedad y diseño
    if _has_any(design_block, PATTERNS["novelty"]):
        pts[DIMENSIONS[4]] += 5
    if _has_any(design_block, [r"\barquitectura\b", r"\bcomponent(es)?\b", r"\bintegraci[oó]n\b", r"\bapi\b"]):
        pts[DIMENSIONS[4]] += 3
    if _has_any(design_block, [r"\btrade[- ]?off\b", r"\bcompensaci[oó]n\b", r"\bdecisi[oó]n\s+de\s+dise[nñ]o\b"]):
        pts[DIMENSIONS[4]] += 2

    # 6) Reusabilidad y aprendizaje
    if _has_any(reuse_block, PATTERNS["reuse"]):
        pts[DIMENSIONS[5]] += 6
    if _has_any(reuse_block, [r"\berror\b", r"\blecci[oó]n\b", r"\bqué\s+har[ií]an\s+diferente\b"]):
        pts[DIMENSIONS[5]] += 2
    if _has_any(reuse_block, [r"\bplaybook\b", r"\best[aá]ndar\b", r"\bplantilla\b"]):
        pts[DIMENSIONS[5]] += 2

    return pts

def local_evidence_used(dim: str, answers: List[Dict[str, Any]]) -> str:
    mapping = {
        DIMENSIONS[0]: ["Impacto Económico y Operativo", "Contexto Estratégico"],
        DIMENSIONS[1]: ["Impacto Económico y Operativo"],
        DIMENSIONS[2]: ["Gobernanza y Riesgo"],
        DIMENSIONS[3]: ["Adopción y Escalamiento", "Diseño de la Solución"],
        DIMENSIONS[4]: ["Diseño de la Solución"],
        DIMENSIONS[5]: ["Reusabilidad y Aprendizaje"],
    }
    blocks = mapping.get(dim, [])
    present = [b for b in blocks if block_text(b, answers)]
    return ("Evidencia detectada en: " + ", ".join(present[:7]) + ".") if present else "No hay evidencia textual suficiente en los bloques esperados."

def local_rationale(dim: str, answers: List[Dict[str, Any]], pts: int, score: int) -> str:
    impact_block = block_text("Impacto Económico y Operativo", answers)
    gov_block = block_text("Gobernanza y Riesgo", answers)
    adoption_block = block_text("Adopción y Escalamiento", answers)
    design_block = block_text("Diseño de la Solución", answers)
    reuse_block = block_text("Reusabilidad y Aprendizaje", answers)
    all_txt = full_text(answers)

    chk_all = evidence_check(all_txt)
    chk_imp = evidence_check(impact_block)

    if dim == DIMENSIONS[0]:
        if not impact_block:
            return "No se documenta impacto cuantitativo en el bloque de impacto."
        if _has_any(impact_block, PATTERNS["impact"]) and chk_imp["baseline"] and chk_imp["period"]:
            return "Se reportan resultados y comparativo temporal; atribución depende del nivel de evidencia explícita."
        return "Hay referencias a impacto, pero falta comparativo temporal o atribución explícita."

    if dim == DIMENSIONS[1]:
        if not impact_block:
            return "No se observa evidencia cerrada en el bloque de impacto; baja trazabilidad de resultados."
        if all(chk_imp.values()):
            return "La evidencia cierra en impacto: baseline, periodo, fuente, owner y método."
        return "El bloque de impacto no cierra evidencia completa; trazabilidad parcial."

    if dim == DIMENSIONS[2]:
        if not gov_block:
            return "No se documentan riesgos y controles; governance no explícito."
        if _has_any(gov_block, PATTERNS["governance"]) and _has_any(gov_block, [r"\bcontrol\b", r"\bmitigaci[oó]n\b", r"\bauditor[ií]a\b"]):
            return "Se describen riesgos y controles; hay enfoque de mitigación y operación."
        return "Se mencionan riesgos o controles de forma general; falta especificidad operacional."

    if dim == DIMENSIONS[3]:
        if not adoption_block:
            return "No se documenta adopción/uso; ejecución no demostrada."
        if _has_any(adoption_block, [r"\busuarios?\b", r"\buso\b"]) and _has_any(adoption_block, [r"\bfrecuencia\b", r"\bactivos\b", r"\broll[- ]?out\b"]):
            return "Se evidencian mecanismos de adopción y señales de uso."
        return "Hay narrativa de cambio, pero poca evidencia de uso real o métricas de adopción."

    if dim == DIMENSIONS[4]:
        if not design_block:
            return "No se describe diseño/arquitectura; falta detalle de solución."
        if _has_any(design_block, PATTERNS["novelty"]) and _has_any(design_block, [r"\barquitectura\b", r"\bintegraci[oó]n\b"]):
            return "Se describe solución con elementos técnicos/arquitectónicos; diferenciación razonable."
        return "La solución se describe a alto nivel; falta detalle de arquitectura o decisiones de diseño."

    if dim == DIMENSIONS[5]:
        if not reuse_block:
            return "No se documentan aprendizajes o reusabilidad; transferencia no explicitada."
        if _has_any(reuse_block, PATTERNS["reuse"]) and _has_any(reuse_block, [r"\berror\b", r"\blecci[oó]n\b"]):
            return "Se documentan lecciones y condiciones de replicabilidad; aprendizaje explícito."
        return "Se mencionan aprendizajes, pero con baja estructuración o sin criterios claros de replicabilidad."

    return f"Puntaje derivado de señales textuales (pts={pts}) y completitud de evidencia (score={score})."

def confidence_from_evidence(answers: List[Dict[str, Any]]) -> float:
    all_txt = full_text(answers)
    imp_txt = block_text("Impacto Económico y Operativo", answers)
    chk_all = evidence_check(all_txt)
    chk_imp = evidence_check(imp_txt) if imp_txt else {k: False for k in ["baseline", "period", "source", "owner", "method"]}
    base = sum(1 for v in chk_all.values() if v) / 5.0
    imp = sum(1 for v in chk_imp.values() if v) / 5.0 if imp_txt else 0.0
    return round(0.6 * base + 0.4 * imp, 2)

def build_dimension_scoring(answers: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    pts = dim_signals(answers)
    dims = []
    for name in DIMENSIONS:
        s = score_1_to_5(pts[name])
        dims.append({
            "name": name,
            "score": s,
            "rationale": local_rationale(name, answers, pts[name], s),
            "evidence_used": local_evidence_used(name, answers),
        })
    overall = round(sum(d["score"] for d in dims) / 6.0, 2)
    return dims, overall

def strengths_list(dims: List[Dict[str, Any]]) -> List[str]:
    strengths = []
    for d in sorted(dims, key=lambda x: x["score"], reverse=True):
        if d["score"] >= 4:
            strengths.append(f"{d['name']} (score {d['score']}/5) con evidencia en bloques relevantes.")
    if not strengths:
        strengths.append("No destacan fortalezas claras por evidencia; priorizar cierre de datos y resultados.")
    return strengths[:7]

def clarifying_questions(answers: List[Dict[str, Any]]) -> List[str]:
    imp_txt = block_text("Impacto Económico y Operativo", answers)
    chk = evidence_check(imp_txt if imp_txt else full_text(answers))

    qs = []
    if not chk["baseline"]:
        qs.append("Para el KPI principal, ¿cuál era el baseline exacto (valor, unidad) y en qué fecha se midió?")
    if not chk["period"]:
        qs.append("¿Cuál es el periodo exacto de medición (fecha inicio/fin) para el KPI principal?")
    if not chk["source"]:
        qs.append("¿Cuál es la fuente del dato (sistema/reporte) y cómo se extrae para auditoría?")
    if not chk["owner"]:
        qs.append("¿Quién es el owner responsable del KPI y cómo valida oficialmente los números?")
    if not chk["method"]:
        qs.append("¿Cuál es la definición operacional y fórmula del KPI (numerador/denominador, reglas de inclusión)?")
    if not _has_any(imp_txt, [r"\batribuci[oó]n\b", r"\bcontrol\b", r"\ba\/b\b", r"\bcontrafactual\b", r"\bcausal\b"]):
        qs.append("¿Qué evidencia tienen para atribuir el cambio al programa (comparativo, control, antes/después con supuestos explícitos)?")
    adp = block_text("Adopción y Escalamiento", answers)
    if not _has_any(adp, [r"\busuarios?\b", r"\bactivos\b", r"\bfrecuencia\b", r"\buso\b"]):
        qs.append("¿Qué métricas de uso real (usuarios activos, frecuencia, cumplimiento) demuestran adopción sostenida?")
    return qs[:7]

def decision_registry_local(answers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    dr = []
    year = datetime.now().year
    imp = block_text("Impacto Económico y Operativo", answers)
    chk_imp = evidence_check(imp) if imp else {k: False for k in ["baseline", "period", "source", "owner", "method"]}

    def add(i: int, decision: str, rationale: str, evidence_required: str, owner: str, due: str):
        dr.append({
            "decision_id": f"DR-{year}-INNO-{i:03d}",
            "decision": decision,
            "rationale": rationale,
            "evidence_required": evidence_required,
            "owner": owner,
            "due_date": due,
        })

    i = 1
    if not (chk_imp["baseline"] and chk_imp["period"]):
        add(i, "Cerrar baseline y periodo del KPI principal",
            "Sin comparativo temporal el impacto no es defendible ante jurado.",
            "Baseline (valor/unidad/fecha) + periodo (inicio/fin) + resultado actual.",
            "CFO / Data Owner", today_plus(7)); i += 1
    if not chk_imp["source"]:
        add(i, "Evidenciar fuente y trazabilidad del KPI",
            "Sin sistema origen no hay auditabilidad mínima.",
            "Sistema origen, reporte, ubicación del dashboard y evidencia adjunta.",
            "CIO / BI Lead", today_plus(7)); i += 1
    if not chk_imp["method"]:
        add(i, "Formalizar método de cálculo del KPI",
            "Definiciones ambiguas generan score bajo en medición.",
            "Definición operacional y fórmula; reglas de inclusión/exclusión.",
            "PMO / Data Owner", today_plus(10)); i += 1
    if not _has_any(imp, [r"\batribuci[oó]n\b", r"\bcontrol\b", r"\ba\/b\b", r"\bcontrafactual\b", r"\bcausal\b"]):
        add(i, "Documentar lógica de atribución del impacto",
            "Sin atribución, el impacto puede ser ruido o factor externo.",
            "Comparativo/control o explicación causal con supuestos explícitos.",
            "Sponsor del caso", today_plus(10)); i += 1

    gov = block_text("Gobernanza y Riesgo", answers)
    if gov and not _has_any(gov, [r"\bcontrol\b", r"\bmitigaci[oó]n\b", r"\bauditor[ií]a\b"]):
        add(i, "Especificar controles para riesgos identificados",
            "Mencionar riesgos sin controles reduce credibilidad.",
            "Controles, frecuencia, owner del control, evidencia de ejecución.",
            "Risk / Compliance", today_plus(14)); i += 1

    adp = block_text("Adopción y Escalamiento", answers)
    if adp and not _has_any(adp, [r"\busuarios?\b", r"\bactivos\b", r"\bfrecuencia\b", r"\buso\b"]):
        add(i, "Aportar métricas de adopción y uso real",
            "Adopción declarativa sin métricas no sostiene escalamiento.",
            "Usuarios activos, frecuencia, cohortes, evidencia de uso sostenido.",
            "CIO / Change Lead", today_plus(14)); i += 1

    if not dr:
        add(1, "Caso listo para validación editorial",
            "No se detectan vacíos críticos por heurística local.",
            "Paquete de evidencia y anexos para publicación de claims.",
            "Equipo de Premio", today_plus(7))

    return dr[:7]

def local_scoring_round(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    dims, overall = build_dimension_scoring(answers)
    conf = confidence_from_evidence(answers)
    gaps = evidence_gaps_list(evidence_check(full_text(answers)))
    qs = clarifying_questions(answers)
    strengths = strengths_list(dims)
    dr = decision_registry_local(answers)

    return {
        "overall_score": overall,
        "confidence": conf,
        "dimensions": dims,
        "strengths": strengths,
        "evidence_gaps": gaps,
        "clarifying_questions": qs,
        "decision_registry": dr,
        "notes": "Scoring determinístico local basado en heurísticas de texto y checklist de evidencia (sin API).",
        "generated_at": now_iso(),
    }

# ----------------------------
# Benchmark + Caso de éxito + Caso Consejo (local)
# ----------------------------
def benchmark_from_scores(
    score_obj: Dict[str, Any],
    cohort_name: str,
    medians: Dict[str, int],
    band_width: int,
) -> Dict[str, Any]:
    """
    Benchmark simple vs “mediana de cohorte” configurable:
    - Above / In-line / Below para cada dimensión
    - Gap prioritario: las 2 dimensiones con peor delta (máx 2) -> se reportan en texto (sin listas >7)
    """
    dims = score_obj["dimensions"]
    rows = []
    deltas = []
    for d in dims:
        m = int(medians.get(d["name"], 3))
        s = int(d["score"])
        delta = s - m
        deltas.append((d["name"], delta))
        if delta >= band_width:
            status = "Arriba de cohorte"
        elif delta <= -band_width:
            status = "Abajo de cohorte"
        else:
            status = "En línea con cohorte"
        rows.append({"dimension": d["name"], "score": s, "median": m, "delta": delta, "status": status})

    deltas_sorted = sorted(deltas, key=lambda x: x[1])
    priority_gaps = [x[0] for x in deltas_sorted[:2]]  # máx 2

    return {
        "cohort_name": cohort_name,
        "band_width": band_width,
        "rows": rows,
        "priority_gaps": priority_gaps,
    }

def render_benchmark_md(meta: Dict[str, Any], score_obj: Dict[str, Any], bm: Dict[str, Any]) -> str:
    md = []
    md.append("# Benchmark de Innovación (para entrevistado)\n")
    md.append(f"**Empresa:** {meta.get('empresa') or '—'}  ")
    md.append(f"**Cohorte:** {bm['cohort_name']}  ")
    md.append(f"**Fecha:** {now_iso()}  ")
    md.append("\n---\n")
    md.append(f"**Score global (local):** {score_obj.get('overall_score','—')}/5  ")
    md.append(f"**Confianza (local):** {score_obj.get('confidence','—')}\n")
    md.append("\n---\n")
    md.append("## Comparativo por dimensión\n")
    md.append("| Dimensión | Score | Mediana cohorte | Delta | Estatus |")
    md.append("|---|---:|---:|---:|---|")
    for r in bm["rows"]:
        md.append(f"| {r['dimension']} | {r['score']} | {r['median']} | {r['delta']} | {r['status']} |")
    md.append("\n---\n")
    md.append("## Lectura ejecutiva\n")
    if bm["priority_gaps"]:
        md.append(f"**Brechas prioritarias (para subir benchmark):** {', '.join(bm['priority_gaps'])}.")
    else:
        md.append("No se detectan brechas prioritarias contra la mediana de cohorte.")
    md.append("\n")
    md.append("**Nota metodológica:** benchmark basado en scoring local heurístico; úsese como guía de mejora y preparación de evidencia.")
    return "\n".join(md).strip()

def _maybe_anonymize(meta: Dict[str, Any], pub_cfg: Dict[str, Any]) -> str:
    if pub_cfg.get("anonymize"):
        return pub_cfg.get("anonymized_name") or "Empresa X"
    return meta.get("empresa") or "—"

def render_success_case_md(meta: Dict[str, Any], answers: List[Dict[str, Any]], pub_cfg: Dict[str, Any]) -> str:
    """
    One-pager publicable: evita claims frágiles marcando placeholders si falta evidencia.
    """
    company = _maybe_anonymize(meta, pub_cfg)
    problem = block_text("Contexto Estratégico", answers) or "—"
    solution = block_text("Diseño de la Solución", answers) or "—"
    impact = block_text("Impacto Económico y Operativo", answers) or "—"
    adoption = block_text("Adopción y Escalamiento", answers) or "—"
    governance = block_text("Gobernanza y Riesgo", answers) or "—"
    learnings = block_text("Reusabilidad y Aprendizaje", answers) or "—"

    # Gate editorial: si falta evidencia mínima global, insertar aviso (sin listas largas)
    gaps = evidence_gaps_list(evidence_check(full_text(answers)))

    md = []
    md.append("# Caso de Éxito (para publicación)\n")
    md.append(f"**Empresa:** {company}  ")
    md.append(f"**Audiencia:** {pub_cfg.get('public_audience','—')}  ")
    md.append(f"**Fecha:** {now_iso()}  ")
    md.append("\n---\n")

    if gaps:
        md.append("**Aviso editorial:** algunos resultados requieren completar evidencia (baseline/periodo/fuente/owner/método) antes de publicar claims numéricos.\n")

    md.append("## Situación\n")
    md.append(problem)
    md.append("\n## Enfoque\n")
    md.append(solution)
    md.append("\n## Resultados\n")
    md.append(impact)
    md.append("\n## Adopción\n")
    md.append(adoption)
    md.append("\n## Gobernanza\n")
    md.append(governance)
    md.append("\n## Lecciones\n")
    md.append(learnings)
    md.append("\n---\n")
    md.append("**Cita sugerida (aprobación interna):** “La innovación no fue un proyecto aislado; fue un cambio de operating model con KPIs y governance.”")
    return "\n".join(md).strip()

def render_board_case_md(meta: Dict[str, Any], answers: List[Dict[str, Any]], score_obj: Dict[str, Any]) -> str:
    """
    Caso de negocio para Consejo: memo ejecutivo con ask, economics, riesgos y KPIs.
    Sin inventar cifras: si faltan, se deja “(pendiente de evidencia)”.
    """
    empresa = meta.get("empresa") or "—"
    role = meta.get("rol") or "—"
    entrevistado = meta.get("entrevistado") or "—"

    context = block_text("Contexto Estratégico", answers) or "—"
    solution = block_text("Diseño de la Solución", answers) or "—"
    impact = block_text("Impacto Económico y Operativo", answers) or "—"
    risks = block_text("Gobernanza y Riesgo", answers) or "—"
    adoption = block_text("Adopción y Escalamiento", answers) or "—"

    imp_chk = evidence_check(block_text("Impacto Económico y Operativo", answers))
    missing_any = any(not v for v in imp_chk.values())

    md = []
    md.append("# Caso de Negocio para Consejo (Board Memo)\n")
    md.append(f"**Empresa:** {empresa}  ")
    md.append(f"**Sponsor/Entrevistado:** {entrevistado} ({role})  ")
    md.append(f"**Fecha:** {now_iso()}  ")
    md.append("\n---\n")

    md.append("## 1) Decisión solicitada al Consejo\n")
    md.append("Aprobar la continuidad/escalamiento de la iniciativa bajo un marco de KPIs, governance y evidencia verificable.")
    md.append("\n## 2) Problema estratégico\n")
    md.append(context)
    md.append("\n## 3) Intervención y operating model\n")
    md.append(solution)
    md.append("\n## 4) Caso económico\n")
    if missing_any:
        md.append("**Impacto reportado:** (pendiente de evidencia completa para publicar cifras: baseline/periodo/fuente/owner/método).")
    else:
        md.append("**Impacto reportado:** evidencia completa detectada para KPI(s) principales.")
    md.append("\n**Detalle (según entrevista):**\n")
    md.append(impact)

    md.append("\n## 5) Riesgos, controles y supuestos\n")
    md.append(risks)

    md.append("\n## 6) Adopción y escalabilidad\n")
    md.append(adoption)

    md.append("\n## 7) KPIs de control y governance\n")
    md.append("Recomendación: formalizar KPIs y owners en un registro y revisar mensualmente en comité ejecutivo.")

    md.append("\n---\n")
    md.append("## Apéndice — Scorecard interno (local)\n")
    md.append(f"**Score global:** {score_obj.get('overall_score','—')}/5 | **Confianza:** {score_obj.get('confidence','—')}\n")
    md.append("| Dimensión | Score | Observación |")
    md.append("|---|---:|---|")
    for d in score_obj.get("dimensions", [])[:6]:
        md.append(f"| {d['name']} | {d['score']} | {d['rationale']} |")

    return "\n".join(md).strip()

def build_pack_md(meta: Dict[str, Any], answers: List[Dict[str, Any]], score_obj: Dict[str, Any], bm_md: str, success_md: str, board_md: str) -> str:
    md = []
    md.append("# Entregables — Innovación (para entrevistado)\n")
    md.append(f"**Empresa:** {meta.get('empresa') or '—'}  ")
    md.append(f"**Fecha:** {now_iso()}  ")
    md.append("\n---\n")
    md.append("## 1) Benchmark\n")
    md.append(bm_md)
    md.append("\n---\n## 2) Caso de éxito publicable\n")
    md.append(success_md)
    md.append("\n---\n## 3) Caso de negocio para Consejo\n")
    md.append(board_md)
    return "\n".join(md).strip()

# ----------------------------
# Dispersión (A/B/C)
# ----------------------------
def dispersion_report(round_scores: Dict[str, Optional[Dict[str, Any]]]) -> Tuple[Dict[str, Any], List[str]]:
    rounds = [r for r in ["A", "B", "C"] if round_scores.get(r)]
    report: Dict[str, Any] = {"overall_range": None, "by_dimension": []}
    flags: List[str] = []
    if not rounds:
        return report, flags

    overalls = [round_scores[r]["overall_score"] for r in rounds]
    report["overall_range"] = float(max(overalls) - min(overalls))

    for i, name in enumerate(DIMENSIONS):
        vals = {r: round_scores[r]["dimensions"][i]["score"] for r in rounds}
        rng = max(vals.values()) - min(vals.values())
        report["by_dimension"].append({"name": name, "scores": vals, "range": rng})
        if rng >= 2 and len(flags) < 7:
            flags.append(f"Dispersión alta en '{name}' (rango {rng}). Revisar evidencia y calibrar anclas.")
    return report, flags

# ----------------------------
# UI
# ----------------------------
init_state()
ensure_answers_length()

st.title("Modo Jurado — 100% local (sin API) + Entregables al entrevistado")
st.caption("Además del score, genera benchmark, caso de éxito publicable y caso de negocio para Consejo.")

with st.expander("Metadatos", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.meta["empresa"] = st.text_input("Empresa", value=st.session_state.meta["empresa"])
        st.session_state.meta["categoria"] = st.text_input("Categoría", value=st.session_state.meta["categoria"])
    with c2:
        st.session_state.meta["entrevistado"] = st.text_input("Entrevistado", value=st.session_state.meta["entrevistado"])
        st.session_state.meta["rol"] = st.text_input("Rol", value=st.session_state.meta["rol"])
    with c3:
        st.session_state.meta["notas"] = st.text_area("Notas (opcional)", value=st.session_state.meta["notas"], height=90)

with st.expander("Benchmark (configurable)", expanded=False):
    st.session_state.benchmark_config["cohort_name"] = st.text_input(
        "Nombre de cohorte de referencia",
        value=st.session_state.benchmark_config.get("cohort_name", "Cohorte (referencia)"),
    )
    st.session_state.benchmark_config["band_width"] = st.slider(
        "Ancho de banda para estatus (± puntos vs mediana)",
        min_value=1,
        max_value=2,
        value=int(st.session_state.benchmark_config.get("band_width", 1)),
    )
    st.markdown("**Mediana por dimensión (1–5)**")
    for d in DIMENSIONS:
        st.session_state.benchmark_config["medians"][d] = st.slider(
            d, min_value=1, max_value=5, value=int(st.session_state.benchmark_config["medians"].get(d, 3))
        )

with st.expander("Publicación (caso de éxito)", expanded=False):
    st.session_state.publication_config["public_audience"] = st.text_input(
        "Audiencia objetivo",
        value=st.session_state.publication_config.get("public_audience", "CIOs y Consejos (B2B)"),
    )
    st.session_state.publication_config["anonymize"] = st.checkbox(
        "Anonimizar nombre de la empresa en el caso de éxito",
        value=bool(st.session_state.publication_config.get("anonymize", True)),
    )
    st.session_state.publication_config["anonymized_name"] = st.text_input(
        "Nombre anonimizado",
        value=st.session_state.publication_config.get("anonymized_name", "Empresa X"),
    )
    st.session_state.publication_config["vendor_names_allowed"] = st.checkbox(
        "Permitir mencionar vendors/marcas en el caso publicable",
        value=bool(st.session_state.publication_config.get("vendor_names_allowed", False)),
    )

st.divider()
left, right = st.columns([2, 1])

with left:
    st.subheader("Entrevista (captura)")
    st.write(f"**Progreso:** {st.session_state.idx + 1} / {len(QUESTIONS)}")

    q = current_question()
    st.markdown(f"### Bloque: {q['block']}")
    st.markdown(f"**Pregunta:** {q['q']}")

    default_answer = st.session_state.answers[st.session_state.idx]["answer"]
    answer = st.text_area("Respuesta", value=default_answer, height=170)

    # Checklist local (sobre respuesta actual)
    live_chk = evidence_check(answer)
    live_gaps = evidence_gaps_list(live_chk)
    if live_gaps:
        st.warning("Checklist evidencia (sobre esta respuesta)")
        st.write("\n".join([f"- {g}" for g in live_gaps[:7]]))

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        back = st.button("⬅️ Anterior", use_container_width=True, disabled=(st.session_state.idx == 0))
    with b2:
        save = st.button("💾 Guardar", use_container_width=True)
    with b3:
        nxt = st.button("➡️ Siguiente", use_container_width=True, disabled=(st.session_state.idx >= len(QUESTIONS) - 1))
    with b4:
        reset = st.button("🧹 Reiniciar", use_container_width=True)

    if back:
        upsert_answer(st.session_state.idx, answer)
        st.session_state.idx = max(0, st.session_state.idx - 1)
        st.rerun()

    if save:
        upsert_answer(st.session_state.idx, answer)
        st.success("Guardado.")
        st.rerun()

    if nxt:
        upsert_answer(st.session_state.idx, answer)
        st.session_state.idx += 1
        st.rerun()

    if reset:
        st.session_state.idx = 0
        st.session_state.answers = []
        st.session_state.round_scores = {"A": None, "B": None, "C": None}
        st.session_state.artifacts = {"benchmark_md": "", "success_case_md": "", "board_case_md": "", "pack_md": ""}
        st.session_state.meta["fecha_inicio"] = now_iso()
        ensure_answers_length()
        st.rerun()

with right:
    st.subheader("Scoring local + Entregables")

    round_id = st.selectbox("Ronda/Jurado (para scoring)", ["A", "B", "C"], index=0)

    if st.button("⚖️ Correr scoring local (esta ronda)", use_container_width=True):
        upsert_answer(st.session_state.idx, answer)
        ensure_answers_length()
        st.session_state.round_scores[round_id] = local_scoring_round(st.session_state.answers)
        st.success(f"Scoring local generado (ronda {round_id}).")

    rs = st.session_state.round_scores.get(round_id)
    if rs:
        st.metric("Score global", f"{rs['overall_score']}/5")
        st.metric("Confianza", f"{rs['confidence']}")
        st.markdown("### Por dimensión")
        for d in rs["dimensions"][:6]:
            st.write(f"- **{d['name']}**: {d['score']}/5")

    st.divider()
    st.markdown("### Control de dispersión (A/B/C)")
    report, flags = dispersion_report(st.session_state.round_scores)
    if report.get("overall_range") is None:
        st.info("Genera scoring en al menos una ronda para ver dispersión.")
    else:
        st.write(f"**Rango overall:** {report['overall_range']}")
        for row in report["by_dimension"][:6]:
            st.write(f"- {row['name']}: {row['scores']} | rango={row['range']}")
        if flags:
            st.warning("Banderas (máx 7)")
            st.write("\n".join([f"- {f}" for f in flags[:7]]))

    st.divider()
    st.markdown("### Entregables al entrevistado (MD)")
    st.caption("Se generan con base en las respuestas y el scoring de la ronda seleccionada.")

    can_generate = rs is not None

    if st.button("📌 Generar Benchmark + Caso Éxito + Caso Consejo", use_container_width=True, disabled=not can_generate):
        upsert_answer(st.session_state.idx, answer)
        ensure_answers_length()

        bm = benchmark_from_scores(
            score_obj=rs,
            cohort_name=st.session_state.benchmark_config["cohort_name"],
            medians=st.session_state.benchmark_config["medians"],
            band_width=int(st.session_state.benchmark_config["band_width"]),
        )
        bm_md = render_benchmark_md(st.session_state.meta, rs, bm)
        success_md = render_success_case_md(st.session_state.meta, st.session_state.answers, st.session_state.publication_config)
        board_md = render_board_case_md(st.session_state.meta, st.session_state.answers, rs)
        pack_md = build_pack_md(st.session_state.meta, st.session_state.answers, rs, bm_md, success_md, board_md)

        st.session_state.artifacts["benchmark_md"] = bm_md
        st.session_state.artifacts["success_case_md"] = success_md
        st.session_state.artifacts["board_case_md"] = board_md
        st.session_state.artifacts["pack_md"] = pack_md
        st.success("Entregables generados.")

    # Descargas
    if st.session_state.artifacts.get("benchmark_md"):
        st.download_button(
            "⬇️ Descargar Benchmark (MD)",
            data=st.session_state.artifacts["benchmark_md"].encode("utf-8"),
            file_name=f"Benchmark_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Descargar Caso de Éxito (MD)",
            data=st.session_state.artifacts["success_case_md"].encode("utf-8"),
            file_name=f"Caso_Exito_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Descargar Caso Consejo (MD)",
            data=st.session_state.artifacts["board_case_md"].encode("utf-8"),
            file_name=f"Caso_Consejo_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Descargar Pack Completo (MD)",
            data=st.session_state.artifacts["pack_md"].encode("utf-8"),
            file_name=f"Pack_Entrevistado_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        with st.expander("Vista previa (Pack completo)", expanded=False):
            st.text_area("Pack", value=st.session_state.artifacts["pack_md"], height=260)

    st.divider()
    payload = {
        "meta": st.session_state.meta,
        "answers": st.session_state.answers,
        "round_scores": st.session_state.round_scores,
        "benchmark_config": st.session_state.benchmark_config,
        "publication_config": st.session_state.publication_config,
        "artifacts": st.session_state.artifacts,
        "exported_at": now_iso(),
        "mode": "local_no_api_with_deliverables",
    }
    st.download_button(
        "⬇️ Descargar todo (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"Local_All_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()
st.caption("Nota: sin API, benchmark y narrativas se basan en heurísticas y en el contenido provisto; para publicación externa, cerrar evidencia antes de fijar cifras.")

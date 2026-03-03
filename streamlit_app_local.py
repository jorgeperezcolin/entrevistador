# streamlit_app_local.py
# Ejecuta: streamlit run streamlit_app_local.py
#
# Versión 100% local (sin API):
# - Entrevista secuencial
# - Checklist de evidencia (baseline, periodo, fuente, owner, método)
# - Scoring automático determinístico (1–5) por 6 dimensiones
# - Control de dispersión por rondas A/B/C (si quieres 3 jurados, capturas 3 scorings locales)
# - Decision Registry local (máx 7)
# - Exportables: JSON + Pack ejecutivo (MD)

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
# Helpers
# ----------------------------
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def today_plus(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()

def init_state():
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    if "answers" not in st.session_state:
        st.session_state.answers = []  # aligned to QUESTIONS
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
        # dict round -> final score obj (local)
        st.session_state.round_scores = {"A": None, "B": None, "C": None}
    if "pack_md" not in st.session_state:
        st.session_state.pack_md = ""

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
        if a["block"] == block:
            if a["answer"].strip():
                parts.append(a["answer"].strip())
    return "\n".join(parts).strip()

def full_text(answers: List[Dict[str, Any]]) -> str:
    parts = []
    for a in answers:
        if a["answer"].strip():
            parts.append(f"[{a['block']}] {a['answer'].strip()}")
    return "\n".join(parts).strip()

# ----------------------------
# Deterministic evidence & scoring
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
        r"\braci\b", r"\bmodelo\s+de\s+gobierno\b", r"\bgovernance\b",
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
    # Mapea puntos (0..10) -> 1..5 de forma estable
    if points <= 1:
        return 1
    if points <= 3:
        return 2
    if points <= 6:
        return 3
    if points <= 8:
        return 4
    return 5

def dim_signals(answers: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Señales determinísticas (puntos) por dimensión a partir de:
    - presencia de evidencia
    - presencia de términos/indicadores
    - completitud en bloque de impacto
    """
    ensure = answers  # already ensured outside

    txt_all = full_text(ensure)
    impact_block = block_text("Impacto Económico y Operativo", ensure)
    gov_block = block_text("Gobernanza y Riesgo", ensure)
    adoption_block = block_text("Adopción y Escalamiento", ensure)
    design_block = block_text("Diseño de la Solución", ensure)
    reuse_block = block_text("Reusabilidad y Aprendizaje", ensure)
    context_block = block_text("Contexto Estratégico", ensure)

    chk_all = evidence_check(txt_all)
    chk_impact = evidence_check(impact_block)

    # Puntos base por dimensión (0..10)
    pts = {d: 0 for d in DIMENSIONS}

    # Impacto económico y operacional
    if _has_any(impact_block, PATTERNS["impact"]):
        pts[DIMENSIONS[0]] += 4
    if chk_impact["baseline"] and chk_impact["period"]:
        pts[DIMENSIONS[0]] += 2
    if _has_any(context_block, [r"\bconsecuencia(s)?\b", r"\bcosto\s+de\s+no\s+hacer\b", r"\bimpacto\b"]):
        pts[DIMENSIONS[0]] += 1
    if _has_any(impact_block, [r"\batribuci[oó]n\b", r"\bcontrafactual\b", r"\bcontrol\b", r"\bdi[dD]\b", r"\ba\/b\b", r"\bexperimento\b"]):
        pts[DIMENSIONS[0]] += 3

    # Evidencia y medición
    pts[DIMENSIONS[1]] += sum(1 for k, v in chk_all.items() if v)  # 0..5
    if chk_impact["baseline"] and chk_impact["period"] and chk_impact["source"] and chk_impact["owner"] and chk_impact["method"]:
        pts[DIMENSIONS[1]] += 4  # evidencia “cerrada” en impacto
    else:
        # penalización si el bloque de impacto está pero incompleto
        if impact_block.strip():
            pts[DIMENSIONS[1]] += 1  # algo hay, pero no cierra

    # Gobernanza y riesgo
    if _has_any(gov_block, PATTERNS["governance"]):
        pts[DIMENSIONS[2]] += 6
    if _has_any(gov_block, [r"\bfall(a|o)\b", r"\bcasos?\s+borde\b", r"\bdegradaci[oó]n\b", r"\bmonitor(eo|ing)\b"]):
        pts[DIMENSIONS[2]] += 2
    if _has_any(gov_block, [r"\bresponsable\b", r"\brol\b", r"\bcomit[eé]\b"]):
        pts[DIMENSIONS[2]] += 2

    # Adopción y ejecución
    if _has_any(adoption_block, PATTERNS["adoption"]):
        pts[DIMENSIONS[3]] += 6
    if _has_any(adoption_block, [r"\busuarios?\s+activos\b", r"\bDAU\b", r"\bMAU\b", r"\buso\s+real\b"]):
        pts[DIMENSIONS[3]] += 2
    if _has_any(design_block, [r"\bSLA\b", r"\britual(es)?\b", r"\boperating\s+model\b", r"\bmodelo\s+operativo\b"]):
        pts[DIMENSIONS[3]] += 2

    # Novedad y diseño de la solución
    if _has_any(design_block, PATTERNS["novelty"]):
        pts[DIMENSIONS[4]] += 5
    if _has_any(design_block, [r"\barquitectura\b", r"\bcomponent(es)?\b", r"\bintegraci[oó]n\b", r"\bapi\b"]):
        pts[DIMENSIONS[4]] += 3
    if _has_any(design_block, [r"\btrade[- ]?off\b", r"\bcompensaci[oó]n\b", r"\bdecisi[oó]n\s+de\s+dise[nñ]o\b"]):
        pts[DIMENSIONS[4]] += 2

    # Reusabilidad y aprendizaje
    if _has_any(reuse_block, PATTERNS["reuse"]):
        pts[DIMENSIONS[5]] += 6
    if _has_any(reuse_block, [r"\bqué\s+har[ií]an\s+diferente\b", r"\berror\b", r"\blecci[oó]n\b"]):
        pts[DIMENSIONS[5]] += 2
    if _has_any(reuse_block, [r"\bplaybook\b", r"\best[aá]ndar\b", r"\bplantilla\b"]):
        pts[DIMENSIONS[5]] += 2

    return pts

def build_dimension_scoring(answers: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    pts = dim_signals(answers)
    dims = []
    for name in DIMENSIONS:
        score = score_1_to_5(pts[name])
        dims.append({
            "name": name,
            "score": score,
            "rationale": local_rationale(name, answers, pts[name], score),
            "evidence_used": local_evidence_used(name, answers),
        })
    overall = round(sum(d["score"] for d in dims) / 6.0, 2)
    return dims, overall

def local_evidence_used(dim: str, answers: List[Dict[str, Any]]) -> str:
    # Parafraseo determinístico: lista de bloques relevantes (máx 7)
    mapping = {
        DIMENSIONS[0]: ["Impacto Económico y Operativo", "Contexto Estratégico"],
        DIMENSIONS[1]: ["Impacto Económico y Operativo"],
        DIMENSIONS[2]: ["Gobernanza y Riesgo"],
        DIMENSIONS[3]: ["Adopción y Escalamiento", "Diseño de la Solución"],
        DIMENSIONS[4]: ["Diseño de la Solución"],
        DIMENSIONS[5]: ["Reusabilidad y Aprendizaje"],
    }
    blocks = mapping.get(dim, [])
    present = []
    for b in blocks:
        if block_text(b, answers):
            present.append(b)
    if not present:
        return "No hay evidencia textual suficiente en los bloques esperados."
    return "Evidencia detectada en: " + ", ".join(present[:7]) + "."

def local_rationale(dim: str, answers: List[Dict[str, Any]], pts: int, score: int) -> str:
    # Rationale determinístico y ejecutivo (sin listas >7)
    impact_block = block_text("Impacto Económico y Operativo", answers)
    gov_block = block_text("Gobernanza y Riesgo", answers)
    adoption_block = block_text("Adopción y Escalamiento", answers)
    design_block = block_text("Diseño de la Solución", answers)
    reuse_block = block_text("Reusabilidad y Aprendizaje", answers)
    all_txt = full_text(answers)

    chk = evidence_check(all_txt)
    chk_imp = evidence_check(impact_block)

    if dim == DIMENSIONS[0]:
        if not impact_block:
            return "No se documenta impacto cuantitativo en el bloque de impacto; el puntaje refleja ausencia de resultados medibles."
        if _has_any(impact_block, PATTERNS["impact"]) and chk_imp["baseline"] and chk_imp["period"]:
            return "Se reportan resultados y comparativo temporal; el puntaje refleja presencia de impacto y horizonte, con atribución variable según la evidencia."
        return "Hay referencias a impacto, pero faltan elementos para sostenerlo con comparativo temporal o atribución explícita."

    if dim == DIMENSIONS[1]:
        missing = [k for k, v in chk.items() if not v]
        if not missing and all(chk_imp.values()):
            return "La evidencia cierra: baseline, periodo, fuente, owner y método aparecen de forma consistente; el puntaje refleja trazabilidad alta."
        if impact_block and any(not chk_imp[k] for k in chk_imp):
            return "El bloque de impacto no cierra evidencia completa (baseline/periodo/fuente/owner/método); el puntaje refleja trazabilidad parcial."
        return "La evidencia es fragmentaria; el puntaje refleja falta de trazabilidad mínima en varios elementos."

    if dim == DIMENSIONS[2]:
        if not gov_block:
            return "No se documentan riesgos y controles; el puntaje refleja ausencia de governance explícito."
        if _has_any(gov_block, PATTERNS["governance"]) and _has_any(gov_block, [r"\bcontrol\b", r"\bmitigaci[oó]n\b", r"\bauditor[ií]a\b"]):
            return "Se describen riesgos y controles; el puntaje refleja governance explícito y consideración de fallas."
        return "Se mencionan riesgos o controles de forma general; falta especificidad operacional."

    if dim == DIMENSIONS[3]:
        if not adoption_block:
            return "No se documenta adopción/uso; el puntaje refleja ejecución no demostrada."
        if _has_any(adoption_block, [r"\busuarios?\b", r"\buso\b"]) and _has_any(adoption_block, [r"\bfrecuencia\b", r"\bactivos\b", r"\broll[- ]?out\b"]):
            return "Se evidencian mecanismos de adopción y señales de uso; el puntaje refleja ejecución con trazas operativas."
        return "Hay narrativa de cambio, pero poca evidencia de uso real o métricas de adopción."

    if dim == DIMENSIONS[4]:
        if not design_block:
            return "No se describe diseño/arquitectura; el puntaje refleja falta de detalle de solución."
        if _has_any(design_block, PATTERNS["novelty"]) and _has_any(design_block, [r"\barquitectura\b", r"\bintegraci[oó]n\b"]):
            return "Se describe solución con elementos técnicos/arquitectónicos; el puntaje refleja diferenciación razonable y trade-offs variables."
        return "La solución se describe a alto nivel; falta detalle de arquitectura o decisiones de diseño."

    if dim == DIMENSIONS[5]:
        if not reuse_block:
            return "No se documentan aprendizajes o reusabilidad; el puntaje refleja ausencia de transferencia."
        if _has_any(reuse_block, PATTERNS["reuse"]) and _has_any(reuse_block, [r"\berror\b", r"\blecci[oó]n\b"]):
            return "Se documentan lecciones y condiciones de replicabilidad; el puntaje refleja aprendizaje explícito."
        return "Se mencionan aprendizajes, pero con baja estructuración o sin criterios claros de replicabilidad."

    return f"Puntaje derivado de señales textuales (pts={pts}) y completitud de evidencia (score={score})."

def confidence_from_evidence(answers: List[Dict[str, Any]]) -> float:
    """
    Confianza local (0..1) basada en:
    - completitud de evidencia global
    - completitud de evidencia en bloque de impacto
    """
    all_txt = full_text(answers)
    imp_txt = block_text("Impacto Económico y Operativo", answers)
    chk_all = evidence_check(all_txt)
    chk_imp = evidence_check(imp_txt)

    base = sum(1 for v in chk_all.values() if v) / 5.0  # 0..1
    imp = sum(1 for v in chk_imp.values() if v) / 5.0 if imp_txt else 0.0
    conf = 0.6 * base + 0.4 * imp
    return round(conf, 2)

def strengths_list(answers: List[Dict[str, Any]], dims: List[Dict[str, Any]]) -> List[str]:
    # Determinístico: toma top dimensiones >=4 como fortalezas (máx 7)
    strengths = []
    for d in sorted(dims, key=lambda x: x["score"], reverse=True):
        if d["score"] >= 4:
            strengths.append(f"{d['name']} (score {d['score']}/5) con evidencia en bloques relevantes.")
    if not strengths:
        strengths.append("No destacan fortalezas claras por evidencia; priorizar cierre de datos y resultados.")
    return strengths[:7]

def clarifying_questions(answers: List[Dict[str, Any]]) -> List[str]:
    """
    Preguntas concretas para cerrar vacíos (máx 7), MECE:
    1) baseline exacto KPI
    2) periodo exacto KPI
    3) fuente
    4) owner
    5) método
    6) atribución
    7) adopción/uso
    """
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

    # Atribución (si no detectamos palabras típicas)
    if not _has_any(imp_txt, [r"\batribuci[oó]n\b", r"\bcontrol\b", r"\ba\/b\b", r"\bcontrafactual\b", r"\bcausal\b"]):
        qs.append("¿Qué evidencia tienen para atribuir el cambio al programa (comparativo, control, experimento, antes/después con supuestos)?")

    # Adopción/uso
    adp = block_text("Adopción y Escalamiento", answers)
    if not _has_any(adp, [r"\busuarios?\b", r"\bactivos\b", r"\bfrecuencia\b", r"\buso\b"]):
        qs.append("¿Qué métricas de uso real (usuarios activos, frecuencia, cumplimiento) demuestran adopción sostenida?")

    return qs[:7]

def decision_registry_local(answers: List[Dict[str, Any]], gaps: List[str]) -> List[Dict[str, str]]:
    """
    Decision Registry local (máx 7) basado en vacíos de evidencia y gates.
    MECE: evidencia, atribución, governance, adopción, escalamiento, comunicación, datos.
    """
    dr = []
    year = datetime.now().year

    def add(i: int, decision: str, rationale: str, evidence_required: str, owner: str, due: str):
        dr.append({
            "decision_id": f"DR-{year}-INNO-{i:03d}",
            "decision": decision,
            "rationale": rationale,
            "evidence_required": evidence_required,
            "owner": owner,
            "due_date": due,
        })

    imp = block_text("Impacto Económico y Operativo", answers)
    chk_imp = evidence_check(imp) if imp else {"baseline": False, "period": False, "source": False, "owner": False, "method": False}

    i = 1
    if not (chk_imp["baseline"] and chk_imp["period"]):
        add(i, "Cerrar baseline y periodo del KPI principal",
            "Sin comparativo temporal el impacto no es defendible ante jurado.",
            "Baseline (valor/unidad/fecha) + periodo (inicio/fin) + resultado actual.",
            "CFO / Data Owner", today_plus(7)); i += 1
    if not chk_imp["source"]:
        add(i, "Evidenciar fuente y trazabilidad del KPI",
            "Sin sistema origen no hay auditabilidad mínima.",
            "Sistema origen, reporte, query/ubicación del dashboard, evidencia adjunta.",
            "CIO / BI Lead", today_plus(7)); i += 1
    if not chk_imp["method"]:
        add(i, "Formalizar método de cálculo del KPI",
            "Definiciones ambiguas generan score bajo en medición.",
            "Definición operacional y fórmula; reglas de inclusión/exclusión.",
            "PMO / Data Owner", today_plus(10)); i += 1
    if not _has_any(imp, [r"\batribuci[oó]n\b", r"\bcontrol\b", r"\ba\/b\b", r"\bcontrafactual\b", r"\bcausal\b"]):
        add(i, "Documentar lógica de atribución del impacto",
            "Sin atribución, el impacto puede ser ruido o factor externo.",
            "Comparativo, control o explicación causal con supuestos explícitos.",
            "Sponsor del caso", today_plus(10)); i += 1

    gov = block_text("Gobernanza y Riesgo", answers)
    if gov and not _has_any(gov, [r"\bcontrol\b", r"\bmitigaci[oó]n\b", r"\bauditor[ií]a\b"]):
        add(i, "Especificar controles para riesgos identificados",
            "Mencionar riesgos sin controles reduce credibilidad.",
            "Lista de controles, frecuencia, owner del control, evidencia de ejecución.",
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
    strengths = strengths_list(answers, dims)
    dr = decision_registry_local(answers, gaps)

    return {
        "overall_score": overall,
        "confidence": conf,
        "dimensions": dims,
        "strengths": strengths[:7],
        "evidence_gaps": gaps[:7],
        "clarifying_questions": qs[:7],
        "decision_registry": dr[:7],
        "notes": "Scoring determinístico local basado en heurísticas de texto y checklist de evidencia (sin API).",
        "generated_at": now_iso(),
    }

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

def executive_pack_md(meta: Dict[str, Any], answers: List[Dict[str, Any]], round_scores: Dict[str, Any]) -> str:
    md: List[str] = []
    md.append("# Pack Ejecutivo (Local)\n")
    md.append(f"**Empresa:** {meta.get('empresa') or '—'}  ")
    md.append(f"**Categoría:** {meta.get('categoria') or '—'}  ")
    md.append(f"**Entrevistado:** {meta.get('entrevistado') or '—'} ({meta.get('rol') or '—'})  ")
    md.append(f"**Exportado:** {now_iso()}  ")
    md.append("\n---\n")

    # Scoring A/B/C (si existe)
    any_score = any(round_scores.get(r) for r in ["A", "B", "C"])
    if any_score:
        md.append("## Scoring (A/B/C)\n")
        for r in ["A", "B", "C"]:
            if round_scores.get(r):
                md.append(f"- **Ronda {r}** — overall {round_scores[r]['overall_score']}/5, confianza {round_scores[r]['confidence']}")
        md.append("\n---\n")

    # Q/A por bloque (máx 7 Q/A por bloque)
    by_block: Dict[str, List[Dict[str, Any]]] = {}
    for a in answers:
        by_block.setdefault(a["block"], []).append(a)

    for b in BLOCKS:
        md.append(f"## {b}\n")
        items = by_block.get(b, [])
        if not items:
            md.append("—\n")
            continue
        for it in items[:7]:
            md.append(f"- **Q:** {it['question']}\n  **A:** {it['answer'] or '—'}")
        md.append("")

    # Decision Registry: toma A si existe, si no B, si no C
    pick = round_scores.get("A") or round_scores.get("B") or round_scores.get("C")
    md.append("\n---\n## Decision Registry (máx 7)\n")
    if pick and pick.get("decision_registry"):
        for d in pick["decision_registry"][:7]:
            md.append(
                f"- **{d['decision_id']}** — {d['decision']}\n"
                f"  - Rationale: {d['rationale']}\n"
                f"  - Evidencia requerida: {d['evidence_required']}\n"
                f"  - Owner: {d['owner']} | Due: {d['due_date']}"
            )
    else:
        md.append("—")

    if meta.get("notas"):
        md.append("\n---\n## Notas\n")
        md.append(meta["notas"])

    return "\n".join(md).strip()

# ----------------------------
# UI
# ----------------------------
init_state()
ensure_answers_length()

st.title("Modo Jurado — 100% local (sin API)")
st.caption("Entrevista + scoring determinístico por 6 dimensiones + dispersión A/B/C + exportables.")

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

    # Checklist local en vivo (sobre respuesta actual)
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
        st.session_state.pack_md = ""
        st.session_state.meta["fecha_inicio"] = now_iso()
        ensure_answers_length()
        st.rerun()

with right:
    st.subheader("Scoring local y exportables")

    round_id = st.selectbox("Ronda/Jurado", ["A", "B", "C"], index=0)

    if st.button("⚖️ Correr scoring local (esta ronda)", use_container_width=True):
        upsert_answer(st.session_state.idx, answer)
        ensure_answers_length()
        st.session_state.round_scores[round_id] = local_scoring_round(st.session_state.answers)
        st.success(f"Scoring local generado (ronda {round_id}).")

    rs = st.session_state.round_scores.get(round_id)
    if rs:
        st.metric("Overall", f"{rs['overall_score']}/5")
        st.metric("Confianza", f"{rs['confidence']}")
        st.markdown("### Por dimensión")
        for d in rs["dimensions"][:6]:
            st.write(f"- **{d['name']}**: {d['score']}/5")
        st.markdown("### Vacíos de evidencia (máx 7)")
        st.write("\n".join([f"- {g}" for g in (rs.get("evidence_gaps") or [])[:7]]) or "—")
        st.markdown("### Preguntas de aclaración (máx 7)")
        st.write("\n".join([f"- {q}" for q in (rs.get("clarifying_questions") or [])[:7]]) or "—")

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
    if st.button("📄 Generar Pack Ejecutivo (MD)", use_container_width=True):
        upsert_answer(st.session_state.idx, answer)
        ensure_answers_length()
        st.session_state.pack_md = executive_pack_md(st.session_state.meta, st.session_state.answers, st.session_state.round_scores)

    if st.session_state.pack_md:
        st.download_button(
            "⬇️ Descargar Pack (MD)",
            data=st.session_state.pack_md.encode("utf-8"),
            file_name=f"Pack_Local_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.text_area("Vista previa", value=st.session_state.pack_md, height=200)

    payload = {
        "meta": st.session_state.meta,
        "answers": st.session_state.answers,
        "round_scores": st.session_state.round_scores,
        "exported_at": now_iso(),
        "mode": "local_no_api",
    }
    st.download_button(
        "⬇️ Descargar todo (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"Local_All_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ', '_')}.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()
st.caption("Nota: el scoring local es heurístico y conservador; su función es estandarizar checklist y priorizar preguntas de aclaración, no sustituir juicio del jurado.")

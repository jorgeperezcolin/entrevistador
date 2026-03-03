# streamlit_app_jurado.py
# Ejecuta: streamlit run streamlit_app_jurado.py
#
# MODO JURADO (avanzado):
# - Scoring por BLOQUE (6 bloques) -> consolidación a 6 DIMENSIONES
# - Calibración (caso de referencia) y registro de calibración
# - Control de dispersión: 3 rondas (A/B/C) o 3 jurados; detecta outliers por dimensión
# - Decision Registry: hallazgos, vacíos de evidencia, preguntas de aclaración y decisiones/editorial-gates
#
# Requisitos:
#   pip install streamlit openai
#   export OPENAI_API_KEY="..."
#   (opcional) export OPENAI_MODEL="gpt-5.2"

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import streamlit as st
from openai import OpenAI

# ----------------------------
# Config
# ----------------------------
st.set_page_config(page_title="Jurado | Las Más Innovadoras", layout="wide")

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Eres Evaluador Senior del Premio Las Más Innovadoras.
Tu trabajo es evaluar iniciativas de innovación con rigor, orientado a evidencia verificable.

Reglas:
- No inventes cifras ni fuentes.
- Penaliza ausencia de baseline, periodo, fuente, owner del KPI y método de cálculo cuando aplique.
- Explica el razonamiento de forma ejecutiva y trazable (sin quotes largos).
- Mantén consistencia inter-jurado (calibración y anclas).
""".strip()

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

QUESTIONS: List[Dict[str, Any]] = [
    {"block": "Contexto Estratégico", "q": "¿Cuál era el problema estratégico que enfrentaban?"},
    {"block": "Contexto Estratégico", "q": "¿Qué consecuencias tenía no resolverlo?"},
    {"block": "Contexto Estratégico", "q": "¿Cuál era el baseline cuantitativo antes de la intervención? (unidad y fecha)"},
    {"block": "Contexto Estratégico", "q": "¿Qué hipótesis estratégica decidieron validar?"},
    {"block": "Diseño de la Solución", "q": "Describe la solución implementada (qué hicieron, para quién, en qué proceso)."},
    {"block": "Diseño de la Solución", "q": "¿Qué cambió en su modelo operativo? (roles, rituales, SLAs, governance)"},
    {"block": "Diseño de la Solución", "q": "¿Qué tecnología o arquitectura habilitó la solución? (alto nivel)"},
    {"block": "Diseño de la Solución", "q": "¿Qué trade-offs asumieron al diseñarla?"},
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
# Schemas (Structured Outputs)
# ----------------------------
BLOCK_SCORE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "block": {"type": "string"},
        "dimension_signals": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "signal": {"type": "integer", "minimum": 1, "maximum": 5},
                    "rationale": {"type": "string"},
                    "evidence_used": {"type": "string"},
                },
                "required": ["name", "signal", "rationale", "evidence_used"],
            },
        },
        "evidence_gaps": {"type": "array", "maxItems": 7, "items": {"type": "string"}},
        "clarifying_questions": {"type": "array", "maxItems": 7, "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["block", "dimension_signals", "evidence_gaps", "clarifying_questions", "notes"],
}

FINAL_SCORE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_score": {"type": "number", "minimum": 1, "maximum": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "dimensions": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "score": {"type": "integer", "minimum": 1, "maximum": 5},
                    "rationale": {"type": "string"},
                    "evidence_used": {"type": "string"},
                },
                "required": ["name", "score", "rationale", "evidence_used"],
            },
        },
        "strengths": {"type": "array", "maxItems": 7, "items": {"type": "string"}},
        "evidence_gaps": {"type": "array", "maxItems": 7, "items": {"type": "string"}},
        "clarifying_questions": {"type": "array", "maxItems": 7, "items": {"type": "string"}},
        "decision_registry": {
            "type": "array",
            "maxItems": 7,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "decision_id": {"type": "string"},
                    "decision": {"type": "string"},
                    "rationale": {"type": "string"},
                    "evidence_required": {"type": "string"},
                    "owner": {"type": "string"},
                    "due_date": {"type": "string"},
                },
                "required": ["decision_id", "decision", "rationale", "evidence_required", "owner", "due_date"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": [
        "overall_score",
        "confidence",
        "dimensions",
        "strengths",
        "evidence_gaps",
        "clarifying_questions",
        "decision_registry",
        "notes",
    ],
}

# ----------------------------
# Helpers
# ----------------------------
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def init_state():
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    if "answers" not in st.session_state:
        st.session_state.answers = []  # aligned to QUESTIONS index
    if "meta" not in st.session_state:
        st.session_state.meta = {
            "empresa": "",
            "categoria": "",
            "entrevistado": "",
            "rol": "",
            "fecha_inicio": now_iso(),
            "notas": "",
        }
    if "calibration" not in st.session_state:
        st.session_state.calibration = {
            "reference_case": "",
            "anchors": {
                "1": "Débil/no probado/poco ejecutado.",
                "3": "Sólido con vacíos relevantes.",
                "5": "Sobresaliente con evidencia robusta y governance explícito.",
            },
            "calibration_notes": "",
        }
    if "block_scores" not in st.session_state:
        # dict[round_id][block] = score_json
        st.session_state.block_scores = {"A": {}, "B": {}, "C": {}}
    if "final_scores" not in st.session_state:
        st.session_state.final_scores = {"A": None, "B": None, "C": None}
    if "pack_md" not in st.session_state:
        st.session_state.pack_md = ""

def current_question() -> Dict[str, Any]:
    return QUESTIONS[st.session_state.idx]

def upsert_answer(i: int, text: str):
    q = QUESTIONS[i]
    entry = {"timestamp": now_iso(), "block": q["block"], "question": q["q"], "answer": (text or "").strip()}
    if len(st.session_state.answers) > i:
        st.session_state.answers[i] = entry
    else:
        while len(st.session_state.answers) < i:
            j = len(st.session_state.answers)
            st.session_state.answers.append({
                "timestamp": now_iso(),
                "block": QUESTIONS[j]["block"],
                "question": QUESTIONS[j]["q"],
                "answer": "",
            })
        st.session_state.answers.append(entry)

def ensure_answers_length():
    while len(st.session_state.answers) < len(QUESTIONS):
        j = len(st.session_state.answers)
        st.session_state.answers.append({
            "timestamp": now_iso(),
            "block": QUESTIONS[j]["block"],
            "question": QUESTIONS[j]["q"],
            "answer": "",
        })

def block_transcript(block: str, meta: Dict[str, Any], answers: List[Dict[str, Any]]) -> str:
    lines = [
        f"Empresa: {meta.get('empresa','')}",
        f"Categoría: {meta.get('categoria','')}",
        f"Entrevistado: {meta.get('entrevistado','')} | Rol: {meta.get('rol','')}",
        f"Bloque: {block}",
        "",
    ]
    for a in answers:
        if a["block"] == block:
            lines.append(f"Q: {a['question']}")
            lines.append(f"A: {a['answer'] or '—'}")
            lines.append("")
    if meta.get("notas"):
        lines.append("Notas del evaluador:")
        lines.append(meta["notas"])
    return "\n".join(lines).strip()

def full_transcript(meta: Dict[str, Any], answers: List[Dict[str, Any]]) -> str:
    lines = [
        f"Empresa: {meta.get('empresa','')}",
        f"Categoría: {meta.get('categoria','')}",
        f"Entrevistado: {meta.get('entrevistado','')} | Rol: {meta.get('rol','')}",
        f"Fecha inicio: {meta.get('fecha_inicio','')}",
        "",
    ]
    for a in answers:
        lines.append(f"[{a['block']}] Q: {a['question']}")
        lines.append(f"A: {a['answer'] or '—'}")
        lines.append("")
    if meta.get("notas"):
        lines.append("Notas del evaluador:")
        lines.append(meta["notas"])
    return "\n".join(lines).strip()

def call_openai_json_schema(user_text: str, schema: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        },
    )
    return json.loads(resp.output_text)

def run_block_scoring(round_id: str, block: str) -> Dict[str, Any]:
    ensure_answers_length()
    transcript = block_transcript(block, st.session_state.meta, st.session_state.answers)
    calib = st.session_state.calibration

    prompt = f"""
EVALÚA ESTE BLOQUE como señales para 6 dimensiones (1–5).
Usa anclas:
1 = {calib['anchors']['1']}
3 = {calib['anchors']['3']}
5 = {calib['anchors']['5']}

Calibración (nota del jurado):
{calib.get('calibration_notes','')}

Reglas:
- Devuelve EXACTAMENTE 6 señales, en este orden y con estos nombres:
1) {DIMENSIONS[0]}
2) {DIMENSIONS[1]}
3) {DIMENSIONS[2]}
4) {DIMENSIONS[3]}
5) {DIMENSIONS[4]}
6) {DIMENSIONS[5]}
- "signal" es una señal parcial del bloque (no es el score final).
- Si falta evidencia, baja la señal correspondiente y registra evidence_gaps.
- "evidence_used" debe referir qué parte del transcript soporta la señal (paráfrasis).
- "clarifying_questions" máx 7, concretas.

TRANSCRIPT BLOQUE:
{transcript}
""".strip()

    data = call_openai_json_schema(prompt, BLOCK_SCORE_SCHEMA, f"block_score_{round_id}")
    # normalizar nombres/orden
    data["block"] = block
    if len(data["dimension_signals"]) == 6:
        for i in range(6):
            data["dimension_signals"][i]["name"] = DIMENSIONS[i]
    return data

def aggregate_final_score(round_id: str) -> Dict[str, Any]:
    ensure_answers_length()
    transcript = full_transcript(st.session_state.meta, st.session_state.answers)
    calib = st.session_state.calibration

    # compact block signals for model input
    block_bundle = []
    for b in BLOCKS:
        bs = st.session_state.block_scores[round_id].get(b)
        if bs:
            block_bundle.append(bs)
    bundle_text = json.dumps(block_bundle, ensure_ascii=False, indent=2)

    prompt = f"""
CONSOLIDA scoring FINAL 1–5 por dimensión usando:
- Transcript completo (fuente primaria)
- Señales por bloque (fuente secundaria)

Anclas:
1 = {calib['anchors']['1']}
3 = {calib['anchors']['3']}
5 = {calib['anchors']['5']}

Reglas:
- 6 dimensiones fijas (mismos nombres y orden).
- Score global = promedio simple de las 6 dimensiones.
- No inventes datos; penaliza evidencia incompleta en "Evidencia y medición".
- "strengths", "evidence_gaps", "clarifying_questions" máx 7.
- "decision_registry" máx 7 decisiones internas (editorial / evidencia / governance), con:
  decision_id: formato "DR-{datetime.now().year}-INNO-###" (secuencial simple 001..007)
  owner: rol sugerido (p.ej. "CFO", "CIO", "PMO", "Data Owner", "Equipo de Premio")
  due_date: ISO date YYYY-MM-DD (si no hay fecha, usa hoy+7 días)

TRANSCRIPT COMPLETO:
{transcript}

SEÑALES POR BLOQUE (JSON):
{bundle_text}
""".strip()

    data = call_openai_json_schema(prompt, FINAL_SCORE_SCHEMA, f"final_score_{round_id}")
    # normalizar dimensiones
    if len(data.get("dimensions", [])) == 6:
        for i in range(6):
            data["dimensions"][i]["name"] = DIMENSIONS[i]
    return data

def dispersion_report(finals: Dict[str, Optional[Dict[str, Any]]]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Calcula dispersión simple entre rondas A/B/C:
    - Por dimensión: max(score)-min(score)
    - Bandera si dispersión >=2 en alguna dimensión (máx 7 banderas)
    """
    flags: List[str] = []
    report: Dict[str, Any] = {"by_dimension": [], "overall_range": None}

    rounds = [r for r in ["A", "B", "C"] if finals.get(r)]
    if not rounds:
        return report, flags

    # overall range
    overalls = [finals[r]["overall_score"] for r in rounds]
    report["overall_range"] = float(max(overalls) - min(overalls))

    # per dimension
    for i, name in enumerate(DIMENSIONS):
        vals = []
        for r in rounds:
            vals.append(finals[r]["dimensions"][i]["score"])
        rng = max(vals) - min(vals)
        report["by_dimension"].append({"name": name, "scores": {r: finals[r]["dimensions"][i]["score"] for r in rounds}, "range": rng})
        if rng >= 2 and len(flags) < 7:
            flags.append(f"Dispersión alta en '{name}' (rango {rng}). Requiere calibración rápida y revisión de evidencia usada.")
    return report, flags

def executive_pack(meta: Dict[str, Any], answers: List[Dict[str, Any]], finals: Dict[str, Any]) -> str:
    md = []
    md.append("# Pack Ejecutivo (Jurado)\n")
    md.append(f"**Empresa:** {meta.get('empresa') or '—'}  ")
    md.append(f"**Categoría:** {meta.get('categoria') or '—'}  ")
    md.append(f"**Entrevistado:** {meta.get('entrevistado') or '—'} ({meta.get('rol') or '—'})  ")
    md.append(f"**Exportado:** {now_iso()}  ")
    md.append("\n---\n")

    if finals:
        md.append("## Scoring (A/B/C)\n")
        for r in ["A", "B", "C"]:
            if finals.get(r):
                md.append(f"- **Ronda {r}** — overall {finals[r]['overall_score']}/5, confianza {finals[r]['confidence']}")
        md.append("\n---\n")

    # Resumen por bloque (máx 7 bullets total por bloque, pero aquí no listamos bullets; Q/A ya es granular)
    by_block: Dict[str, List[Dict[str, Any]]] = {}
    for a in answers:
        by_block.setdefault(a["block"], []).append(a)

    for b in BLOCKS:
        md.append(f"## {b}\n")
        items = by_block.get(b, [])
        if not items:
            md.append("—\n")
            continue
        # Mostrar máximo 7 Q/A por bloque (MECE no aplica a Q/A, pero el límite sí)
        for it in items[:7]:
            md.append(f"- **Q:** {it['question']}\n  **A:** {it['answer'] or '—'}")
        md.append("")

    # Decision registry: tomar el de la ronda A si existe, si no B, si no C
    pick = finals.get("A") or finals.get("B") or finals.get("C")
    md.append("\n---\n## Decision Registry (máx 7)\n")
    if pick:
        dr = (pick.get("decision_registry") or [])[:7]
        if dr:
            for d in dr:
                md.append(
                    f"- **{d['decision_id']}** — {d['decision']}\n"
                    f"  - Rationale: {d['rationale']}\n"
                    f"  - Evidencia requerida: {d['evidence_required']}\n"
                    f"  - Owner: {d['owner']} | Due: {d['due_date']}"
                )
        else:
            md.append("—")
    else:
        md.append("—")

    return "\n".join(md).strip()

# ----------------------------
# UI
# ----------------------------
init_state()

st.title("Modo Jurado — Entrevista + Scoring por Bloque + Dispersión + Decision Registry")
st.caption("Pensado para 3 rondas/jurados (A/B/C). Si usas 1 jurado, corre solo ronda A.")

api_key_ok = bool(os.environ.get("OPENAI_API_KEY"))
if not api_key_ok:
    st.error("Falta OPENAI_API_KEY en variables de entorno. El scoring no funcionará.")

with st.expander("Metadatos", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.meta["empresa"] = st.text_input("Empresa", value=st.session_state.meta["empresa"])
        st.session_state.meta["categoria"] = st.text_input("Categoría", value=st.session_state.meta["categoria"])
    with c2:
        st.session_state.meta["entrevistado"] = st.text_input("Entrevistado", value=st.session_state.meta["entrevistado"])
        st.session_state.meta["rol"] = st.text_input("Rol", value=st.session_state.meta["rol"])
    with c3:
        st.session_state.meta["notas"] = st.text_area("Notas del evaluador (opcional)", value=st.session_state.meta["notas"], height=90)

with st.expander("Calibración (recomendado antes de evaluar)", expanded=False):
    st.session_state.calibration["reference_case"] = st.text_area(
        "Caso de referencia (mini-resumen del caso ‘gold standard’ o ejemplo calibrado)",
        value=st.session_state.calibration.get("reference_case", ""),
        height=110,
    )
    st.session_state.calibration["calibration_notes"] = st.text_area(
        "Notas de calibración del jurado (qué significa 3 vs 4 en esta categoría, qué penaliza, etc.)",
        value=st.session_state.calibration.get("calibration_notes", ""),
        height=90,
    )

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Entrevista (captura)")
    st.write(f"**Progreso:** {st.session_state.idx + 1} / {len(QUESTIONS)}")

    q = current_question()
    st.markdown(f"### Bloque: {q['block']}")
    st.markdown(f"**Pregunta:** {q['q']}")

    default_answer = ""
    if len(st.session_state.answers) > st.session_state.idx:
        default_answer = st.session_state.answers[st.session_state.idx].get("answer", "")

    answer = st.text_area("Respuesta", value=default_answer, height=170)

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
        st.session_state.block_scores = {"A": {}, "B": {}, "C": {}}
        st.session_state.final_scores = {"A": None, "B": None, "C": None}
        st.session_state.pack_md = ""
        st.session_state.meta["fecha_inicio"] = now_iso()
        st.rerun()

with right:
    st.subheader("Evaluación (jurado)")

    round_id = st.selectbox("Ronda/Jurado", ["A", "B", "C"], index=0)
    st.caption("Sugerencia: A/B/C para 3 jurados o 3 pasadas. Si solo hay 1 jurado, usa A.")

    st.markdown("### 1) Scoring por bloque")
    block = st.selectbox("Selecciona bloque", BLOCKS, index=0)

    if st.button("📌 Correr scoring de este bloque", use_container_width=True, disabled=not api_key_ok):
        upsert_answer(st.session_state.idx, answer)
        ensure_answers_length()
        with st.spinner("Scoring por bloque..."):
            try:
                bs = run_block_scoring(round_id, block)
                st.session_state.block_scores[round_id][block] = bs
                st.success(f"Listo: {block} (ronda {round_id}).")
            except Exception as e:
                st.exception(e)

    bs_view = st.session_state.block_scores[round_id].get(block)
    if bs_view:
        st.markdown(f"**Resultado bloque — {block} (ronda {round_id})**")
        for d in bs_view.get("dimension_signals", [])[:6]:
            st.write(f"- {d['name']}: {d['signal']}/5")
        gaps = (bs_view.get("evidence_gaps") or [])[:7]
        if gaps:
            st.markdown("**Vacíos (máx 7)**")
            st.write("\n".join([f"- {g}" for g in gaps]))
        qs = (bs_view.get("clarifying_questions") or [])[:7]
        if qs:
            st.markdown("**Preguntas (máx 7)**")
            st.write("\n".join([f"- {q}" for q in qs]))

    st.divider()
    st.markdown("### 2) Consolidación final (6 dimensiones)")
    if st.button("⚖️ Consolidar scoring final (esta ronda)", use_container_width=True, disabled=not api_key_ok):
        upsert_answer(st.session_state.idx, answer)
        ensure_answers_length()
        with st.spinner("Consolidando scoring final..."):
            try:
                fs = aggregate_final_score(round_id)
                st.session_state.final_scores[round_id] = fs
                st.success(f"Scoring final generado (ronda {round_id}).")
            except Exception as e:
                st.exception(e)

    fs_view = st.session_state.final_scores.get(round_id)
    if fs_view:
        st.metric("Overall", f"{fs_view.get('overall_score','—')}/5")
        st.metric("Confianza", f"{fs_view.get('confidence','—')}")
        st.markdown("**Por dimensión**")
        for d in fs_view.get("dimensions", [])[:6]:
            st.write(f"- {d['name']}: {d['score']}/5")

    st.divider()
    st.markdown("### 3) Control de dispersión (A/B/C)")
    report, flags = dispersion_report(st.session_state.final_scores)
    if report.get("overall_range") is not None:
        st.write(f"**Rango overall:** {report['overall_range']}")
        st.markdown("**Rango por dimensión**")
        for row in report.get("by_dimension", [])[:6]:
            st.write(f"- {row['name']}: {row['scores']} | rango={row['range']}")
        if flags:
            st.warning("Banderas de dispersión (máx 7)")
            st.write("\n".join([f"- {f}" for f in flags]))
    else:
        st.info("Corre scoring final en al menos una ronda para ver dispersión.")

    st.divider()
    st.markdown("### 4) Exportables")
    if st.button("📄 Generar Pack Ejecutivo (MD)", use_container_width=True):
        st.session_state.pack_md = executive_pack(st.session_state.meta, st.session_state.answers, st.session_state.final_scores)

    if st.session_state.pack_md:
        st.download_button(
            "⬇️ Descargar Pack (MD)",
            data=st.session_state.pack_md.encode("utf-8"),
            file_name=f"Pack_Jurado_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ','_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.text_area("Vista previa", value=st.session_state.pack_md, height=200)

    payload = {
        "meta": st.session_state.meta,
        "calibration": st.session_state.calibration,
        "answers": st.session_state.answers,
        "block_scores": st.session_state.block_scores,
        "final_scores": st.session_state.final_scores,
        "generated_at": now_iso(),
        "model": MODEL,
    }
    st.download_button(
        "⬇️ Descargar todo (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"Jurado_All_{(st.session_state.meta.get('empresa') or 'empresa').replace(' ','_')}.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()
st.caption("Uso típico: (1) Captura entrevista, (2) corre scoring por bloque, (3) consolida final, (4) revisa dispersión, (5) ejecuta ronda 2 con preguntas de aclaración.")

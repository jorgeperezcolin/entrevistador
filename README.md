# Las Más Innovadoras — Modo Jurado (100% local, sin API)

Aplicación en Streamlit para conducir la entrevista y generar **scoring determinístico local** (sin llamadas a OpenAI ni a ningún API), con:

- Entrevista estructurada (6 bloques)
- Checklist de evidencia (baseline, periodo, fuente, owner, método)
- Scoring automático local por 6 dimensiones (1–5) basado en heurísticas
- Control de dispersión A/B/C (si capturas 3 rondas/jurados)
- Decision Registry local (máx 7 decisiones)
- Exportables: JSON completo + Pack Ejecutivo (Markdown)

---

## 1. Qué hace y qué no hace

### Hace
- Estandariza la captura de respuestas y la trazabilidad.
- Señala vacíos de evidencia de forma consistente.
- Produce un score **conservador** para priorizar aclaraciones.
- Genera un Decision Registry accionable para cerrar evidencia.

### No hace
- No valida documentos externos.
- No calcula causalidad real; sólo detecta señales textuales.
- No sustituye el juicio del jurado.

---

## 2. Arquitectura conceptual

### 6 Bloques de entrevista
1. Contexto Estratégico  
2. Diseño de la Solución  
3. Impacto Económico y Operativo  
4. Gobernanza y Riesgo  
5. Adopción y Escalamiento  
6. Reusabilidad y Aprendizaje  

### 6 Dimensiones de scoring
1. Impacto económico y operacional  
2. Evidencia y medición  
3. Gobernanza y riesgo  
4. Adopción y ejecución  
5. Novedad y diseño de la solución  
6. Reusabilidad y aprendizaje  

El scoring se deriva de:
- Presencia de señales (palabras clave, números, unidades, términos de governance, etc.)
- Completitud de evidencia en general y especialmente en el bloque de impacto

---

## 3. Requisitos

### Python
- Python 3.9+ recomendado

### Dependencias
```bash
pip install streamlit

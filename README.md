# Las Más Innovadoras — Modo Jurado  
Entrevista estructurada + Scoring por Bloque + Control de Dispersión + Decision Registry

Aplicación en Streamlit para evaluar empresas candidatas al premio *Las Más Innovadoras* con:

- Entrevista estructurada (6 bloques)
- Scoring automático por bloque (señales 1–5)
- Consolidación final en 6 dimensiones
- Control de dispersión entre rondas/jurados (A/B/C)
- Decision Registry interno (máx 7 decisiones)
- Exportables en JSON y Markdown

---

## 1. Objetivo

Esta herramienta busca:

1. Estandarizar evaluación entre jurados.
2. Exigir evidencia verificable (baseline, periodo, fuente, owner, método).
3. Reducir sesgos individuales mediante calibración y control de dispersión.
4. Generar trazabilidad auditables de decisiones.

---

## 2. Arquitectura Conceptual

### 6 Bloques de Entrevista
1. Contexto Estratégico  
2. Diseño de la Solución  
3. Impacto Económico y Operativo  
4. Gobernanza y Riesgo  
5. Adopción y Escalamiento  
6. Reusabilidad y Aprendizaje  

### 6 Dimensiones de Scoring
1. Impacto económico y operacional  
2. Evidencia y medición  
3. Gobernanza y riesgo  
4. Adopción y ejecución  
5. Novedad y diseño de la solución  
6. Reusabilidad y aprendizaje  

Cada bloque genera señales parciales por dimensión (1–5).  
La consolidación final calcula:

- Score por dimensión
- Score global (promedio simple)
- Confianza del scoring
- Vacíos de evidencia
- Preguntas de aclaración
- Decision Registry (máx 7 decisiones)

---

## 3. Requisitos

### Python
>= 3.9 recomendado

### Dependencias
```bash
pip install streamlit openai

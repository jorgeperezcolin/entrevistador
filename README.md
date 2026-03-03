# Las Más Innovadoras — Modo Jurado (100% local, sin API) + Entregables al entrevistado

App en Streamlit para conducir la entrevista, calcular scoring determinístico y generar 3 entregables para el entrevistado:

1) **Benchmark** de la innovación (vs cohorte configurable)  
2) **Caso de éxito publicable** (one-pager)  
3) **Caso de negocio para Consejo** (board memo)

Sin llamadas a OpenAI ni a ningún API.

---

## 1) Qué resuelve

- Estandariza entrevistas y evita “claims” sin evidencia.
- Produce un score conservador y trazable (heurísticas).
- Devuelve valor inmediato al candidato con:
  - Diagnóstico vs benchmark
  - Narrativa publicable (con gate editorial)
  - Memo para Consejo con estructura ejecutiva

---

## 2) Entregables

### 2.1 Benchmark (para entrevistado)
Comparativo por dimensión vs **mediana de cohorte** (configurable en UI):

- Estatus por dimensión:
  - Arriba de cohorte
  - En línea con cohorte
  - Abajo de cohorte
- Identifica **brechas prioritarias** para mejorar el benchmark

> Importante: la cohorte es un “reference set” operado por el usuario (no se infiere sola).

### 2.2 Caso de éxito publicable (one-pager)
Documento para publicación externa con secciones:

- Situación
- Enfoque
- Resultados
- Adopción
- Gobernanza
- Lecciones

Incluye **aviso editorial automático** si faltan elementos de evidencia (baseline/periodo/fuente/owner/método), para evitar publicar cifras frágiles.

Opciones:
- Anonimizar empresa
- Definir audiencia objetivo
- Restringir mención de vendors/marcas

### 2.3 Caso de negocio para Consejo (board memo)
Memo ejecutivo que estructura:

- Decisión solicitada al Consejo
- Problema estratégico
- Intervención y operating model
- Caso económico (con “pendiente de evidencia” si falta cierre)
- Riesgos/controles/supuestos
- Adopción/escalabilidad
- KPIs de control y governance
- Apéndice: scorecard local (6 dimensiones)

---

## 3) Arquitectura conceptual

### 3.1 Bloques de entrevista (6)
1. Contexto Estratégico  
2. Diseño de la Solución  
3. Impacto Económico y Operativo  
4. Gobernanza y Riesgo  
5. Adopción y Escalamiento  
6. Reusabilidad y Aprendizaje  

### 3.2 Dimensiones de scoring (6)
1. Impacto económico y operacional  
2. Evidencia y medición  
3. Gobernanza y riesgo  
4. Adopción y ejecución  
5. Novedad y diseño de la solución  
6. Reusabilidad y aprendizaje  

### 3.3 Evidencia mínima (checklist)
La app penaliza cuando no detecta:

- Baseline
- Periodo/fechas de medición
- Fuente del dato (sistema/reporte)
- Owner del KPI
- Método de cálculo (definición/fórmula)

---

## 4) Requisitos

### Python
- Python 3.9+ recomendado

### Dependencias
```bash
pip install streamlit

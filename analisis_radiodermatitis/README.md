# Análisis de radiodermitis — cohorte de cáncer de mama (n = 21)

Depuración y análisis bioestadístico de una cohorte de cáncer de mama tratada con
radioterapia adyuvante. **Endpoint primario:** aparición de radiodermitis aguda.

## 📄 Entregable principal

**`Informe_Radiodermitis.docx`** — informe científico en Word estructurado en:

1. **Análisis metodológico** — diseño, endpoint primario, variables analizadas (Tabla I),
   depuración de la base (Tabla II), metodología estadística y herramientas.
2. **Análisis de la muestra** — demografía, características tumorales, tratamiento y
   comparabilidad basal (Tabla III), con las Figuras 1–3.
3. **Resultados** — incidencia, Fisher con IC (Tablas IV–V, Figuras 5–6), Kaplan-Meier
   (Tabla VI, Figuras 7–8), síntesis, limitaciones, conclusiones y recomendaciones.

Todas las figuras están referenciadas en el texto.

## Contenido

```
analisis_radiodermatitis/
├── Informe_Radiodermitis.docx      ← INFORME FINAL (Word)
├── INFORME.md                       Resumen técnico del pipeline
│
├── datos_crudos.csv                 Datos originales (con los errores tal cual)
├── datos_limpios.csv                Salida depurada (40 variables)
│
├── comun.py                         Utilidades: IC Wilson/Newcombe, Kaplan-Meier, log-rank
├── 01_depuracion.py                 Detección y corrección de errores
├── 02_analisis_poblacional.py       Caracterización de la población
├── 03_fisher_ic.py                  Fisher exacto con IC 95 %
├── 04_kaplan_meier.py               Supervivencia libre de radiodermitis
├── 05_exportar_resultados.py        Volcado de resultados a JSON
├── 06_generar_informe.js            Construcción del documento Word
│
├── reporte_depuracion.txt           Traza de las 64 acciones de depuración
├── resultados_poblacional.txt
├── resultados_fisher.txt
├── resultados_kaplan_meier.txt
└── figuras/                         8 figuras (PNG)
```

## Reproducir

```bash
pip install pandas numpy scipy matplotlib pillow
python 01_depuracion.py
python 02_analisis_poblacional.py
python 03_fisher_ic.py
python 04_kaplan_meier.py
python 05_exportar_resultados.py
npm install docx && node 06_generar_informe.js
```

El documento Word se construye a partir de `informe_datos.json`, generado por el paso 5
con los resultados realmente calculados: **ninguna cifra del informe está transcrita a mano**.

## Resultados en una línea

Radiodermitis de cualquier grado en el **66,7 %** (≥ grado 2 en el **42,9 %**). El
**normofraccionamiento** es el único predictor significativo de aparición (p = 0,047) y de
gravedad (p = 0,016), aunque **confundido con la irradiación ganglionar** (7/7 vs 2/14).
Mediana de supervivencia libre de radiodermitis: **4 semanas** (log-rank por
fraccionamiento p = 0,185).

> Estudio exploratorio (n = 21, 14 eventos): pruebas exactas y no paramétricas, sin modelos
> multivariables ni corrección por comparaciones múltiples. Genera hipótesis, no
> conclusiones confirmatorias.

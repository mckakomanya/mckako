# Radiodermitis aguda en cáncer de mama tratado con radioterapia

**Cohorte:** 21 pacientes · **Endpoint primario:** aparición de radiodermitis aguda (grado ≥ 1)

> **El informe completo es `Informe_Radiodermitis.docx`** (documento Word con metodología,
> análisis de la muestra, resultados, 6 tablas y 8 figuras referenciadas en el texto).
> Este archivo es un resumen técnico del pipeline.

---

## Pipeline reproducible

```bash
pip install pandas numpy scipy matplotlib pillow
python 01_depuracion.py            # -> datos_limpios.csv, reporte_depuracion.txt
python 02_analisis_poblacional.py  # -> resultados_poblacional.txt, figuras 1-4
python 03_fisher_ic.py             # -> resultados_fisher.txt, figuras 5-6
python 04_kaplan_meier.py          # -> resultados_kaplan_meier.txt, figuras 7-8
python 05_exportar_resultados.py   # -> informe_datos.json, figuras_dims.json
node 06_generar_informe.js         # -> Informe_Radiodermitis.docx
```

`comun.py` contiene las utilidades compartidas: IC de Wilson y Newcombe, OR condicional
con IC exacto, y las implementaciones propias de **Kaplan-Meier** (varianza de Greenwood,
IC log-log) y del **test de log-rank** (Mantel-Cox con HR de Peto).

---

## 1. Depuración (64 acciones trazadas)

| Incidencia | Casos | Resolución |
|---|:--:|---|
| Nomenclatura TNM heterogénea (`T3`,`pT3`,`ypT2`,`T2(m)`,`N1mi(sn)`) | 21 | Descompuesta en categoría + prefijo (p/yp) + multifocalidad + micrometástasis + centinela |
| `Anastrozole` (fármaco) en columna binaria Sí/No | 1 | HT concurrente = **Sí**, fármaco conservado aparte |
| Tto. sistémico en texto libre (`Neoady`/`Neoadyuvante`/`Adyuvante`) | 6 | Recodificado a binaria |
| `Adyuvante` incompatible con **ypT0 ypN0** (respuesta completa) | 1 | Corregido a neoadyuvante |
| Semana de presentación = 0 sin radiodermitis | 1 | Ausente (la RT empieza en semana 1) |
| Variantes ortográficas (`Sí`/`Si`, `LuminalA`) | 4 | Unificadas |
| Estadio `Cis` | 2 | Recodificado a estadio 0 |
| Biomarcadores no evaluados en carcinoma in situ | 2 | Ausentes (no imputados) |
| Estadio anatómico IIIA vs pronóstico IB (pac. 11) | 1 | Marcado para revisión, **no** modificado |

**Ki67 = 99 %:** valores **reales** confirmados con el investigador. Se mantienen en todos
los análisis; solo se consideran ausentes los 2 casos in situ no evaluados.

---

## 2. Análisis poblacional

- **Edad:** media 61,6 ± 12,9; mediana 60 (RIC 58–72); rango 29–81. Normal (Shapiro-Wilk p=0,326).
- **Comorbilidad:** diabetes 19 % · tabaquismo activo 9,5 %.
- **Tumor:** T2 38 % · ganglios positivos 43 % · grado 3 en 65 % · Luminal B 38 %, triple negativo 24 %.
- **Ki67:** mediana 30 % (RIC 20–83; rango 9–99), fuertemente asimétrico (p=0,002).
- **Tratamiento:** conservadora 81 % · hipofx 67 % · boost 38 % · irradiación ganglionar 43 %.

**Colinealidad crítica:** las **7/7** pacientes normofraccionadas recibieron irradiación
ganglionar, frente a **2/14** hipofraccionadas (p<0,001). Ambas exposiciones son
inseparables con este tamaño muestral.

---

## 3. Test exacto de Fisher con IC 95 %

OR condicional (máxima verosimilitud) con **IC exacto**; riesgos con IC de Wilson;
diferencia de riesgos con IC de Newcombe.

### Aparición de radiodermitis (≥ grado 1) — 14/21 (66,7 %)

| Factor | Expuestas | No expuestas | Dif. riesgo (IC95%) | p |
|---|:--:|:--:|:--:|:--:|
| **Normofraccionamiento** | **100 %** | **50 %** | **+50,0 (7,6 a 73,2)** | **0,047** |
| Irradiación ganglionar | 77,8 % | 58,3 % | +19,4 (−20,0 a 50,2) | 0,642 |
| Boost | 87,5 % | 53,8 % | +33,7 (−7,9 a 60,4) | 0,174 |
| Diabetes | 100 % | 58,8 % | +41,2 (−11,6 a 64,0) | 0,255 |

> **Discordancia p vs IC:** el OR del normofraccionamiento es ∞ (celda con cero: ninguna
> normofraccionada quedó libre de RD) y su IC exacto (0,93–∞) incluye el 1 pese a p=0,047.
> No es un error: el IC de Cornfield es **conservador** respecto al p bilateral de Fisher.
> La medida interpretable aquí es la **diferencia de riesgos**, que sí excluye el 0.

### Radiodermitis significativa (≥ grado 2) — 9/21 (42,9 %)

| Factor | Expuestas | No expuestas | OR (IC95%) | p |
|---|:--:|:--:|:--:|:--:|
| **Normofraccionamiento** | **85,7 %** | **21,4 %** | **18,09 (1,44–1100)** | **0,016** |
| Irradiación ganglionar | 66,7 % | 25,0 % | 5,44 (0,66–60,6) | 0,087 |

---

## 4. Kaplan-Meier — supervivencia libre de radiodermitis

Origen: primera sesión de RT. Evento: primera radiodermitis de cualquier grado.
**14 eventos, 7 censuradas.**

**Censura:** las libres de evento se censuran en la primera visita post-RT (duración + 1
semana), porque la radiodermitis aguda alcanza su pico 1–2 semanas *tras* finalizar la RT
—de hecho 2 pacientes con esquemas de 3 semanas debutaron en la 4.ª—. Censurar al terminar
la RT habría generado **censura informativa**.

| Semana | En riesgo | Eventos | Superv. libre de RD | IC95% |
|:--:|:--:|:--:|:--:|:--:|
| 0 | 21 | 0 | 100 % | — |
| 2 | 21 | 2 | 90,5 % | 67,0–97,5 |
| 3 | 19 | 4 | 71,4 % | 47,2–86,0 |
| 4 | 15 | 7 | 38,1 % | 18,3–57,8 |
| 5 | 2 | 1 | 19,0 % | 1,7–50,9 |

- **Mediana de supervivencia libre de radiodermitis: 4 semanas.**
- Por fraccionamiento: log-rank χ²=1,76, **p=0,185**, HR (Peto) 1,81. Sin diferencia
  significativa en el *tiempo* hasta la aparición.
- Análisis de sensibilidad (censura al fin de RT): p=0,982. La conclusión cualitativa se
  mantiene, pero el estadístico es **muy sensible** al criterio de censura — señal de
  fragilidad con 14 eventos.

---

## 5. Conclusiones

1. Radiodermitis de cualquier grado en **66,7 %**; ≥ grado 2 en **42,9 %**; ninguna grado 4.
2. El **normofraccionamiento** es el único factor asociado significativamente a la aparición
   (p=0,047) y a la gravedad (p=0,016) — pero **confundido con la irradiación ganglionar**.
3. Mediana de supervivencia libre de radiodermitis: **4 semanas**; los eventos se concentran
   entre las semanas 3 y 4.
4. Las reacciones más graves aparecen **más tarde** (Spearman rho=0,60; p=0,023).
5. No se demostró diferencia en la *velocidad* de aparición entre esquemas.

**Limitaciones:** n=21 con 14 eventos (potencia baja); colinealidad fraccionamiento–volumen
ganglionar; semana registrada en enteros (censura por intervalo no modelada); todas las
censuras en el grupo hipofx. Análisis **exploratorio y generador de hipótesis**.

# Análisis de radiodermitis — cohorte de cáncer de mama (n=21)

Depuración y análisis bioestadístico de una base de datos de pacientes con
cáncer de mama tratadas con radioterapia. Endpoint: **radiodermitis aguda**.

## Contenido

```
analisis_radiodermatitis/
├── datos_crudos.csv            # Datos originales (con los errores tal cual)
├── 01_depuracion.py            # Paso 1: detección y corrección de errores
├── 02_analisis.py              # Paso 2: estadística descriptiva e inferencial
├── datos_limpios.csv           # Salida depurada (36 variables)
├── reporte_depuracion.txt      # Traza de las 68 acciones de depuración
├── resultados_estadisticos.txt # Resultados numéricos completos
├── figuras/                    # 5 gráficos (PNG)
├── INFORME.md                  # Informe clínico-estadístico (leer esto)
└── README.md
```

## Reproducir

```bash
pip install pandas numpy scipy matplotlib
python 01_depuracion.py    # genera datos_limpios.csv + reporte_depuracion.txt
python 02_analisis.py      # genera resultados_estadisticos.txt + figuras/
```

## Resumen

- **Depuración:** Ki67=99 (código centinela → ausente), tildes/espacios en
  categóricas, texto libre → binarias, fármaco en columna Sí/No, semana
  imposible, estadificación incoherente (pac. 11). Ver `INFORME.md §1`.
- **Análisis:** radiodermitis ≥ grado 2 en el 43 %. El **normofraccionamiento**
  se asocia a mayor toxicidad (86 % vs 21 %, Fisher p=0,016; efecto grande sobre
  el grado), aunque **confundido con la irradiación ganglionar**. Ver `INFORME.md §2`.

> Estudio exploratorio (n=21): pruebas no paramétricas y exactas, sin modelos
> multivariables. Genera hipótesis, no conclusiones confirmatorias.

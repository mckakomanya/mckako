/**
 * PASO 6 — GENERACION DEL INFORME EN WORD (.docx)
 * Construye el informe cientifico a partir de informe_datos.json (resultados
 * reales calculados en los pasos 1-5) y de las figuras de figuras/.
 *
 * Uso:  NODE_PATH=<ruta a node_modules> node 06_generar_informe.js
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, PageBreak, Footer, PageNumber, LevelFormat, convertInchesToTwip,
} = require("docx");

const BASE = __dirname;
const D = JSON.parse(fs.readFileSync(path.join(BASE, "informe_datos.json"), "utf8"));
const DIMS = JSON.parse(fs.readFileSync(path.join(BASE, "figuras_dims.json"), "utf8"));

// Ancho util de pagina A4 con margenes de 1 pulgada (DXA)
const ANCHO = 9026;
const AZUL = "2E5A87";
const NARANJA = "D98032";
const GRIS_F = "EDF1F5";

// ------------------------------------------------------------------ //
// Helpers
// ------------------------------------------------------------------ //
const p = (texto, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 120, line: opts.line ?? 276 },
  alignment: opts.align ?? AlignmentType.JUSTIFIED,
  indent: opts.indent,
  children: [new TextRun({
    text: texto, size: opts.size ?? 21, bold: opts.bold, italics: opts.italics,
    color: opts.color, font: "Calibri",
  })],
});

/** Parrafo con fragmentos de formato mixto: [["texto",{bold:true}], ...] */
const pMix = (partes, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 120, line: 276 },
  alignment: opts.align ?? AlignmentType.JUSTIFIED,
  children: partes.map(([t, o = {}]) => new TextRun({
    text: t, size: o.size ?? 21, bold: o.bold, italics: o.italics,
    color: o.color, font: "Calibri",
  })),
});

const h1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 340, after: 180 },
  children: [new TextRun({ text: t, size: 30, bold: true, color: AZUL, font: "Calibri" })],
});
const h2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 260, after: 130 },
  children: [new TextRun({ text: t, size: 24, bold: true, color: AZUL, font: "Calibri" })],
});
const h3 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 110 },
  children: [new TextRun({ text: t, size: 22, bold: true, color: "333333", font: "Calibri" })],
});

const vinneta = (texto) => new Paragraph({
  numbering: { reference: "vinnetas", level: 0 },
  spacing: { after: 90, line: 276 },
  alignment: AlignmentType.JUSTIFIED,
  children: [new TextRun({ text: texto, size: 21, font: "Calibri" })],
});

/** Celda de tabla */
function celda(texto, anchoDxa, opts = {}) {
  const runs = Array.isArray(texto) ? texto : [[texto, {}]];
  return new TableCell({
    width: { size: anchoDxa, type: WidthType.DXA },
    shading: opts.fill
      ? { type: ShadingType.CLEAR, fill: opts.fill, color: "auto" }
      : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: opts.align ?? AlignmentType.LEFT,
      spacing: { after: 0, line: 240 },
      children: runs.map(([t, o = {}]) => new TextRun({
        text: String(t), size: o.size ?? 18, bold: o.bold ?? opts.bold,
        color: o.color ?? opts.color, italics: o.italics, font: "Calibri",
      })),
    })],
  });
}

/** Tabla con cabecera sombreada y filas alternas */
function tabla(cabeceras, filas, anchos, opts = {}) {
  const bordeFino = { style: BorderStyle.SINGLE, size: 2, color: "BFC9D4" };
  const rows = [
    new TableRow({
      tableHeader: true,
      children: cabeceras.map((c, i) =>
        celda(c, anchos[i], {
          fill: AZUL, bold: true, color: "FFFFFF",
          align: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        })),
    }),
    ...filas.map((f, k) => new TableRow({
      children: f.map((c, i) =>
        celda(c, anchos[i], {
          fill: k % 2 ? GRIS_F : undefined,
          align: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
          bold: opts.negritaFilas?.includes(k),
        })),
    })),
  ];
  return new Table({
    columnWidths: anchos,
    width: { size: anchos.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    borders: {
      top: bordeFino, bottom: bordeFino, left: bordeFino, right: bordeFino,
      insideHorizontal: bordeFino, insideVertical: bordeFino,
    },
    rows,
  });
}

/** Imagen escalada al ancho util + pie de figura */
function figura(archivo, pie, anchoPt = 600) {
  const [w, h] = DIMS[archivo];
  const alto = Math.round((anchoPt * h) / w);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 160, after: 60 },
      children: [new ImageRun({
        type: "png",
        data: fs.readFileSync(path.join(BASE, "figuras", archivo)),
        transformation: { width: anchoPt, height: alto },
      })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 220 },
      children: [new TextRun({
        text: pie, size: 17, italics: true, color: "555555", font: "Calibri",
      })],
    }),
  ];
}

const espacio = (n = 1) => Array.from({ length: n }, () =>
  new Paragraph({ spacing: { after: 0 }, children: [] }));

// Busca una frecuencia concreta
const fr = (col, cat) => {
  const e = (D.frecuencias[col] || []).find((x) => x.categoria === cat);
  return e ? `${e.k} (${e.pct.toFixed(1).replace(".", ",")} %)` : "—";
};
/** Variante para usar YA dentro de un parentesis: "8; 38,1 %" */
const frP = (col, cat) => {
  const e = (D.frecuencias[col] || []).find((x) => x.categoria === cat);
  return e ? `${e.k}; ${e.pct.toFixed(1).replace(".", ",")} %` : "—";
};
/** Solo el porcentaje: "38,1 %" */
const frPct = (col, cat) => {
  const e = (D.frecuencias[col] || []).find((x) => x.categoria === cat);
  return e ? `${e.pct.toFixed(1).replace(".", ",")} %` : "—";
};

// ------------------------------------------------------------------ //
// CONTENIDO
// ------------------------------------------------------------------ //
const hijos = [];

// ---------- Portada ---------- //
hijos.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 1400, after: 120 },
  children: [new TextRun({
    text: "Radiodermitis aguda en pacientes con cáncer de mama tratadas con radioterapia",
    size: 40, bold: true, color: AZUL, font: "Calibri",
  })],
}));
hijos.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 500 },
  children: [new TextRun({
    text: "Análisis descriptivo, inferencial y de supervivencia de una cohorte institucional",
    size: 24, italics: true, color: "555555", font: "Calibri",
  })],
}));
hijos.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 100 },
  children: [new TextRun({
    text: `Cohorte de ${D.N} pacientes`, size: 22, bold: true, font: "Calibri",
  })],
}));
hijos.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 900 },
  children: [new TextRun({
    text: "Servicio de Oncología Radioterápica", size: 21, color: "555555", font: "Calibri",
  })],
}));

// Resumen destacado
const rd1 = D.rd_umbrales.cualquiera, rd2 = D.rd_umbrales.significativa;
hijos.push(new Table({
  columnWidths: [ANCHO],
  width: { size: ANCHO, type: WidthType.DXA },
  borders: {
    top: { style: BorderStyle.SINGLE, size: 12, color: AZUL },
    bottom: { style: BorderStyle.SINGLE, size: 12, color: AZUL },
    left: { style: BorderStyle.SINGLE, size: 12, color: AZUL },
    right: { style: BorderStyle.SINGLE, size: 12, color: AZUL },
  },
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: ANCHO, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: GRIS_F, color: "auto" },
      margins: { top: 200, bottom: 200, left: 200, right: 200 },
      children: [
        new Paragraph({
          spacing: { after: 100 },
          children: [new TextRun({ text: "Resumen de resultados", size: 22, bold: true, color: AZUL, font: "Calibri" })],
        }),
        p(`La radiodermitis de cualquier grado afectó al ${rd1.txt_ic} de la cohorte y la radiodermitis significativa (≥ grado 2) al ${rd2.txt_ic}. La mediana de supervivencia libre de radiodermitis fue de ${D.km_global.mediana} semanas desde el inicio del tratamiento. El normofraccionamiento fue el único factor asociado de forma significativa a la aparición de radiodermitis (p = ${D.fisher_aparicion[0].p}) y a la radiodermitis significativa (p = ${D.fisher_significativa[0].p}), si bien está estrechamente confundido con la irradiación ganglionar.`, { after: 0 }),
      ],
    })],
  })],
}));

hijos.push(new Paragraph({ children: [new PageBreak()] }));

// ================================================================== //
// I. METODOLOGIA
// ================================================================== //
hijos.push(h1("I. Análisis metodológico"));

hijos.push(h2("1.1. Diseño del estudio y objetivo"));
hijos.push(p(`Se trata de un estudio observacional, retrospectivo y unicéntrico sobre una cohorte consecutiva de ${D.N} pacientes diagnosticadas de cáncer de mama y tratadas con radioterapia adyuvante. El objetivo principal fue cuantificar la incidencia de radiodermitis aguda e identificar los factores clínicos, tumorales y terapéuticos asociados a su aparición y a su gravedad.`));
hijos.push(p("De forma secundaria se caracterizó el patrón temporal de aparición de la toxicidad cutánea a lo largo del tratamiento, mediante técnicas de análisis de supervivencia."));

hijos.push(h2("1.2. Endpoint primario y variables de resultado"));
hijos.push(pMix([
  ["Endpoint primario: ", { bold: true }],
  ["aparición de radiodermitis aguda de cualquier grado (≥ grado 1) durante el tratamiento radioterápico o en la primera visita posterior a su finalización. La radiodermitis se graduó según la escala RTOG/CTCAE (grados 0 a 4), registrándose el grado máximo alcanzado por cada paciente y la semana de tratamiento en la que se constató por primera vez."],
]));
hijos.push(p("Se definieron además dos endpoints secundarios:"));
hijos.push(vinneta("Radiodermitis significativa: grado máximo ≥ 2, umbral con relevancia clínica por requerir habitualmente tratamiento tópico específico y condicionar la tolerancia al tratamiento."));
hijos.push(vinneta("Tiempo hasta la aparición de la radiodermitis: número de semanas transcurridas desde la primera sesión de radioterapia hasta la primera constatación de toxicidad cutánea de cualquier grado."));

hijos.push(h2("1.3. Variables analizadas"));
hijos.push(p("Se analizaron 25 variables agrupadas en cuatro bloques. La Tabla I resume su naturaleza y escala de medida, siguiendo la codificación del cuaderno de recogida de datos."));
hijos.push(espacio()[0]);

const anchosVar = [2100, 3400, 1700, 1826];
hijos.push(tabla(
  ["Bloque", "Variable", "Tipo", "Escala"],
  [
    ["Demográficas", "Edad", "Cuantitativa", "Continua (razón)"],
    ["", "Diabetes mellitus", "Cualitativa", "Nominal binaria"],
    ["", "Tabaquismo activo", "Cualitativa", "Nominal binaria"],
    ["Tumorales", "Categoría pT (Tis–T4)", "Cualitativa", "Ordinal"],
    ["", "Categoría pN (N0–N3)", "Cualitativa", "Ordinal"],
    ["", "Metástasis (M)", "Cualitativa", "Nominal binaria"],
    ["", "Grado histológico (GHF)", "Cualitativa", "Ordinal"],
    ["", "Multifocalidad", "Cualitativa", "Nominal binaria"],
    ["", "Estadio anatómico y pronóstico", "Cualitativa", "Ordinal"],
    ["Biomarcadores", "Receptores ER y PR", "Cualitativa", "Nominal binaria"],
    ["", "Sobreexpresión HER2", "Cualitativa", "Nominal binaria"],
    ["", "Ki67 (%)", "Cuantitativa", "Continua (razón)"],
    ["", "Subtipo molecular", "Cualitativa", "Nominal"],
    ["Terapéuticas", "Tipo de cirugía", "Cualitativa", "Nominal binaria"],
    ["", "Tto. sistémico previo a RT", "Cualitativa", "Nominal binaria"],
    ["", "Hormonoterapia concurrente", "Cualitativa", "Nominal binaria"],
    ["", "Fraccionamiento (hipo/normo)", "Cualitativa", "Nominal binaria"],
    ["", "Sobreimpresión (boost)", "Cualitativa", "Nominal binaria"],
    ["", "CTV ganglionar axilar / nivel III–SC", "Cualitativa", "Nominal binaria"],
    ["Resultado", "Grado máximo de radiodermitis", "Cualitativa", "Ordinal (0–4)"],
    ["", "Semana de presentación", "Cuantitativa", "Discreta (razón)"],
  ],
  anchosVar,
));
hijos.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { before: 90, after: 220 },
  children: [new TextRun({ text: "Tabla I. Variables analizadas, naturaleza y escala de medida.", size: 17, italics: true, color: "555555", font: "Calibri" })],
}));

hijos.push(h2("1.4. Depuración de la base de datos"));
hijos.push(p("Con carácter previo al análisis se aplicó un protocolo sistemático de control de calidad, contrastando cada registro con el libro de códigos y con la coherencia clínica interna. Se documentaron y trazaron todas las modificaciones (Tabla II). Ninguna paciente fue excluida del análisis."));
hijos.push(espacio()[0]);
hijos.push(tabla(
  ["Incidencia detectada", "Casos", "Resolución adoptada"],
  [
    ["Nomenclatura TNM heterogénea (T3, pT3, ypT2, T2(m), N1mi(sn))", "21", "Descomposición en categoría, prefijo (p/yp), multifocalidad, micrometástasis y ganglio centinela"],
    ["Nombre de fármaco (Anastrozol) en columna binaria Sí/No", "1", "Recodificado a hormonoterapia concurrente = Sí, conservando el fármaco en variable aparte"],
    ["Tratamiento sistémico en texto libre (Neoady/Neoadyuvante/Adyuvante)", "6", "Recodificado a variable binaria"],
    ["Etiqueta «Adyuvante» incompatible con respuesta patológica completa (ypT0 ypN0)", "1", "Corregido a tratamiento neoadyuvante"],
    ["Semana de presentación = 0 en paciente sin radiodermitis", "1", "Marcado como ausente (la RT se inicia en la semana 1)"],
    ["Variantes ortográficas (Sí/Si, LuminalA/Luminal A)", "4", "Unificación de etiquetas"],
    ["Estadio «Cis» en variable de estadificación", "2", "Recodificado a estadio 0"],
    ["Biomarcadores no evaluados en carcinoma in situ", "2", "Marcados como ausentes (no imputados)"],
    ["Discordancia estadio anatómico (IIIA) / pronóstico (IB)", "1", "Señalado para revisión de la fuente; no modificado"],
  ],
  [3500, 800, 4726],
));
hijos.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { before: 90, after: 160 },
  children: [new TextRun({ text: "Tabla II. Incidencias detectadas en la depuración de la base de datos y resolución adoptada.", size: 17, italics: true, color: "555555", font: "Calibri" })],
}));
hijos.push(pMix([
  ["Nota sobre el índice de proliferación. ", { bold: true }],
  ["Los valores de Ki67 del 99 % registrados en cuatro pacientes fueron verificados con el investigador responsable y corresponden a determinaciones reales, por lo que se mantuvieron como tales en todos los análisis. Únicamente se consideraron ausentes los dos casos de carcinoma in situ en los que el marcador no fue evaluado."],
]));

hijos.push(h2("1.5. Metodología estadística"));
hijos.push(p("Dado el tamaño muestral y la naturaleza ordinal del endpoint principal, el plan de análisis se basó en pruebas exactas y no paramétricas, evitando aproximaciones asintóticas que resultan poco fiables con frecuencias esperadas reducidas."));
hijos.push(h3("Estadística descriptiva"));
hijos.push(p("Las variables cuantitativas se resumieron mediante media y desviación estándar, y mediana con rango intercuartílico; la normalidad se contrastó con el test de Shapiro-Wilk. Las variables cualitativas se expresaron como frecuencias absolutas y relativas, acompañadas de su intervalo de confianza del 95 % calculado por el método de Wilson, preferible al intervalo de Wald cuando el tamaño muestral es reducido o las proporciones son extremas."));
hijos.push(h3("Estadística inferencial"));
hijos.push(p("La asociación entre cada factor y la aparición de radiodermitis se evaluó mediante el test exacto de Fisher bilateral. Para cada comparación se estimó el odds ratio por máxima verosimilitud condicional, con su intervalo de confianza exacto del 95 %. Se calcularon asimismo el riesgo en expuestos y no expuestos, el riesgo relativo y la diferencia de riesgos, esta última con intervalo de confianza híbrido de Newcombe."));
hijos.push(h3("Análisis de supervivencia"));
hijos.push(p("El tiempo hasta la aparición de radiodermitis se analizó mediante el estimador de Kaplan-Meier, tomando como origen la primera sesión de radioterapia y como evento la primera constatación de toxicidad cutánea de cualquier grado. La varianza se estimó por la fórmula de Greenwood y los intervalos de confianza mediante transformación log-log. La comparación entre esquemas de fraccionamiento se realizó con el test de log-rank (Mantel-Cox), estimándose el hazard ratio por el método de Peto."));
hijos.push(pMix([
  ["Criterio de censura. ", { bold: true }],
  ["Las pacientes que no desarrollaron radiodermitis se censuraron en la primera visita posterior a la radioterapia (duración del tratamiento más una semana). Este criterio responde a que la radiodermitis aguda alcanza su máxima expresión entre una y dos semanas después de finalizar la irradiación —de hecho, dos pacientes con esquemas de tres semanas debutaron en la cuarta—, de modo que censurar al terminar el tratamiento habría generado censura informativa. Se realizó un análisis de sensibilidad con censura al finalizar la radioterapia."],
]));
hijos.push(p("Se consideró estadísticamente significativo un valor de p inferior a 0,05. No se aplicó corrección por comparaciones múltiples, por tratarse de un análisis exploratorio y generador de hipótesis."));

hijos.push(h2("1.6. Herramientas empleadas"));
hijos.push(p("El análisis se ejecutó íntegramente en Python 3.11, mediante un flujo reproducible de scripts independientes (depuración, análisis poblacional, inferencia y supervivencia). Se emplearon las bibliotecas pandas 3.0 para la gestión de datos, NumPy 2.4 para el cálculo numérico, SciPy 1.17 para las pruebas exactas y no paramétricas, y Matplotlib 3.11 para la generación de gráficos. Los estimadores de Kaplan-Meier, la varianza de Greenwood, los intervalos log-log y el test de log-rank se implementaron de forma explícita y verificada, sin recurrir a bibliotecas externas de supervivencia."));

hijos.push(new Paragraph({ children: [new PageBreak()] }));

// ================================================================== //
// II. ANALISIS DE LA MUESTRA
// ================================================================== //
hijos.push(h1("II. Análisis de la muestra"));

hijos.push(h2("2.1. Características demográficas"));
const e = D.edad;
hijos.push(p(`La cohorte estuvo constituida por ${D.N} pacientes con una edad media de ${e.txt_media} años y una mediana de ${e.mediana.toFixed(0)} años (RIC ${e.q1.toFixed(0)}–${e.q3.toFixed(0)}; rango ${e.min.toFixed(0)}–${e.max.toFixed(0)}). La distribución de la edad fue compatible con la normalidad (Shapiro-Wilk, p = ${e.shapiro_p.toFixed(3).replace(".", ",")}), como se aprecia en la Figura 1A. El grupo de mayor peso fue el de pacientes de 65 años o más (${frP("Grupo_edad", "≥65")}), seguido del grupo de 50 a 64 años (${frP("Grupo_edad", "50-64")}) y de las pacientes menores de 50 años (${frP("Grupo_edad", "<50")}), tal como recoge la Figura 1B.`));
hijos.push(p(`En cuanto a la comorbilidad con impacto conocido sobre la tolerancia cutánea, ${fr("Diabetes", "Si")} pacientes presentaban diabetes mellitus y ${fr("Tabaquismo_Actual", "Si")} eran fumadoras activas en el momento del tratamiento.`));
hijos.push(...figura("fig1_poblacion_edad.png", "Figura 1. Caracterización etaria de la población. (A) Histograma de la distribución de la edad, con la media señalada. (B) Distribución por grupos etarios."));

hijos.push(h2("2.2. Características tumorales e histopatológicas"));
hijos.push(p(`La categoría T más frecuente fue T2 (${frP("pT_cat", "T2")}), seguida de T1 y T3, con 5 casos cada una (${frPct("pT_cat", "T1")}); se incluyeron dos carcinomas in situ y un caso con respuesta patológica completa tras tratamiento neoadyuvante (ypT0). Presentaban afectación ganglionar ${fr("Ganglios_positivos", "Si")} pacientes. El grado histológico fue alto (grado 3) en ${fr("GHF", "3.0")} casos. La Figura 2 sintetiza la distribución por subtipo molecular, categoría T y estadio anatómico.`));
hijos.push(p(`Por subtipo molecular predominó el luminal B (${frP("Subtipo_Hist", "Luminal B")}), seguido del triple negativo (${frP("Subtipo_Hist", "Triple Neg")}), HER2 (${frP("Subtipo_Hist", "Her2")}) y luminal A (${frP("Subtipo_Hist", "Luminal A")}). Expresaban receptores de estrógeno ${fr("ER", "Si")} pacientes y receptores de progesterona ${fr("PR", "Si")}; la sobreexpresión de HER2 se documentó en ${fr("Her2", "Si")} casos.`));
const k = D.ki67;
hijos.push(p(`El índice de proliferación Ki67 mostró una mediana del ${k.mediana.toFixed(0)} % (RIC ${k.q1.toFixed(0)}–${k.q3.toFixed(0)} %; rango ${k.min.toFixed(0)}–${k.max.toFixed(0)} %), con una distribución marcadamente asimétrica y alejada de la normalidad (Shapiro-Wilk, p = ${k.shapiro_p.toFixed(3).replace(".", ",")}), lo que refleja la coexistencia de tumores luminales de baja proliferación con tumores triple negativo de proliferación muy elevada.`));
hijos.push(...figura("fig2_poblacion_tumor.png", "Figura 2. Características tumorales de la población. (A) Subtipo molecular. (B) Categoría T. (C) Estadio anatómico.", 620));

hijos.push(h2("2.3. Características del tratamiento"));
hijos.push(p(`La cirugía fue conservadora en ${fr("Cirugia", "CC")} pacientes y radical (mastectomía) en ${fr("Cirugia", "Mastectomia")}. Recibieron tratamiento sistémico previo a la radioterapia ${fr("Tto_sist_previo", "Si")} pacientes, con esquemas que incluyeron quimioterapia convencional, trastuzumab, pembrolizumab, paclitaxel y adriamicina/ciclofosfamida. La hormonoterapia concurrente con la irradiación se administró en ${fr("HT_concurrente", "Si")} caso.`));
hijos.push(p(`Respecto a la radioterapia, el esquema hipofraccionado fue el mayoritario (${frP("Fraccionamiento", "Hipofx")}) frente al normofraccionado (${frP("Fraccionamiento", "Normofx")}). Se administró sobreimpresión del lecho en ${fr("Boost", "Si")} pacientes e irradiación de volúmenes ganglionares en ${fr("Irradiacion_ganglionar", "Si")}. La Figura 3 resume el perfil terapéutico de la cohorte.`));
hijos.push(...figura("fig3_poblacion_tratamiento.png", "Figura 3. Perfil terapéutico de la población: proporción de pacientes que recibieron cada modalidad de tratamiento.", 520));

hijos.push(h2("2.4. Comparabilidad de los grupos de tratamiento"));
hijos.push(p(`Puesto que el esquema de fraccionamiento constituye la principal variable de exposición del estudio, se contrastaron las características basales de ambos subgrupos (${D.n_hipo} pacientes hipofraccionadas frente a ${D.n_normo} normofraccionadas). Los resultados se presentan en la Tabla III.`));
hijos.push(espacio()[0]);
hijos.push(tabla(
  ["Característica", `Hipofx (n=${D.n_hipo})`, `Normofx (n=${D.n_normo})`, "p"],
  D.tabla_basal.map((f) => [f.variable, f.hipo, f.normo,
    f.sig ? [[f.p, { bold: true, color: "B5442A" }]] : f.p]),
  [3200, 2100, 2100, 1626],
));
hijos.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { before: 90, after: 160 },
  children: [new TextRun({ text: "Tabla III. Comparación de las características basales según el esquema de fraccionamiento (test exacto de Fisher para variables cualitativas y U de Mann-Whitney para cuantitativas).", size: 17, italics: true, color: "555555", font: "Calibri" })],
}));
hijos.push(pMix([
  ["Colinealidad entre exposiciones. ", { bold: true }],
  [`Los grupos resultaron comparables en edad, comorbilidad, tipo de cirugía y tratamiento sistémico previo, pero difirieron de forma marcada en la afectación ganglionar y, sobre todo, en la irradiación de volúmenes ganglionares: la totalidad de las ${D.n_normo} pacientes normofraccionadas la recibieron, frente a únicamente 2 de las ${D.n_hipo} hipofraccionadas (p < 0,001). Ambas exposiciones están, por tanto, casi perfectamente confundidas, lo que impide separar sus efectos respectivos con el tamaño muestral disponible. Esta limitación condiciona la interpretación de todo el análisis inferencial posterior y se retoma en el apartado de limitaciones.`],
]));

hijos.push(new Paragraph({ children: [new PageBreak()] }));

// ================================================================== //
// III. RESULTADOS
// ================================================================== //
hijos.push(h1("III. Resultados"));

hijos.push(h2("3.1. Incidencia y gravedad de la radiodermitis"));
const g = Object.fromEntries(D.rd_grados.map((x) => [x.grado, x]));
hijos.push(p(`Desarrollaron radiodermitis de cualquier grado ${rd1.txt} pacientes (IC95% ${rd1.ic[0].toFixed(1).replace(".", ",")}–${rd1.ic[1].toFixed(1).replace(".", ",")} %). La radiodermitis significativa (≥ grado 2) se registró en ${rd2.txt} casos (IC95% ${rd2.ic[0].toFixed(1).replace(".", ",")}–${rd2.ic[1].toFixed(1).replace(".", ",")} %) y la forma severa (grado 3) en ${D.rd_umbrales.severa.txt}. No se documentó ningún caso de grado 4. La distribución completa por grados se representa en la Figura 4A.`));
const sem = D.semana_rd;
hijos.push(p(`Entre las pacientes que presentaron toxicidad cutánea, la mediana de la semana de aparición fue la semana ${sem.mediana.toFixed(0)} (RIC ${sem.q1.toFixed(0)}–${sem.q3.toFixed(0)}), con un rango de ${sem.min.toFixed(0)} a ${sem.max.toFixed(0)} semanas. Como muestra la Figura 4B, la aparición se concentró en las semanas 3 y 4 de tratamiento. Se observó además una correlación positiva y significativa entre el grado máximo alcanzado y la semana de presentación (rho de Spearman = ${D.spearman_grado_semana.rho.toFixed(2).replace(".", ",")}; p = ${D.spearman_grado_semana.p}; n = ${D.spearman_grado_semana.n}), lo que indica que las reacciones más intensas se manifestaron más tardíamente, de forma coherente con un efecto acumulativo de la dosis.`));
hijos.push(...figura("fig4_endpoint_rd.png", "Figura 4. Endpoint primario. (A) Distribución del grado máximo de radiodermitis alcanzado. (B) Semana de aparición en las pacientes que desarrollaron toxicidad cutánea."));

hijos.push(h2("3.2. Factores predictores de la aparición de radiodermitis"));
hijos.push(p("Se evaluó la asociación entre diez factores clínicos, tumorales y terapéuticos y la aparición de radiodermitis de cualquier grado, mediante test exacto de Fisher. Los resultados completos figuran en la Tabla IV y se representan gráficamente en la Figura 5."));
hijos.push(espacio()[0]);
hijos.push(tabla(
  ["Factor", "Riesgo expuestas", "Riesgo no expuestas", "Dif. riesgo (IC95%)", "OR (IC95%)", "p"],
  D.fisher_aparicion.map((f) => [
    f.factor, f.r1_txt, f.r0_txt, f.dr_txt, `${f.or_txt} (${f.or_ic_txt})`,
    f.sig ? [[f.p, { bold: true, color: "B5442A" }]] : f.p,
  ]),
  [2400, 1200, 1300, 1700, 1500, 926],
));
hijos.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { before: 90, after: 160 },
  children: [new TextRun({ text: "Tabla IV. Factores asociados a la aparición de radiodermitis de cualquier grado. OR: odds ratio condicional con intervalo de confianza exacto.", size: 17, italics: true, color: "555555", font: "Calibri" })],
}));
const fa = D.fisher_aparicion[0];
hijos.push(p(`El normofraccionamiento fue el único factor con asociación estadísticamente significativa: la totalidad de las pacientes tratadas con este esquema desarrolló radiodermitis (${fa.r1_txt}), frente al ${fa.r0_txt} de las hipofraccionadas (p = ${fa.p}), lo que se traduce en una diferencia de riesgo de ${fa.dr_txt} puntos porcentuales. Ninguno de los restantes factores —irradiación ganglionar, afectación ganglionar, sobreimpresión, tipo de cirugía, diabetes, tabaquismo, tratamiento sistémico previo, edad o índice de proliferación— alcanzó significación estadística, si bien todos ellos presentan intervalos de confianza muy amplios que impiden descartar efectos clínicamente relevantes.`));
hijos.push(pMix([
  ["Consideración metodológica. ", { bold: true }],
  [`En el caso del normofraccionamiento, el odds ratio no es estimable (resulta infinito) porque ninguna paciente normofraccionada permaneció libre de radiodermitis, y su intervalo de confianza exacto (${fa.or_ic_txt}) incluye el valor nulo pese a que el valor de p es significativo. Esta discordancia no constituye un error: el intervalo exacto de Cornfield es conservador respecto al valor de p bilateral de Fisher, y ambos pueden divergir en presencia de una celda con frecuencia cero. En este escenario la medida interpretable es la diferencia de riesgos, que sí excluye el valor nulo y confirma la asociación.`],
]));
hijos.push(...figura("fig5_forest_aparicion.png", "Figura 5. Diagrama de bosque de los factores predictores de la aparición de radiodermitis. Los odds ratio se representan en escala logarítmica con su intervalo de confianza exacto del 95 %; en naranja, la asociación estadísticamente significativa. Las flechas indican intervalos que exceden los límites del eje.", 560));

hijos.push(h2("3.3. Factores predictores de radiodermitis significativa"));
hijos.push(p("El análisis se repitió tomando como evento la radiodermitis de grado 2 o superior, de mayor trascendencia clínica. Los resultados se recogen en la Tabla V y en la Figura 6."));
hijos.push(espacio()[0]);
hijos.push(tabla(
  ["Factor", "Riesgo expuestas", "Riesgo no expuestas", "Dif. riesgo (IC95%)", "OR (IC95%)", "p"],
  D.fisher_significativa.map((f) => [
    f.factor, f.r1_txt, f.r0_txt, f.dr_txt, `${f.or_txt} (${f.or_ic_txt})`,
    f.sig ? [[f.p, { bold: true, color: "B5442A" }]] : f.p,
  ]),
  [2400, 1200, 1300, 1700, 1500, 926],
));
hijos.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { before: 90, after: 160 },
  children: [new TextRun({ text: "Tabla V. Factores asociados a radiodermitis significativa (≥ grado 2).", size: 17, italics: true, color: "555555", font: "Calibri" })],
}));
const fs2 = D.fisher_significativa[0];
const fg2 = D.fisher_significativa.find((x) => x.factor.startsWith("Irradiación"));
hijos.push(p(`El normofraccionamiento volvió a mostrarse como el factor de mayor peso, con una incidencia de radiodermitis significativa del ${fs2.r1_txt} frente al ${fs2.r0_txt} en el grupo hipofraccionado (OR ${fs2.or_txt}, IC95% ${fs2.or_ic_txt}; p = ${fs2.p}). La diferencia de riesgo asciende a ${fs2.dr_txt} puntos porcentuales, magnitud de indudable relevancia clínica. La irradiación ganglionar mostró una tendencia en el mismo sentido sin alcanzar significación (${fg2.r1_txt} frente a ${fg2.r0_txt}; p = ${fg2.p}), resultado esperable dada su colinealidad con el fraccionamiento.`));
hijos.push(p("Cabe destacar que la sobreimpresión del lecho tumoral, clásicamente considerada un factor de riesgo de toxicidad cutánea, no se asoció a un mayor grado de radiodermitis en esta serie, probablemente porque se administra tras la finalización de la fase de irradiación de la mama completa y sobre un volumen reducido."));
hijos.push(...figura("fig6_forest_significativa.png", "Figura 6. Diagrama de bosque de los factores predictores de radiodermitis significativa (≥ grado 2). Representación en escala logarítmica con intervalos de confianza exactos del 95 %.", 560));

hijos.push(h2("3.4. Análisis de supervivencia libre de radiodermitis"));
const km = D.km_global;
hijos.push(p(`Se registraron ${km.eventos} eventos y ${km.censurados} observaciones censuradas. La Figura 7 representa la curva de Kaplan-Meier de supervivencia libre de radiodermitis para el conjunto de la cohorte, junto con la tabla de pacientes en riesgo en cada semana. La probabilidad de permanecer libre de toxicidad cutánea descendió de forma progresiva a lo largo del tratamiento, con una mediana de supervivencia libre de radiodermitis de ${km.mediana} semanas.`));
hijos.push(espacio()[0]);
hijos.push(tabla(
  ["Semana", "En riesgo", "Eventos", "Censuradas", "Superv. libre de RD", "IC95%", "Incidencia acum."],
  km.tabla.map((r) => [String(r.t), String(r.n), String(r.ev), String(r.cen),
    r.S_txt, r.ic_txt, r.inc_txt]),
  [1000, 1200, 1150, 1300, 1900, 1500, 976],
));
hijos.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { before: 90, after: 160 },
  children: [new TextRun({ text: "Tabla VI. Tabla de supervivencia libre de radiodermitis (estimador de Kaplan-Meier). Intervalos de confianza calculados por transformación log-log.", size: 17, italics: true, color: "555555", font: "Calibri" })],
}));
const t3 = km.tabla.find((r) => r.t === 3), t4 = km.tabla.find((r) => r.t === 4);
hijos.push(p(`Al finalizar la tercera semana de tratamiento, el ${t3.S_txt} de las pacientes permanecía libre de radiodermitis (IC95% ${t3.ic_txt}); en la cuarta semana esta proporción había descendido al ${t4.S_txt} (IC95% ${t4.ic_txt}), lo que refleja que es en ese intervalo cuando se concentra la aparición de la toxicidad cutánea.`));
hijos.push(...figura("fig7_km_global.png", "Figura 7. Curva de Kaplan-Meier de supervivencia libre de radiodermitis de cualquier grado en el conjunto de la cohorte. La banda sombreada representa el intervalo de confianza del 95 %; las marcas verticales indican observaciones censuradas y la línea discontinua la mediana.", 470));

const kf = D.km_fraccionamiento;
hijos.push(p(`La comparación entre esquemas de fraccionamiento se presenta en la Figura 8. Las pacientes normofraccionadas alcanzaron una mediana de supervivencia libre de radiodermitis de ${kf.mediana_normo} semanas y las hipofraccionadas de ${kf.mediana_hipo} semanas. Aunque la curva del grupo normofraccionado desciende más abruptamente a partir de la tercera semana, hasta alcanzar el 0 % en la quinta, la diferencia no alcanzó significación estadística (log-rank: χ² = ${kf.chi2.toFixed(2).replace(".", ",")}; p = ${kf.p}), con un hazard ratio estimado de ${kf.hr.toFixed(2).replace(".", ",")}.`));
hijos.push(p(`Este resultado matiza de forma relevante los hallazgos previos: el fraccionamiento se asocia a la gravedad de la radiodermitis y a su aparición considerada globalmente, pero no se ha demostrado que modifique la velocidad con la que ésta se instaura. Tampoco se observaron diferencias en función de la irradiación ganglionar (log-rank p = ${D.km_ganglionar.p}).`));
hijos.push(p(`El análisis de sensibilidad, censurando a las pacientes libres de evento al finalizar la radioterapia en lugar de en la primera visita posterior, mantuvo la mediana en ${D.km_sensibilidad.mediana} semanas y la ausencia de significación (p = ${D.km_sensibilidad.p}). No obstante, la magnitud del estadístico de log-rank resultó muy sensible al criterio de censura, lo que evidencia la fragilidad del análisis temporal con el número de eventos disponible.`));
hijos.push(...figura("fig8_km_fraccionamiento.png", "Figura 8. Curvas de Kaplan-Meier de supervivencia libre de radiodermitis según el esquema de fraccionamiento, con la tabla de pacientes en riesgo por grupo. Comparación mediante test de log-rank.", 470));

hijos.push(h2("3.5. Síntesis de los resultados"));
hijos.push(vinneta(`La radiodermitis aguda afectó a dos de cada tres pacientes (${rd1.txt}), alcanzando grado 2 o superior en el ${rd2.pct.toFixed(1).replace(".", ",")} % de la cohorte.`));
hijos.push(vinneta(`El normofraccionamiento fue el único factor asociado de forma significativa tanto a la aparición de radiodermitis (p = ${fa.p}) como a su forma significativa (p = ${fs2.p}), con diferencias de riesgo de gran magnitud.`));
hijos.push(vinneta(`La mediana de supervivencia libre de radiodermitis fue de ${km.mediana} semanas, concentrándose la aparición de la toxicidad entre las semanas 3 y 4 del tratamiento.`));
hijos.push(vinneta("Las reacciones de mayor grado se manifestaron más tardíamente, en consonancia con un efecto acumulativo de la dosis."));
hijos.push(vinneta("No se demostraron diferencias significativas en el tiempo hasta la aparición de la toxicidad entre esquemas de fraccionamiento."));

hijos.push(h2("3.6. Limitaciones"));
hijos.push(p(`El presente análisis debe interpretarse a la luz de varias limitaciones. En primer lugar, el tamaño muestral (${D.N} pacientes, ${km.eventos} eventos) confiere una potencia estadística reducida, de modo que la ausencia de significación no permite descartar asociaciones reales de magnitud moderada; los intervalos de confianza obtenidos son, en consecuencia, amplios.`));
hijos.push(p("En segundo lugar, y de forma determinante, el esquema de fraccionamiento y la irradiación de volúmenes ganglionares están casi perfectamente confundidos en esta serie, por lo que el efecto atribuido al primero podría corresponder en realidad al mayor volumen irradiado, a la dosis total acumulada o a la combinación de ambos. Discriminar estas contribuciones exigiría una serie mayor y un modelo multivariable, inviable con los datos disponibles."));
hijos.push(p("En tercer lugar, la semana de aparición se registró en unidades enteras, lo que introduce una censura por intervalo no modelada por el estimador de Kaplan-Meier, que asume tiempos exactos. Adicionalmente, todas las observaciones censuradas pertenecen al grupo hipofraccionado, lo que limita la comparación de curvas más allá de la cuarta semana."));
hijos.push(p("Por último, el carácter retrospectivo del estudio y la ausencia de corrección por comparaciones múltiples obligan a considerar estos resultados como exploratorios y generadores de hipótesis, que requieren confirmación en series prospectivas de mayor tamaño."));

hijos.push(h2("3.7. Conclusiones"));
hijos.push(p(`La radiodermitis aguda constituyó un efecto adverso frecuente en esta cohorte, afectando a dos de cada tres pacientes y alcanzando intensidad clínicamente relevante en más del cuarenta por ciento. El normofraccionamiento se asoció de forma consistente a una mayor incidencia y gravedad de la toxicidad cutánea, hallazgo concordante con la evidencia disponible sobre el mejor perfil de tolerancia cutánea de los esquemas hipofraccionados, si bien la confusión con la irradiación ganglionar impide atribuir el efecto de manera inequívoca al fraccionamiento.`));
hijos.push(p(`Desde una perspectiva asistencial, el patrón temporal identificado —con una mediana de supervivencia libre de radiodermitis de ${km.mediana} semanas y una concentración de los eventos entre las semanas tercera y cuarta— respalda la intensificación de la vigilancia dermatológica y de las medidas profilácticas en ese intervalo, particularmente en las pacientes que reciben esquemas normofraccionados con irradiación ganglionar.`));

hijos.push(h2("3.8. Recomendaciones para la recogida de datos"));
hijos.push(p("Del proceso de depuración se derivan varias recomendaciones orientadas a mejorar la calidad de futuros registros:"));
hijos.push(vinneta("Establecer un código explícito y unívoco para los valores ausentes, evitando el uso de cifras plausibles (como 0 o 99) que puedan confundirse con determinaciones reales."));
hijos.push(vinneta("Restringir mediante validación las columnas binarias a los valores Sí/No, impidiendo la introducción de texto libre o nombres de fármacos."));
hijos.push(vinneta("Homogeneizar la nomenclatura TNM, separando el prefijo (p/yp) de la categoría y registrando la multifocalidad, la micrometástasis y el ganglio centinela en campos independientes."));
hijos.push(vinneta("Incorporar reglas de coherencia automáticas entre el estadio anatómico y el pronóstico, así como entre el grado de toxicidad y su semana de presentación."));
hijos.push(vinneta("Registrar la fecha exacta de aparición de la toxicidad, en lugar de la semana, para permitir análisis de supervivencia con tiempos precisos."));

// ------------------------------------------------------------------ //
const doc = new Document({
  creator: "Servicio de Oncología Radioterápica",
  title: "Radiodermitis aguda en cáncer de mama tratado con radioterapia",
  description: "Análisis descriptivo, inferencial y de supervivencia",
  numbering: {
    config: [{
      reference: "vinnetas",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: {
          paragraph: {
            indent: { left: convertInchesToTwip(0.3), hanging: convertInchesToTwip(0.18) },
          },
        },
      }],
    }],
  },
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 21 } },
    },
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({
            children: ["Página ", PageNumber.CURRENT, " de ", PageNumber.TOTAL_PAGES],
            size: 16, color: "888888", font: "Calibri",
          })],
        })],
      }),
    },
    children: hijos,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const salida = path.join(BASE, "Informe_Radiodermitis.docx");
  fs.writeFileSync(salida, buf);
  console.log(`OK -> ${path.basename(salida)} (${(buf.length / 1024).toFixed(0)} KB)`);
});

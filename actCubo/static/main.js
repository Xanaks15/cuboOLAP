/**
 * ============================================================
 * UTILIDADES GENERALES
 * ============================================================
 */

/**
 * Realiza una solicitud HTTP GET a un endpoint y devuelve el resultado en JSON.
 *
 * @async
 * @function fetchJSON
 * @param {string} url - URL del endpoint a consultar.
 * @returns {Promise<Object>} Objeto Javascript con la respuesta JSON del servidor.
 */
async function fetchJSON(url) {
    const r = await fetch(url);
    return await r.json();
}


/**
 * Renderiza una tabla HTML dentro de un contenedor.
 *
 * @function renderTable
 * @param {string} containerId - ID del elemento donde se colocará la tabla.
 * @param {string[]} columns - Arreglo con los nombres de las columnas.
 * @param {Object[]} rows - Lista de registros (filas) donde cada registro es un diccionario.
 *
 * @description
 * - Aplica formato numérico: métricas con 2 decimales excepto Año, Trimestre, Cantidad.
 * - Si no hay datos, muestra “Sin datos”.
 * - Esta función es reutilizada por CARA, DICE, CUBO y CELDA.
 */
function renderTable(containerId, columns, rows) {
    const el = document.getElementById(containerId);

    if (!rows || rows.length === 0) {
        el.innerHTML = "<em>Sin datos</em>";
        return;
    }

    // Construcción del encabezado
    let thead = "<thead><tr>";
    for (const c of columns) thead += `<th>${c}</th>`;
    thead += "</tr></thead>";

    // Construcción del cuerpo
    let tbody = "<tbody>";
    for (const row of rows) {
        tbody += "<tr>";

        for (const c of columns) {
            let v = row[c];

            // Control de formato para números
            if (typeof v === "number") {
                if (!["año", "cantidad", "trimestre"].includes(c.toLowerCase())) {
                    v = v.toFixed(2);
                } else {
                    v = Math.trunc(v);
                }
            }

            tbody += `<td>${v ?? ""}</td>`;
        }
        tbody += "</tr>";
    }
    tbody += "</tbody>";

    el.innerHTML = `<table>${thead}${tbody}</table>`;
}



/**
 * ============================================================
 * 1. CARA DEL CUBO (SLICE 2D)
 * ============================================================
 *
 * Vista 2D que combina dos dimensiones: eje X y eje Y.
 * Usa el endpoint:
 *      GET /api/cara?dim_x=...&dim_y=...&metric=...
 */

document.addEventListener("DOMContentLoaded", () => {

    const caraSelect  = document.getElementById("cara-cubo");
    const inputX      = document.getElementById("cara-dimx");
    const inputY      = document.getElementById("cara-dimy");
    const inputMetric = document.getElementById("cara-metric");
    const output      = document.getElementById("cara-resultado");

    /**
     * Solicita una vista 2D del cubo al backend y renderiza la tabla.
     *
     * @async
     * @function generarCara
     * @returns {Promise<void>}
     */
    async function generarCara() {
        const dimX   = inputX.value;
        const dimY   = inputY.value;
        const metric = inputMetric.value;

        output.innerHTML = "<em>Cargando...</em>";

        try {
            const data = await fetchJSON(
                `/api/cara?dim_x=${dimX}&dim_y=${dimY}&metric=${metric}`
            );
            renderTable("cara-resultado", data.columns, data.data);
        } catch (error) {
            console.error("Error al generar la cara:", error);
            output.innerHTML = "<em>Error al cargar</em>";
        }
    }

    // Cambiar dimensiones según la cara seleccionada
    caraSelect.addEventListener("change", () => {
        const v = caraSelect.value;

        let dx = "Año", dy = "Región";

        if (v === "anio-canal")          { dx = "Año";      dy = "Canal"; }
        if (v === "producto-region")    { dx = "Producto"; dy = "Región"; }
        if (v === "producto-canal")     { dx = "Producto"; dy = "Canal"; }
        if (v === "trimestre-region")   { dx = "Trimestre";dy = "Región"; }
        if (v === "mes-region")         { dx = "Mes";       dy = "Región"; }

        inputX.value = dx;
        inputY.value = dy;

        generarCara();
    });

    // Actualizar cara al cambiar la métrica
    inputMetric.addEventListener("change", generarCara);

    // Inicial
    generarCara();
});


/**
 * ============================================================
 * 2. DICE (filtrado multidimensional)
 * ============================================================
 *
 * Usa el endpoint:
 *      GET /api/seccion?anios=...&regiones=...&productos=...&canales=...
 *
 * Retorna un subconjunto detallado sin agregación.
 */

document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-dice");
    const out = document.getElementById("dice-resultado");

    /**
     * Ejecuta la operación DICE sobre el cubo.
     *
     * @async
     * @function generarDice
     * @returns {Promise<void>}
     */
    async function generarDice() {
        const anios     = document.getElementById("dice-anios").value;
        const regiones  = document.getElementById("dice-regiones").value;
        const productos = document.getElementById("dice-productos").value;
        const canales   = document.getElementById("dice-canales").value;

        const params = new URLSearchParams();
        if (anios)     params.append("anios", anios);
        if (regiones)  params.append("regiones", regiones);
        if (productos) params.append("productos", productos);
        if (canales)   params.append("canales", canales);

        out.innerHTML = "<em>Cargando sección del cubo...</em>";

        try {
            const data = await fetchJSON(`/api/seccion?${params.toString()}`);
            renderTable("dice-resultado", data.columns, data.data);
        } catch (error) {
            console.error("Error al generar DICE:", error);
            out.innerHTML = "<em>Error al cargar datos</em>";
        }
    }

    btn.addEventListener("click", generarDice);
});



/**
 * ============================================================
 * 3. CUBO COMPLETO DINÁMICO (pivot OLAP configurable)
 * ============================================================
 *
 * Usa el endpoint:
 *      GET /api/cubo_dinamico?index=...&columns=...&metric=...
 *
 * Retorna un pivot_table con totales OLAP.
 */

document.addEventListener("DOMContentLoaded", async () => {

    const selIndex   = document.getElementById("cubo-index");
    const selColumns = document.getElementById("cubo-columns");
    const selMetric  = document.getElementById("cubo-metric");
    const btn        = document.getElementById("btn-cubo");
    const out        = document.getElementById("cubo-resultado");

    /**
     * Llena los selectores de dimensiones y métricas con información
     * proveniente del backend (/api/opciones).
     */
    const opts = await fetchJSON("/api/opciones");

    // Llenar selects
    opts.dimensiones.forEach(dim => {
        selIndex.add(new Option(dim, dim));
        selColumns.add(new Option(dim, dim));
    });

    opts.metricas.forEach(m => {
        selMetric.add(new Option(m, m));
    });

    // Selección inicial por defecto
    ["Producto","Región"].forEach(d => {
        const opt = [...selIndex.options].find(o => o.value === d);
        if (opt) opt.selected = true;
    });

    ["Año","Trimestre"].forEach(d => {
        const opt = [...selColumns.options].find(o => o.value === d);
        if (opt) opt.selected = true;
    });

    selMetric.value = "Ventas";

    /**
     * Obtiene los valores seleccionados de un <select multiple>.
     *
     * @function selectedValues
     * @param {HTMLSelectElement} sel
     * @returns {string[]} Lista de valores seleccionados.
     */
    function selectedValues(sel) {
        return [...sel.selectedOptions].map(o => o.value);
    }

    /**
     * Genera el cubo OLAP completo mediante pivot_table.
     *
     * @async
     * @function generarCubo
     * @returns {Promise<void>}
     */
    async function generarCubo() {
        out.innerHTML = "<em>Cargando cubo...</em>";

        const idx    = selectedValues(selIndex);
        const cols   = selectedValues(selColumns);
        const metric = selMetric.value;

        const params = new URLSearchParams({
            index: idx.join(","),
            columns: cols.join(","),
            metric
        });

        const data = await fetchJSON(`/api/cubo_dinamico?${params.toString()}`);

        renderTable("cubo-resultado", data.cols, data.data);
    }

    // Botón
    btn.addEventListener("click", generarCubo);
});



/**
 * ============================================================
 * 4. DETALLE DE UNA CELDA (drill-down)
 * ============================================================
 *
 * Usa el endpoint:
 *      GET /api/celda?dim_x=...&valor_x=...&dim_y=...&valor_y=...
 */

document.getElementById("btn-celda").addEventListener("click", async () => {
    const dx = document.getElementById("celda-dimx").value;
    const vx = document.getElementById("celda-valorx").value;
    const dy = document.getElementById("celda-dimy").value;
    const vy = document.getElementById("celda-valory").value;

    const params = new URLSearchParams({
        dim_x: dx,
        valor_x: vx,
        dim_y: dy,
        valor_y: vy
    });

    const data = await fetchJSON(`/api/celda?${params.toString()}`);

    renderTable("celda-resultado", data.columns, data.data);
});

/**
 * ============================================================
 * UTILIDADES GENERALES
 * ============================================================
 */

/** HTTP GET y JSON */
async function fetchJSON(url) {
    const r = await fetch(url);
    return await r.json();
}

/** Renderización general de tablas HTML */
function renderTable(containerId, columns, rows) {
    const el = document.getElementById(containerId);

    if (!rows || rows.length === 0) {
        el.innerHTML = "<em>Sin datos</em>";
        return;
    }

    let thead = "<thead><tr>";
    columns.forEach(c => thead += `<th>${c}</th>`);
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    rows.forEach(row => {
        tbody += "<tr>";
        columns.forEach(col => {
            let v = row[col];

            if (typeof v === "number") {
                if (!["año","cantidad","trimestre"].includes(col.toLowerCase())) {
                    v = v.toFixed(2);
                } else {
                    v = Math.trunc(v);
                }
            }

            tbody += `<td>${v ?? ""}</td>`;
        });
        tbody += "</tr>";
    });
    tbody += "</tbody>";

    el.innerHTML = `<table>${thead}${tbody}</table>`;
}


/**
 * ============================================================
 * 1. CARA DEL CUBO (SLICE 2D)
 * ============================================================
 */

document.addEventListener("DOMContentLoaded", () => {

    const caraSelect  = document.getElementById("cara-cubo");
    const inputX      = document.getElementById("cara-dimx");
    const inputY      = document.getElementById("cara-dimy");
    const inputMetric = document.getElementById("cara-metric");
    const output      = document.getElementById("cara-resultado");

    // 1. Cargar métricas ANTES DE CUALQUIER OTRA COSA
    fetchJSON("/api/opciones").then(opts => {

        // Llenar select de métricas
        opts.metricas.forEach(m => {
            inputMetric.add(new Option(m, m));
        });

        // Asignar valor inicial
        inputMetric.value = "Ventas";

        // 🔥 AHORA SÍ — Ejecutar la primera carga
        generarCara();
    });

    async function generarCara() {
        const dimX   = inputX.value;
        const dimY   = inputY.value;
        const metric = inputMetric.value || "Ventas";  // Backup extra por si acaso

        output.innerHTML = "<em>Cargando...</em>";

        try {
            const data = await fetchJSON(`/api/cara?dim_x=${dimX}&dim_y=${dimY}&metric=${metric}`);
            renderTable("cara-resultado", data.columns, data.data);
        } catch (error) {
            console.error("Error al generar la cara:", error);
            output.innerHTML = "<em>Error al cargar</em>";
        }
    }

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

    inputMetric.addEventListener("change", generarCara);
});


/**
 * ============================================================
 * 2. DICE
 * ============================================================
 */
document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-dice");
    const out = document.getElementById("dice-resultado");

    async function generarDice() {
        const anios     = document.getElementById("dice-anios").value;
        const regiones  = document.getElementById("dice-regiones").value;
        const productos = document.getElementById("dice-productos").value;
        const canales   = document.getElementById("dice-canales").value;

        const params = new URLSearchParams();
        if (anios) params.append("anios", anios);
        if (regiones) params.append("regiones", regiones);
        if (productos) params.append("productos", productos);
        if (canales) params.append("canales", canales);

        out.innerHTML = "<em>Cargando...</em>";

        try {
            const data = await fetchJSON(`/api/seccion?${params.toString()}`);
            renderTable("dice-resultado", data.columns, data.data);
        } catch (err) {
            out.innerHTML = "<em>Error al cargar</em>";
        }
    }

    btn.addEventListener("click", generarDice);
});


/**
 * ============================================================
 * 3. CUBO DINÁMICO
 * ============================================================
 */
document.addEventListener("DOMContentLoaded", async () => {

    const selIndex   = document.getElementById("cubo-index");
    const selColumns = document.getElementById("cubo-columns");
    const selMetric  = document.getElementById("cubo-metric");
    const btn        = document.getElementById("btn-cubo");
    const out        = document.getElementById("cubo-resultado");

    const opts = await fetchJSON("/api/opciones");

    opts.dimensiones.forEach(dim => {
        selIndex.add(new Option(dim, dim));
        selColumns.add(new Option(dim, dim));
    });

    opts.metricas.forEach(m => selMetric.add(new Option(m, m)));
    selMetric.value = "Ventas";

    function selectedValues(sel) {
        return [...sel.selectedOptions].map(o => o.value);
    }

    async function generarCubo() {
        out.innerHTML = "<em>Cargando cubo...</em>";

        const idx = selectedValues(selIndex);
        const cols = selectedValues(selColumns);
        const metric = selMetric.value;

        const params = new URLSearchParams({
            index: idx.join(","),
            columns: cols.join(","),
            metric
        });

        const data = await fetchJSON(`/api/cubo_dinamico?${params.toString()}`);

        renderTable("cubo-resultado", data.cols, data.data);
    }

    btn.addEventListener("click", generarCubo);
});


/**
 * ============================================================
 * 4. DETALLE DE CELDA (DRILL)
 * ============================================================
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

async function fetchJSON(url) {

/**
    Realiza una petición HTTP GET a una URL y devuelve el resultado como JSON.

    Args:
    url (string): URL a consultar mediante fetch.

    Returns:
    Promise<object>: Promesa que resuelve al objeto JSON resultante de la petición.
 */

    const r = await fetch(url);
    return await r.json();
}

function renderTable(containerId, columns, rows) {

/**
    Renderiza una tabla HTML en un contenedor usando columnas y filas proporcionadas.

    Args:
    containerId (string): ID del elemento HTML donde se insertará la tabla.
    columns (Array<string>): Lista de nombres de columnas.
    rows (Array<object>): Arreglo de objetos que representan las filas.

    Returns:
    void: No retorna valor; modifica el DOM insertando la tabla en el contenedor.
 */

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

document.addEventListener("DOMContentLoaded", () => {

/**
    Inicializa la lógica para mostrar una cara (slice 2D) del cubo OLAP.

    Args:
    event (Event): Evento DOMContentLoaded (no se usa directamente).

    Returns:
    void: Configura eventos y carga inicial en el DOM.
 */

    const caraSelect  = document.getElementById("cara-cubo");
    const inputX      = document.getElementById("cara-dimx");
    const inputY      = document.getElementById("cara-dimy");
    const inputMetric = document.getElementById("cara-metric");
    const output      = document.getElementById("cara-resultado");

    fetchJSON("/api/opciones").then(opts => {
        opts.metricas.forEach(m => {
            inputMetric.add(new Option(m, m));
        });

        inputMetric.value = "Ventas";

        generarCara();
    });

    async function generarCara() {

/**
    Genera y muestra una “cara” (slice) del cubo OLAP según dos dimensiones y una métrica.

    Args:
    Ninguno directo: utiliza valores actuales de los elementos del DOM (inputX, inputY, inputMetric).

    Returns:
    Promise<void>: No retorna valor; actualiza el contenido HTML del contenedor de resultado.
 */

        const dimX   = inputX.value;
        const dimY   = inputY.value;
        const metric = inputMetric.value || "Ventas";

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

        if (v === "anio-canal")        { dx = "Año";      dy = "Canal"; }
        if (v === "producto-region")   { dx = "Producto"; dy = "Región"; }
        if (v === "producto-canal")    { dx = "Producto"; dy = "Canal"; }
        if (v === "trimestre-region")  { dx = "Trimestre";dy = "Región"; }
        if (v === "mes-region")        { dx = "Mes";      dy = "Región"; }

        inputX.value = dx;
        inputY.value = dy;

        generarCara();
    });

    inputMetric.addEventListener("change", generarCara);
});

document.addEventListener("DOMContentLoaded", () => {

/**
    Inicializa la lógica para generar una sección (DICE) del cubo mediante filtros.

    Args:
    event (Event): Evento DOMContentLoaded (no se usa directamente).

    Returns:
    void: Configura el botón y el comportamiento de filtrado en el DOM.
 */

    const btn = document.getElementById("btn-dice");
    const out = document.getElementById("dice-resultado");

    async function generarDice() {

/**
    Genera una sección (DICE) del cubo filtrando por múltiples dimensiones opcionales.

    Args:
    Ninguno directo: lee los valores desde los campos del DOM para construir los filtros.

    Returns:
    Promise<void>: No retorna valor; muestra el resultado de la sección en una tabla HTML.
 */

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

document.addEventListener("DOMContentLoaded", async () => {

/**
    Inicializa la lógica del cubo dinámico, permitiendo elegir dimensiones para filas y columnas.

    Args:
    event (Event): Evento DOMContentLoaded (no se usa directamente).

    Returns:
    void: Configura selects, métricas y botón para generar el cubo dinámico.
 */

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

/**
    Obtiene los valores seleccionados en un elemento <select> (posiblemente múltiple).

    Args:
    sel (HTMLSelectElement): Elemento select del que se tomarán las opciones seleccionadas.

    Returns:
    Array<string>: Lista de valores seleccionados.
 */

        return [...sel.selectedOptions].map(o => o.value);
    }

    async function generarCubo() {

/**
    Construye y muestra un cubo dinámico usando dimensiones elegidas como índices y columnas.

    Args:
    Ninguno directo: utiliza los valores seleccionados en los elementos del DOM.

    Returns:
    Promise<void>: No retorna valor; renderiza la tabla del cubo dinámico en el DOM.
 */

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

document.getElementById("btn-celda").addEventListener("click", async () => {

/**
    Maneja el evento de clic del botón de detalle de celda para obtener el drill-down.

    Args:
    event (MouseEvent): Evento de clic (no se usa directamente).

    Returns:
    void: Dispara la consulta de detalle de celda y actualiza la tabla en el DOM.
 */

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

async function fetchJSON(url) {
    const res = await fetch(url);
    return await res.json();
}


function renderTable(containerId, columns, rows) {
    const container = document.getElementById(containerId);
    if (!rows || rows.length === 0) {
        container.innerHTML = "<em>Sin datos</em>";
        return;
    }

    let thead = "<thead><tr>";
    for (const col of columns) {
        thead += `<th>${col}</th>`;
    }
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    for (const row of rows) {
        tbody += "<tr>";
        for (const col of columns) {
            let value = row[col];

            // 👇 aquí controlamos los decimales
            if (typeof value === "number") {
                value = value.toFixed(2); // fuerza 2 decimales
            }

            tbody += `<td>${value !== undefined ? value : ""}</td>`;
        }
        tbody += "</tr>";
    }
    tbody += "</tbody>";

    const tableHTML = `<table>${thead}${tbody}</table>`;
    container.innerHTML = tableHTML;
}

// 1. Cara del cubo
document.getElementById("btn-cara").addEventListener("click", async () => {
    const dim_x = document.getElementById("cara-dimx").value;
    const dim_y = document.getElementById("cara-dimy").value;
    const metric = document.getElementById("cara-metric").value;

    const url = `/api/cara?dim_x=${encodeURIComponent(dim_x)}&dim_y=${encodeURIComponent(dim_y)}&metric=${encodeURIComponent(metric)}`;
    const data = await fetchJSON(url);

    renderTable("cara-resultado", data.columns, data.data);
});

// 2. Sección / slice
document.getElementById("btn-seccion").addEventListener("click", async () => {
    const filtro_dim = document.getElementById("sec-dim").value;
    const filtro_valor = document.getElementById("sec-valor").value;

    const url = `/api/seccion?filtro_dim=${encodeURIComponent(filtro_dim)}&filtro_valor=${encodeURIComponent(filtro_valor)}`;
    const data = await fetchJSON(url);

    renderTable("seccion-resultado", data.columns, data.data);
});

// 3. Cubo completo
document.getElementById("btn-cubo").addEventListener("click", async () => {
    const data = await fetchJSON("/api/cubo");

    // data es {vista1: [...], vista2:[...], ...}
    const container = document.getElementById("cubo-resultado");
    container.innerHTML = "";

    Object.entries(data).forEach(([vistaNombre, rows]) => {
        if (!rows || rows.length === 0) return;

        const cols = Object.keys(rows[0]);

        const block = document.createElement("div");
        block.style.marginBottom = "1rem";

        const title = document.createElement("div");
        title.style.color = "#38bdf8";
        title.style.fontWeight = "600";
        title.style.fontSize = ".8rem";
        title.style.margin = ".5rem 0";
        title.textContent = vistaNombre;
        block.appendChild(title);

        const tableWrapper = document.createElement("div");
        const tmpId = `tbl-${vistaNombre}`;
        tableWrapper.id = tmpId;
        block.appendChild(tableWrapper);

        container.appendChild(block);

        // renderizar tabla dentro de cada bloque
        renderTable(tmpId, cols, rows);
    });
});

// 4. Detalle de una celda
document.getElementById("btn-celda").addEventListener("click", async () => {
    const dim_x = document.getElementById("celda-dimx").value;
    const valor_x = document.getElementById("celda-valorx").value;
    const dim_y = document.getElementById("celda-dimy").value;
    const valor_y = document.getElementById("celda-valory").value;

    const url = `/api/celda?dim_x=${encodeURIComponent(dim_x)}&valor_x=${encodeURIComponent(valor_x)}&dim_y=${encodeURIComponent(dim_y)}&valor_y=${encodeURIComponent(valor_y)}`;
    const data = await fetchJSON(url);

    renderTable("celda-resultado", data.columns, data.data);
});


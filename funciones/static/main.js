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
document.addEventListener("DOMContentLoaded", function () {
    const caraSelect = document.getElementById("cara-cubo");
    const inputDimX = document.getElementById("cara-dimx");
    const inputDimY = document.getElementById("cara-dimy");
    const inputMetric = document.getElementById("cara-metric");
    const divResultado = document.getElementById("cara-resultado");
  
    // Si la sección de cara no existe (por ejemplo, en otras páginas), salir
    if (!caraSelect || !inputDimX || !inputDimY || !divResultado) return;
  
    // 🧩 Función local para mostrar tabla
    function renderTable(data, columns, containerId) {
      const container = document.getElementById(containerId);
      if (!data || data.length === 0) {
        container.innerHTML = "<em>Sin datos</em>";
        return;
      }
  
      let html = "<table><thead><tr>";
      columns.forEach(c => html += `<th>${c}</th>`);
      html += "</tr></thead><tbody>";
  
      data.forEach(row => {
        html += "<tr>";
        columns.forEach(col => {
          let value = row[col];
          if (typeof value === "number" && !["año", "cantidad"].includes(col.toLowerCase())) {
            value = value.toFixed(2);
          }
          html += `<td>${value !== undefined ? value : ""}</td>`;
        });
        html += "</tr>";
      });
  
      html += "</tbody></table>";
      container.innerHTML = html;
    }
  
    // 🧩 Función local para generar cara
    async function generarCara() {
      const dimX = inputDimX.value;
      const dimY = inputDimY.value;
      const metric = inputMetric.value;
  
      divResultado.innerHTML = "<em>Cargando...</em>";
  
      try {
        const res = await fetch(`/api/cara?dim_x=${dimX}&dim_y=${dimY}&metric=${metric}`);
        const data = await res.json();
        renderTable(data.data, data.columns, "cara-resultado");
      } catch (error) {
        console.error("Error al generar la cara:", error);
        divResultado.innerHTML = "<em>Error al cargar datos</em>";
      }
    }
  
    // 🧩 Cambios de cara: actualiza ejes y genera
    caraSelect.addEventListener("change", function () {
      const opcion = this.value;
      let dimX = "Año";
      let dimY = "Región";
  
      switch (opcion) {
        case "anio-canal": dimX = "Año"; dimY = "Canal"; break;
        case "producto-region": dimX = "Producto"; dimY = "Región"; break;
        case "producto-canal": dimX = "Producto"; dimY = "Canal"; break;
        case "trimestre-region": dimX = "Trimestre"; dimY = "Región"; break;
        case "mes-region": dimX = "Mes"; dimY = "Región"; break;
      }
  
      inputDimX.value = dimX;
      inputDimY.value = dimY;
      generarCara();
    });
  
    // 🧩 También volver a generar si cambia la métrica
    inputMetric.addEventListener("change", generarCara);
  
    // 🧩 Generar al cargar la página (una sola vez)
    generarCara();
  });
  document.addEventListener("DOMContentLoaded", function () {
    const btnDice = document.getElementById("btn-dice");
    const resultDice = document.getElementById("dice-resultado");
  
    if (!btnDice || !resultDice) return; // por si no existe en la página
  
    async function generarDice() {
      const anios = document.getElementById("dice-anios").value.trim();
      const regiones = document.getElementById("dice-regiones").value.trim();
      const productos = document.getElementById("dice-productos").value.trim();
      const canales = document.getElementById("dice-canales").value.trim();
      const metric = document.getElementById("dice-metric").value.trim() || "Ventas";
  
      // construir URL con filtros
      const params = new URLSearchParams();
      if (anios) params.append("anios", anios);
      if (regiones) params.append("regiones", regiones);
      if (productos) params.append("productos", productos);
      if (canales) params.append("canales", canales);
      params.append("metric", metric);
  
      resultDice.innerHTML = "<em>Cargando sección del cubo...</em>";
  
      try {
        const res = await fetch(`/api/seccion?${params.toString()}`);
        const data = await res.json();
  
        if (!data.data || data.data.length === 0) {
          resultDice.innerHTML = "<em>Sin datos para los filtros seleccionados</em>";
          return;
        }
  
        renderTable("dice-resultado", data.columns, data.data);
      } catch (error) {
        console.error("Error al generar sección del cubo (DICE):", error);
        resultDice.innerHTML = "<em>Error al cargar datos</em>";
      }
    }
  
    btnDice.addEventListener("click", generarDice);
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


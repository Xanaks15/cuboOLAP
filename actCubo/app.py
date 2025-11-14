from flask import Flask, request, render_template, Response
import pandas as pd
import json
from generarDatos import generar_dataset

app = Flask(__name__, template_folder="templates", static_folder="static")

# ============================================================
# DATASET GLOBAL
# ============================================================
# Se genera una sola vez para simular un cubo OLAP estático.
DATA_DF = generar_dataset(seed=42)
pd.options.display.float_format = "{:.2f}".format


# ============================================================
# UTILIDAD: JSON SEGURO
# ============================================================
def safe_json(data):
    """
    Convierte estructuras Python/Pandas en una respuesta JSON segura.
    
    Args:
        data (object): Diccionario, DataFrame, lista o cualquier estructura serializable.

    Returns:
        Response: Objeto HTTP con el JSON serializado.
    """
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        content_type="application/json"
    )


# ============================================================
# 1) CARA DEL CUBO (SLICE 2D)
# ============================================================
def cara_del_cubo(df, dim_x, dim_y, metric):
    """
    Genera una "cara" del cubo: tabla 2D agregada.

    Args:
        df (DataFrame): Dataset del cubo OLAP.
        dim_x (str): Dimensión colocada en columnas.
        dim_y (str): Dimensión colocada en filas.
        metric (str): Métrica a agregar (sum).

    Returns:
        DataFrame: Tabla pivot 2D indexada por dim_y y columnas = dim_x.
    """
    tabla = pd.pivot_table(
        df,
        values=metric,
        index=[dim_y],
        columns=[dim_x],
        aggfunc="sum",
        margins=False
    ).reset_index().fillna(0)

    return tabla


# ============================================================
# 2) DICE: Filtrado multidimensional
# ============================================================
def dice_subset(df, anios=None, regiones=None, productos=None, canales=None):
    """
    Realiza un DICE (subcubo filtrado sin agregación).

    Args:
        df (DataFrame): Dataset global.
        anios (list[int] | None): Lista de años a incluir.
        regiones (list[str] | None): Lista de regiones a incluir.
        productos (list[str] | None): Lista de productos a incluir.
        canales (list[str] | None): Lista de canales a incluir.

    Returns:
        DataFrame: Subconjunto detallado con las filas que cumplen los filtros.
    """
    m = pd.Series([True] * len(df))

    if anios is not None:
        if not isinstance(anios, list):
            anios = [anios]
        m &= df["Año"].isin(anios)

    if regiones is not None:
        if not isinstance(regiones, list):
            regiones = [regiones]
        m &= df["Región"].isin(regiones)

    if productos is not None:
        if not isinstance(productos, list):
            productos = [productos]
        m &= df["Producto"].isin(productos)

    if canales is not None:
        if not isinstance(canales, list):
            canales = [canales]
        m &= df["Canal"].isin(canales)

    # Filtrado final
    sub = df.loc[m].copy()

    # Columnas a mostrar
    columnas = ["Año", "Trimestre", "Mes", "Región", "Canal",
                "Producto", "Cantidad", "Ventas"]
    columnas = [c for c in columnas if c in sub.columns]
    sub = sub[columnas]

    # Redondeo
    sub["Ventas"] = sub["Ventas"].round(2)
    if "Cantidad" in sub.columns:
        sub["Cantidad"] = sub["Cantidad"].astype(int)

    return sub


# ============================================================
# 3) CUBO COMPLETO DINÁMICO (PIVOT)
# ============================================================
def flatten_cols(cols):
    """
    Convierte MultiIndex de columnas en nombres legibles.

    Args:
        cols (iterable): Columnas originales (posiblemente MultiIndex).

    Returns:
        list[str]: Lista de nombres de columnas simplificados.
    """
    out = []
    for col in cols:
        if isinstance(col, tuple):
            a, b = col
            if b and str(b).isdigit():
                out.append(f"{a}-T{b}")
            else:
                out.append(str(a))
        else:
            out.append(str(col))
    return out


@app.route("/api/opciones")
def api_opciones():
    """
    Devuelve las dimensiones disponibles y las métricas posibles.

    Returns:
        JSON: { dimensiones: [...], metricas: [...] }
    """
    dims = ["Año", "Trimestre", "Mes", "Región", "Canal", "Producto"]
    return safe_json({
        "dimensiones": dims,
        "metricas": ["Ventas", "Cantidad"]
    })


@app.route("/api/cubo_dinamico")
def api_cubo_dinamico():
    """
    Construye un pivot OLAP configurable.
    
    Query params:
        index (str): Dimensiones separadas por coma para filas.
        columns (str): Dimensiones para columnas.
        metric (str): Métrica a agregar.

    Returns:
        JSON: {
          index: [...],
          columns: [...],
          metric: "...",
          cols: columnas resultantes,
          data: filas de la tabla pivot
        }
    """
    index = request.args.get("index", "Producto,Región")
    columns = request.args.get("columns", "Año,Trimestre")
    metric = request.args.get("metric", "Ventas")

    idx = [x for x in index.split(",") if x.strip()]
    cols = [x for x in columns.split(",") if x.strip()]

    tabla = pd.pivot_table(
        DATA_DF,
        values=metric,
        index=idx if idx else None,
        columns=cols if cols else None,
        aggfunc="sum",
        margins=True,         # ← SIEMPRE incluye totales OLAP
        margins_name="Total"
    ).reset_index().fillna(0)

    tabla = tabla.round(2)
    tabla.columns = flatten_cols(tabla.columns)

    return safe_json({
        "index": idx,
        "columns": cols,
        "metric": metric,
        "cols": tabla.columns.tolist(),
        "data": tabla.to_dict(orient="records")
    })


# ============================================================
# 4) DETALLE DE UNA CELDA (DRILL)
# ============================================================
def detalle_celda(df, dim_x, valor_x, dim_y, valor_y):
    """
    Devuelve las filas del dataset que coinciden con una celda
    específica del cubo OLAP.

    Args:
        df (DataFrame): Dataset.
        dim_x (str): Dimensión horizontal.
        valor_x (str|int): Valor de la dimensión X.
        dim_y (str): Dimensión vertical.
        valor_y (str|int): Valor de la dimensión Y.

    Returns:
        DataFrame: Filas detalladas que corresponden a esa celda.
    """
    try: valor_x = int(valor_x)
    except: pass

    try: valor_y = int(valor_y)
    except: pass

    mask = (df[dim_x] == valor_x) & (df[dim_y] == valor_y)
    sub = df[mask].copy()

    columnas = ["Año", "Trimestre", "Mes", "Región",
                "Canal", "Producto", "Cantidad", "Ventas"]
    columnas = [c for c in columnas if c in sub.columns]

    return sub[columnas]


# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/")
def index():
    """Carga la página principal."""
    return render_template("index.html")


@app.route("/api/cara")
def api_cara():
    """
    Endpoint: Vista 2D del cubo.

    Query:
        dim_x, dim_y, metric

    Returns:
        JSON con columnas y datos pivotados.
    """
    dim_x = request.args.get("dim_x", "Año")
    dim_y = request.args.get("dim_y", "Región")
    metric = request.args.get("metric", "Ventas")

    tabla = cara_del_cubo(DATA_DF, dim_x, dim_y, metric)

    return safe_json({
        "dim_x": dim_x,
        "dim_y": dim_y,
        "metric": metric,
        "columns": list(map(str, tabla.columns)),
        "data": tabla.to_dict(orient="records")
    })


@app.route("/api/seccion")
def api_seccion():
    """
    Endpoint: DICE (filtros múltiples).

    Query:
        anios, regiones, productos, canales

    Returns:
        JSON con columnas y datos filtrados sin agregación.
    """
    parse_list = lambda x: x.split(",") if x else None

    anios = parse_list(request.args.get("anios"))
    regiones = parse_list(request.args.get("regiones"))
    productos = parse_list(request.args.get("productos"))
    canales = parse_list(request.args.get("canales"))

    if anios:
        try:
            anios = [int(a) for a in anios]
        except:
            pass

    tabla = dice_subset(DATA_DF, anios, regiones, productos, canales)

    return safe_json({
        "columns": tabla.columns.tolist(),
        "data": tabla.to_dict(orient="records")
    })


@app.route("/api/celda")
def api_celda():
    """
    Endpoint: detalle Drill-Down de una celda.

    Query:
        dim_x, valor_x, dim_y, valor_y

    Returns:
        JSON: filas completas que cumplen esa combinación.
    """
    dim_x = request.args.get("dim_x", "Año")
    valor_x = request.args.get("valor_x", "2024")
    dim_y = request.args.get("dim_y", "Región")
    valor_y = request.args.get("valor_y", "Norte")

    tabla = detalle_celda(DATA_DF, dim_x, valor_x, dim_y, valor_y)

    return safe_json({
        "columns": tabla.columns.tolist(),
        "data": tabla.to_dict(orient="records")
    })


if __name__ == "__main__":
    app.run(debug=True)

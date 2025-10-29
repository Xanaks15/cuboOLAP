from flask import Flask, request, render_template
import pandas as pd
import json
import numpy as np
from flask import Response

# Importa tus módulos reales:
from generarDatos import generar_dataset
# opcionalmente puedes importar helpers de crearCubo / operacionesCubo si quieres usarlos internamente

app = Flask(__name__, template_folder="templates", static_folder="static")

# ---- Generamos el dataset una vez al iniciar ----
DATA_DF = generar_dataset(seed=42)
pd.options.display.float_format = "{:.2f}".format

def safe_json(data):
    """Convierte objetos de Pandas/Numpy a JSON seguro."""
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        content_type="application/json"
    )
    
def cara_del_cubo(df, dim_x, dim_y, metric):
    """
    Devuelve una tabla dinámica 2D: dim_x vs dim_y con sum(metric).
    """
    tabla = pd.pivot_table(
        df,
        values=metric,
        index=[dim_y],   # filas
        columns=[dim_x], # columnas
        aggfunc="sum",
        margins=False
    )
    # convertimos índice/columnas a columnas normales para mandarlo como JSON
    tabla = tabla.reset_index().fillna(0)
    return tabla


def seccion_del_cubo_dice(
    df: pd.DataFrame,
    anios=None,
    regiones=None,
    productos=None,
    canales=None,
    metric="Ventas"
):
    """
    Realiza una operación DICE sobre el cubo OLAP:
    filtra simultáneamente por varias dimensiones y devuelve una vista 2D.

    Parámetros:
        df          : DataFrame original del cubo
        anios       : lista o valor único de años (ej. [2023, 2024])
        regiones    : lista o valor único de regiones
        productos   : lista o valor único de productos
        canales     : lista o valor único de canales
        metric      : métrica a resumir (por defecto 'Ventas')

    Retorna:
        DataFrame 2D resumido por Año y Región.
    """

    # --- Construcción del filtro dinámico
    m = pd.Series([True] * len(df))

    if anios is not None:
        if not isinstance(anios, (list, tuple)):
            anios = [anios]
        m &= df["Año"].isin(anios)

    if regiones is not None:
        if not isinstance(regiones, (list, tuple)):
            regiones = [regiones]
        m &= df["Región"].isin(regiones)

    if productos is not None:
        if not isinstance(productos, (list, tuple)):
            productos = [productos]
        m &= df["Producto"].isin(productos)

    if canales is not None:
        if not isinstance(canales, (list, tuple)):
            canales = [canales]
        m &= df["Canal"].isin(canales)

    # --- Aplicar el filtro DICE
    sub = df.loc[m].copy()

    # --- Generar la tabla 2D (puedes cambiar índices si lo deseas)
    tabla = pd.pivot_table(
        sub,
        values=metric,
        index=["Año", "Región"],
        aggfunc="sum",
        margins=False
    ).reset_index().fillna(0).round(2)

    return tabla


def cubo_completo(df):
    vistas = {}

    # 1️⃣ Cubo principal: Producto x Región x Año x Trimestre
    vista1 = pd.pivot_table(
        df,
        values="Ventas",
        index=["Producto", "Región"],
        columns=["Año", "Trimestre"],
        aggfunc="sum",
        margins=True,
        margins_name="Total"
    ).reset_index().fillna(0).round(2)

    # 🔧 Aplana columnas multinivel (ej: (2023,1) -> "2023-T1")
    def formatear_columna(col):
        """
        Convierte columnas tipo ('2023', 1) → '2023-T1'
        y deja sin cambios columnas como ('Producto', '') → 'Producto'.
        """
        if isinstance(col, tuple):
            # Si hay año y trimestre (por ejemplo (2023, 1))
            if len(col) == 2 and str(col[1]).isdigit():
                return f"{col[0]}-T{col[1]}"
            # Si es una columna base (Producto, Región)
            elif col[1] in [None, ""]:
                return str(col[0])
        # Si no es tupla (columna normal)
        return str(col)

    # Aplicar el formateo a todas las columnas
    vista1.columns = [formatear_columna(c) for c in vista1.columns]

    vistas["producto_region_anio_trimestre_ventas"] = vista1.to_dict(orient="records")
    return vistas


def detalle_celda(df, dim_x, valor_x, dim_y, valor_y):
    """
    Devuelve las filas del DataFrame que conforman una celda específica del cubo.
    """
    # intenta convertir a número si es posible
    try:
        valor_x = int(valor_x)
    except ValueError:
        pass
    try:
        valor_y = int(valor_y)
    except ValueError:
        pass

    mask = (df[dim_x] == valor_x) & (df[dim_y] == valor_y)
    detalle = df[mask].copy()

    columnas_utiles = ["Año", "Trimestre", "Mes", "Región", "Canal", "Producto", "Cantidad", "Ventas"]
    columnas_existentes = [c for c in columnas_utiles if c in detalle.columns]
    detalle = detalle[columnas_existentes]

    return detalle



# ----------------- Rutas API -----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/cara")
def api_cara():
    dim_x = request.args.get("dim_x", "Año")
    dim_y = request.args.get("dim_y", "Región")
    metric = request.args.get("metric", "Ventas")

    tabla = cara_del_cubo(DATA_DF, dim_x, dim_y, metric)
    return safe_json({
        "dim_x": dim_x,
        "dim_y": dim_y,
        "metric": metric,
        "data": tabla.to_dict(orient="records"),
        "columns": list(map(str, tabla.columns))  # <- fuerza texto
    })


@app.route("/api/seccion")
def api_seccion():
    anios = request.args.get("anios")
    regiones = request.args.get("regiones")
    productos = request.args.get("productos")
    canales = request.args.get("canales")
    metric = request.args.get("metric", "Ventas")

    # convertir strings CSV a listas
    parse_list = lambda x: x.split(",") if x else None

    anios = parse_list(anios)
    regiones = parse_list(regiones)
    productos = parse_list(productos)
    canales = parse_list(canales)

    # convertir años a enteros si aplica
    if anios:
        try:
            anios = [int(a) for a in anios]
        except ValueError:
            pass

    # ejecutar dice
    tabla = seccion_del_cubo_dice(DATA_DF, anios, regiones, productos, canales, metric)

    return safe_json({
        "filtros": {
            "Año": anios,
            "Región": regiones,
            "Producto": productos,
            "Canal": canales
        },
        "metric": metric,
        "data": tabla.to_dict(orient="records"),
        "columns": list(tabla.columns)
    })


@app.route("/api/cubo")
def api_cubo():
    vistas = cubo_completo(DATA_DF)
    return safe_json(vistas)


@app.route("/api/celda")
def api_celda():
    dim_x = request.args.get("dim_x", "Año")
    valor_x = request.args.get("valor_x", "2024")
    dim_y = request.args.get("dim_y", "Región")
    valor_y = request.args.get("valor_y", "Norte")

    detalle = detalle_celda(DATA_DF, dim_x, valor_x, dim_y, valor_y)
    return safe_json({
        "dim_x": dim_x,
        "valor_x": valor_x,
        "dim_y": dim_y,
        "valor_y": valor_y,
        "data": detalle.to_dict(orient="records"),
        "columns": list(map(str, detalle.columns))
    })


if __name__ == "__main__":
    app.run(debug=True)

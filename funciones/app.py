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

def seccion_del_cubo(df, filtro_dim, filtro_valor):
    """
    Aplica slice/dice: filtra el DataFrame por una dimensión específica.
    Devuelve las filas filtradas resumidas por Año y Región (por ejemplo).
    Aquí puedes customizar la agregación que quieras mostrar.
    """
    sub = df[df[filtro_dim] == filtro_valor]
    tabla = pd.pivot_table(
        sub,
        values="Ventas",
        index=["Año", "Región"],
        aggfunc="sum",
        margins=False
    ).reset_index().fillna(0)
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
    filtro_dim = request.args.get("filtro_dim", "Año")
    filtro_valor = request.args.get("filtro_valor", "2023")

    # Detectar tipo de dato de la columna (solo con Pandas)
    if filtro_dim in DATA_DF.columns:
        dtype = DATA_DF[filtro_dim].dtype
        if pd.api.types.is_numeric_dtype(dtype):
            try:
                filtro_valor = float(filtro_valor)
            except ValueError:
                pass

    # Filtrar los datos dinámicamente
    tabla = DATA_DF[DATA_DF[filtro_dim] == filtro_valor].copy()

    return safe_json({
        "filtro_dim": filtro_dim,
        "filtro_valor": filtro_valor,
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

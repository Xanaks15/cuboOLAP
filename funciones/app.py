from flask import Flask, jsonify, request, render_template
import pandas as pd
import json
from flask import Response

# Importa tus módulos reales:
from generarDatos import generar_dataset
# opcionalmente puedes importar helpers de crearCubo / operacionesCubo si quieres usarlos internamente

app = Flask(__name__, template_folder="templates", static_folder="static")

# ---- Generamos el dataset una vez al iniciar ----
DATA_DF = generar_dataset(seed=42)

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
    """
    Devuelve varias vistas/pivotes predefinidas del cubo.
    Esto simula 'todas las caras' que existen.
    """
    vistas = {}

    # Vista 1: Ventas por Producto x Región x Año (colapsando trimestre)
    vista1 = pd.pivot_table(
        df,
        values="Ventas",
        index=["Producto", "Región"],
        columns=["Año"],
        aggfunc="sum",
        margins=False
    ).reset_index().fillna(0)
    vistas["producto_region_anio_ventas"] = vista1.to_dict(orient="records")

    # Vista 2: Ventas por Año x Región
    vista2 = pd.pivot_table(
        df,
        values="Ventas",
        index=["Año"],
        columns=["Región"],
        aggfunc="sum",
        margins=False
    ).reset_index().fillna(0)
    vistas["anio_region_ventas"] = vista2.to_dict(orient="records")

    # Vista 3: Cantidad por Producto x Año
    if "Cantidad" in df.columns:
        vista3 = pd.pivot_table(
            df,
            values="Cantidad",
            index=["Producto"],
            columns=["Año"],
            aggfunc="sum",
            margins=False
        ).reset_index().fillna(0)
        vistas["producto_anio_cantidad"] = vista3.to_dict(orient="records")

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
    filtro_dim = request.args.get("filtro_dim", "Región")
    filtro_valor = request.args.get("filtro_valor", "Norte")

    tabla = seccion_del_cubo(DATA_DF, filtro_dim, filtro_valor)
    return safe_json({
        "filtro_dim": filtro_dim,
        "filtro_valor": filtro_valor,
        "data": tabla.to_dict(orient="records"),
        "columns": list(map(str, tabla.columns))
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

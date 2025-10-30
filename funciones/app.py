from flask import Flask, request, render_template, Response
import pandas as pd
import json
from generarDatos import generar_dataset

app = Flask(__name__, template_folder="templates", static_folder="static")

# Dataset global inicial
DATA_DF = generar_dataset(seed=42)
pd.options.display.float_format = "{:.2f}".format


def safe_json(data):
    """Convierte un objeto Python o Pandas en una respuesta JSON segura.

    Args:
        data (object): Estructura serializable (dict, DataFrame, lista, etc.).

    Returns:
        flask.Response: Objeto HTTP con contenido JSON.
    """
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        content_type="application/json"
    )


def cara_del_cubo(df, dim_x, dim_y, metric):
    """Genera una vista 2D del cubo (operación "cara").

    Crea una tabla dinámica (pivot table) donde las filas y columnas 
    corresponden a dimensiones seleccionadas y los valores son la suma 
    de la métrica especificada.

    Args:
        df (pd.DataFrame): Dataset base del cubo.
        dim_x (str): Dimensión a ubicar en columnas.
        dim_y (str): Dimensión a ubicar en filas.
        metric (str): Métrica a agregar (por ejemplo, "Ventas").

    Returns:
        pd.DataFrame: Tabla resumen bidimensional.
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


def seccion_del_cubo_dice(df, anios=None, regiones=None, productos=None, canales=None, metric="Ventas"):
    """Realiza una operación DICE sobre el cubo OLAP.

    Filtra simultáneamente el DataFrame por múltiples dimensiones y 
    genera una vista 2D resumida por Año y Región.

    Args:
        df (pd.DataFrame): Dataset base del cubo.
        anios (list[int] | None): Lista de años a filtrar.
        regiones (list[str] | None): Lista de regiones.
        productos (list[str] | None): Lista de productos.
        canales (list[str] | None): Lista de canales.
        metric (str): Métrica a sumar. Por defecto "Ventas".

    Returns:
        pd.DataFrame: Tabla agregada por Año y Región.
    """
    m = pd.Series([True] * len(df))

    if anios is not None:
        anios = [anios] if not isinstance(anios, (list, tuple)) else anios
        m &= df["Año"].isin(anios)

    if regiones is not None:
        regiones = [regiones] if not isinstance(regiones, (list, tuple)) else regiones
        m &= df["Región"].isin(regiones)

    if productos is not None:
        productos = [productos] if not isinstance(productos, (list, tuple)) else productos
        m &= df["Producto"].isin(productos)

    if canales is not None:
        canales = [canales] if not isinstance(canales, (list, tuple)) else canales
        m &= df["Canal"].isin(canales)

    sub = df.loc[m].copy()
    tabla = pd.pivot_table(
        sub,
        values=metric,
        index=["Año", "Región"],
        aggfunc="sum",
        margins=False
    ).reset_index().fillna(0).round(2)

    return tabla


def cubo_completo(df):
    """Genera una representación agregada completa del cubo OLAP.

    Construye una vista multidimensional (Producto × Región × Año × Trimestre) 
    con sumas de ventas y formatea las columnas para exportar como JSON.

    Args:
        df (pd.DataFrame): Dataset base del cubo.

    Returns:
        dict: Diccionario con vistas (key = nombre de vista, value = lista de registros).
    """
    vistas = {}
    vista1 = pd.pivot_table(
        df,
        values="Ventas",
        index=["Producto", "Región"],
        columns=["Año", "Trimestre"],
        aggfunc="sum",
        margins=True,
        margins_name="Total"
    ).reset_index().fillna(0).round(2)

    def formatear_columna(col):
        """Formatea nombres de columnas multinivel."""
        if isinstance(col, tuple):
            if len(col) == 2 and str(col[1]).isdigit():
                return f"{col[0]}-T{col[1]}"
            elif col[1] in [None, ""]:
                return str(col[0])
        return str(col)

    vista1.columns = [formatear_columna(c) for c in vista1.columns]
    vistas["producto_region_anio_trimestre_ventas"] = vista1.to_dict(orient="records")
    return vistas


def detalle_celda(df, dim_x, valor_x, dim_y, valor_y):
    """Obtiene las filas que corresponden a una celda específica del cubo.

    Args:
        df (pd.DataFrame): Dataset base.
        dim_x (str): Dimensión de columna.
        valor_x (str | int): Valor de la dimensión X.
        dim_y (str): Dimensión de fila.
        valor_y (str | int): Valor de la dimensión Y.

    Returns:
        pd.DataFrame: Subconjunto de filas correspondiente a la celda.
    """
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
    return detalle[columnas_existentes]


# ------------------ Rutas Flask ------------------

@app.route("/")
def index():
    """Renderiza la página principal de la aplicación."""
    return render_template("index.html")


@app.route("/api/cara")
def api_cara():
    """Endpoint que devuelve una vista 2D del cubo.

    Query Params:
        dim_x (str): Dimensión X.
        dim_y (str): Dimensión Y.
        metric (str): Métrica a calcular.

    Returns:
        JSON: Datos, columnas y metadatos de la vista.
    """
    dim_x = request.args.get("dim_x", "Año")
    dim_y = request.args.get("dim_y", "Región")
    metric = request.args.get("metric", "Ventas")

    tabla = cara_del_cubo(DATA_DF, dim_x, dim_y, metric)
    return safe_json({
        "dim_x": dim_x,
        "dim_y": dim_y,
        "metric": metric,
        "data": tabla.to_dict(orient="records"),
        "columns": list(map(str, tabla.columns))
    })


@app.route("/api/seccion")
def api_seccion():
    """Endpoint que ejecuta la operación DICE sobre el cubo.

    Query Params:
        anios, regiones, productos, canales, metric (str): Filtros y métrica.

    Returns:
        JSON: Tabla filtrada y metadatos de filtros aplicados.
    """
    anios = request.args.get("anios")
    regiones = request.args.get("regiones")
    productos = request.args.get("productos")
    canales = request.args.get("canales")
    metric = request.args.get("metric", "Ventas")

    parse_list = lambda x: x.split(",") if x else None
    anios = parse_list(anios)
    regiones = parse_list(regiones)
    productos = parse_list(productos)
    canales = parse_list(canales)

    if anios:
        try:
            anios = [int(a) for a in anios]
        except ValueError:
            pass

    tabla = seccion_del_cubo_dice(DATA_DF, anios, regiones, productos, canales, metric)

    return safe_json({
        "filtros": {"Año": anios, "Región": regiones, "Producto": productos, "Canal": canales},
        "metric": metric,
        "data": tabla.to_dict(orient="records"),
        "columns": list(tabla.columns)
    })


@app.route("/api/cubo")
def api_cubo():
    """Endpoint que devuelve la estructura completa del cubo OLAP."""
    vistas = cubo_completo(DATA_DF)
    return safe_json(vistas)


@app.route("/api/celda")
def api_celda():
    """Endpoint que devuelve los detalles de una celda específica del cubo."""
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

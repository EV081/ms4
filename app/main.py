import os
import time
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List
from datetime import date
import logging

load_dotenv()
ATHENA_DB = os.getenv("ATHENA_DB", "analytic")
WORKGROUP = "primary"
athena = boto3.client("athena", region_name="us-east-1")

app = FastAPI(title="MS4 Analytics")

def run_athena(query: str, params: dict, timeout_s: int = 60):
    logging.debug(f"Ejecutando consulta Athena con los parámetros: {params}")
    
    for k, v in params.items():
        qv = str(v) if isinstance(v, (int, float)) else f"'{v}'"
        query = query.replace(f":{k}", qv)

    logging.debug(f"Consulta Athena final: {query}")

    output_location = "s3://ms4-results/"

    try:
        qid = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": ATHENA_DB},
            WorkGroup=WORKGROUP,
            ResultConfiguration={'OutputLocation': output_location},
        )["QueryExecutionId"]

        logging.debug(f"Query Execution ID: {qid}")

        start = time.time()
        while True:
            status = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            if time.time() - start > timeout_s:
                athena.stop_query_execution(QueryExecutionId=qid)
                logging.error("Athena timeout")
                raise HTTPException(504, "Athena timeout")
            time.sleep(0.5)

        if status != "SUCCEEDED":
            logging.error(f"Athena query failed with status: {status}")
            raise HTTPException(502, f"Athena error: {status}")

        rs = athena.get_query_results(QueryExecutionId=qid)
        cols = [c["Label"].lower() for c in rs["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
        out = []
        for row in rs["ResultSet"]["Rows"][1:]:
            vals = [d.get("VarCharValue") for d in row["Data"]]
            out.append(dict(zip(cols, vals)))
        return out
    except Exception as e:
        logging.error(f"Error en la ejecución de Athena: {str(e)}")
        raise HTTPException(502, f"Athena error: {str(e)}")


class EstadoHistorialResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    productos_completados: int
    productos_pendientes: int
    productos_cancelados: int
    porcentaje_completados: float
    porcentaje_pendientes: float
    porcentaje_cancelados: float

class TotalGastadoResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    total_gastado: float

class CategoriaCompraResponse(BaseModel):
    ranking: int
    id_categoria: int
    nombre_categoria: str
    total_compras: int

# Endpoint 1: Estado de los productos por usuario con porcentajes
@app.get("/estado_historial/{id_usuario}", response_model=EstadoHistorialResponse)
async def get_estado_historial(id_usuario: int):
    query = """
        WITH estado_historial AS (
            SELECT hp.id_usuario,
                   hp.estado AS estado_evento,
                   CASE
                       WHEN hp.estado = 'entregado' THEN 'entregado'
                       WHEN hp.estado = 'pendiente' THEN 'pendiente'
                       WHEN hp.estado = 'cancelado' THEN 'cancelado'
                       ELSE 'otro'
                   END AS estado_producto
            FROM "analytic"."historialpedidos" hp
            WHERE hp.id_usuario = :id_usuario
        )
        SELECT u.id_usuario,
               u.nombre,
               u.correo,
               SUM(CASE WHEN ep.estado_producto = 'entregado' THEN 1 ELSE 0 END) AS productos_completados,
               SUM(CASE WHEN ep.estado_producto = 'pendiente' THEN 1 ELSE 0 END) AS productos_pendientes,
               SUM(CASE WHEN ep.estado_producto = 'cancelado' THEN 1 ELSE 0 END) AS productos_cancelados,
               COUNT(*) AS total_productos
        FROM "analytic"."usuarios" u
        JOIN estado_historial ep ON u.id_usuario = ep.id_usuario
        GROUP BY u.id_usuario, u.nombre, u.correo;
    """

    result = run_athena(query, {'id_usuario': id_usuario})

    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    row = result[0]

    total_productos = int(row['total_productos'])
    porcentaje_completados = (int(row['productos_completados']) / total_productos) * 100 if total_productos > 0 else 0
    porcentaje_pendientes = (int(row['productos_pendientes']) / total_productos) * 100 if total_productos > 0 else 0
    porcentaje_cancelados = (int(row['productos_cancelados']) / total_productos) * 100 if total_productos > 0 else 0

    return EstadoHistorialResponse(
        id_usuario=int(row['id_usuario']),
        nombre=row['nombre'],
        correo=row['correo'],
        productos_completados=int(row['productos_completados']),
        productos_pendientes=int(row['productos_pendientes']),
        productos_cancelados=int(row['productos_cancelados']),
        porcentaje_completados=porcentaje_completados,
        porcentaje_pendientes=porcentaje_pendientes,
        porcentaje_cancelados=porcentaje_cancelados
    )

# Endpoint 2: Total gastado por usuario en un rango de fechas
@app.get("/total_gastado/{id_usuario}", response_model=TotalGastadoResponse)
async def get_total_gastado(id_usuario: int, fecha_inicio: str, fecha_fin: str):
    try:
        fecha_inicio = str(date.fromisoformat(fecha_inicio))
        fecha_fin = str(date.fromisoformat(fecha_fin))

        logging.debug(f"Fecha inicio procesada: {fecha_inicio}, Fecha fin procesada: {fecha_fin}")
        
    except ValueError as e:
        logging.error(f"Error al procesar las fechas: {str(e)}")
        raise HTTPException(status_code=400, detail="Formato de fecha incorrecto. Usa YYYY-MM-DD")

    query = """
        SELECT 
            u.id_usuario,
            u.nombre,
            u.correo,
            SUM(p.total) AS total_gastado
        FROM 
            "analytic"."usuarios" u
        JOIN 
            "analytic"."pedidos" p ON u.id_usuario = p.id_usuario
        WHERE 
            u.id_usuario = :id_usuario
            AND p.fecha_pedido BETWEEN DATE :fecha_inicio AND DATE :fecha_fin
        GROUP BY 
            u.id_usuario, u.nombre, u.correo
        ORDER BY 
            total_gastado DESC
        LIMIT 5;
    """
    
    result = run_athena(query, {
        'id_usuario': id_usuario,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })

    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    row = result[0]

    return TotalGastadoResponse(
        id_usuario=int(row['id_usuario']),
        nombre=row['nombre'],
        correo=row['correo'],
        total_gastado=float(row['total_gastado'])
    )


# Endpoint 3: Ranking de las categorías más compradas
@app.get("/ranking_categorias", response_model=List[CategoriaCompraResponse])
async def get_ranking_categorias():
    query = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as ranking,
            cat.id_categoria,
            cat.nombre_categoria,
            COUNT(*) AS total_compras
        FROM 
            "analytic"."pedidos" p
        CROSS JOIN 
            UNNEST(p.productos) AS t(prod)
        JOIN 
            "analytic"."producto" pr ON t.prod.id_producto = pr.id_producto
        JOIN 
            "analytic"."categoria" cat ON pr.id_categoria = cat.id_categoria
        GROUP BY 
            cat.id_categoria, cat.nombre_categoria
        ORDER BY 
            total_compras DESC
        LIMIT 10;
    """

    result = run_athena(query, {})

    return [CategoriaCompraResponse(**row) for row in result]

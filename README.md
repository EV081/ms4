# MS4 Analytics - API de FastAPI

Este proyecto proporciona una API RESTful utilizando **FastAPI** para consultar y procesar datos de compras de usuarios a través de AWS Athena. La API permite obtener información sobre el estado de los productos comprados por un usuario, el total gastado en un rango de fechas y el ranking de las categorías más compradas.

## Requisitos

- Docker
- Python 3.12
- FastAPI
- Uvicorn
- AWS Athena
- Boto3
- DockerHub (para almacenar la imagen)

## Endpoints

### Health

- **Método**: `GET`
- **Ruta**: `/health`
```json
{
  "status": "ok",
  "message": "API is running"
}
```

### 1. **Obtener el estado del historial de productos de un usuario**

- **Método**: `GET`
- **Ruta**: `/estado_historial/{id_usuario}`
- **Descripción**: Devuelve el estado de los productos comprados por un usuario en formato JSON, incluyendo los porcentajes de productos entregados, pendientes y cancelados.

#### Ejemplo de solicitud:

```http
GET http://localhost:8000/estado_historial/1
````

#### Parámetros:

* `id_usuario`: El ID del usuario.

#### Ejemplo de respuesta:

```json
{
    "id_usuario": 1,
    "nombre": "Juan Pérez",
    "correo": "juan.perez@correo.com",
    "productos_completados": 50,
    "productos_pendientes": 20,
    "productos_cancelados": 10,
    "porcentaje_completados": 50.0,
    "porcentaje_pendientes": 20.0,
    "porcentaje_cancelados": 10.0
}
```

---

### 2. **Obtener el total gastado por un usuario en un rango de fechas**

* **Método**: `GET`
* **Ruta**: `/total_gastado/{id_usuario}`
* **Descripción**: Devuelve el total gastado por un usuario en el rango de fechas especificado.

#### Ejemplo de solicitud:

```http
GET http://localhost:8000/total_gastado/1?fecha_inicio=2025-01-25&fecha_fin=2025-09-25
```

#### Parámetros:

* `id_usuario`: El ID del usuario.
* `fecha_inicio`: La fecha de inicio en formato `YYYY-MM-DD`.
* `fecha_fin`: La fecha de fin en formato `YYYY-MM-DD`.

#### Ejemplo de respuesta:

```json
{
    "id_usuario": 1,
    "nombre": "Juan Pérez",
    "correo": "juan.perez@correo.com",
    "total_gastado": 500.0
}
```

---

### 3. **Obtener el ranking de las categorías más compradas**

* **Método**: `GET`
* **Ruta**: `/ranking_categorias`
* **Descripción**: Devuelve un ranking de las 10 categorías más compradas en base a los pedidos realizados.

#### Ejemplo de solicitud:

```http
GET http://localhost:8000/ranking_categorias
```

#### Ejemplo de respuesta:

```json
[
    {
      "ranking": 1,
      "id_categoria": 1,
      "nombre_categoria": "Electrónica",
      "total_compras": 150
    },
    {
      "ranking": 2,
      "id_categoria": 2,
      "nombre_categoria": "Ropa",
      "total_compras": 120
    },
    {
      "ranking": 3,
      "id_categoria": 3,
      "nombre_categoria": "Hogar",
      "total_compras": 90
    }
]
```

---

## Cómo ejecutar el proyecto

### 1. **Instalar dependencias**

Asegúrate de tener las dependencias necesarias instaladas:

```bash
pip install -r requirements.txt
```

### 2. **Configurar las credenciales de AWS**

Este proyecto usa **AWS Athena** para ejecutar consultas SQL. Debes asegurarte de que las credenciales de AWS estén configuradas correctamente. Si no tienes las credenciales configuradas, puedes configurarlas usando **AWS CLI** o configurando las variables de entorno:

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
```

### 3. **Ejecutar el servidor con Uvicorn**

Puedes ejecutar la aplicación localmente usando Uvicorn:

```bash
uvicorn main:app --reload
```

El servidor estará disponible en [http://localhost:8000](http://localhost:8000).


## Tecnologías utilizadas

* **FastAPI**: Framework web para construir APIs.
* **Uvicorn**: Servidor ASGI para ejecutar FastAPI.
* **AWS Athena**: Servicio de consultas SQL basado en S3.
* **Docker**: Contenerización de la aplicación para despliegue.
* **boto3**: Cliente de Python para interactuar con AWS.


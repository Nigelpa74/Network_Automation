import base64
import json
import os
import ssl
import urllib.request
import yaml


def cargar_inventario(archivo="inventario-m.yml"):
    """Carga la lista de routers desde el archivo YAML."""
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["routers"]


def get_ifm_restconf(router):
    """Realiza la consulta RESTCONF a un equipo y guarda el resultado en un archivo JSON."""
    nombre = router["nombre"]
    host = router["host"]
    port = router.get(
        "port", 1028
    )  # Usa el puerto 1028 si no está definido en el YAML
    user = router["user"]
    password = router["password"]

    # Endpoint para el contenedor ifm de Huawei VRP8
    url = f"https://{host}:{port}/restconf/data/huawei-ifm:ifm"

    # 1. Crear credenciales de autenticación Basic HTTP
    auth_str = f"{user}:{password}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    # 2. Encabezados para consulta RESTCONF (RFC 8040)
    headers = {
        "Accept": "application/yang-data+json",
        "Authorization": f"Basic {b64_auth}",
    }

    # 3. Contexto SSL que ignora la verificación del certificado autofirmado/preset
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers=headers, method="GET")

    print(f"[{nombre}] 🚀 Conectando a {host}:{port} vía RESTCONF...")

    try:
        with urllib.request.urlopen(
            req, context=ssl_context, timeout=10
        ) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            parsed_json = json.loads(body)

            # Crear carpeta de salida (opcional)
            os.makedirs("outputs_json", exist_ok=True)
            archivo_salida = f"{nombre}_ifm.json"
            # archivo_salida = f"outputs_json/{nombre}_ifm.json"

            # Guardar el JSON formateado
            with open(archivo_salida, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=4)

            print(
                f"[{nombre}] ✅ Guardado exitosamente en {archivo_salida} (HTTP {status_code})"
            )

    except urllib.error.HTTPError as e:
        print(f"[{nombre}] ❌ Error HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"[{nombre}] ❌ Error de conexión: {e}")


if __name__ == "__main__":
    routers = cargar_inventario("inventario-c.yml")
    print(f"Se cargaron {len(routers)} equipos desde el inventario.\n")

    for router in routers:
        get_ifm_restconf(router)
import base64
import json
import os
import ssl
import urllib.parse
import urllib.request
import yaml


def cargar_inventario(archivo="inventario-c.yml"):
    """Carga la lista de routers desde el archivo YAML."""
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["routers"]


def get_devm_restconf(router):
    """Realiza la consulta RESTCONF filtrada a un equipo y guarda el resultado."""
    nombre = router["nombre"]
    host = router["host"]
    port = router.get("port", 1028)
    user = router["user"]
    password = router["password"]

    # 1. Definir los campos específicos que deseas filtrar (RESTCONF fields)
    fields = "class;name;esn;software-version;running-state"
    fields_encoded = urllib.parse.quote(fields, safe=";")

    # 2. Endpoint apuntando a la lista con el filtro aplicado
    path_base = "/restconf/data/huawei-devm:devm/physical-entitys/physical-entity"
    url = f"https://{host}:{port}{path_base}?fields={fields_encoded}"

    # 3. Credenciales de autenticación Basic HTTP
    auth_str = f"{user}:{password}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    # 4. Encabezados HTTP RESTCONF
    headers = {
        "Accept": "application/yang-data+json",
        "Authorization": f"Basic {b64_auth}",
    }

    # 5. Ignorar verificación SSL autofirmada
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers=headers, method="GET")

    print(f"[{nombre}] 🚀 Conectando a {host}:{port} vía RESTCONF (Filtrado)...")

    try:
        with urllib.request.urlopen(
            req, context=ssl_context, timeout=10
        ) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            parsed_json = json.loads(body)

            # Crear carpeta de salida
            os.makedirs("outputs_json", exist_ok=True)
            archivo_salida = os.path.join("outputs_json", f"{nombre}_devm.json")

            # Guardar el JSON filtrado
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
    # La lectura del archivo YAML arranca aquí al ejecutar el script directamente
    archivo_yaml = "inventario-c.yml"

    if os.path.exists(archivo_yaml):
        routers = cargar_inventario(archivo_yaml)
        print(f"Se cargaron {len(routers)} equipos desde {archivo_yaml}.\n")

        for router in routers:
            get_devm_restconf(router)
    else:
        print(f"❌ El archivo {archivo_yaml} no existe en el directorio actual.")
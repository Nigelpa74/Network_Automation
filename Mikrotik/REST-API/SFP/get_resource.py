import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.auth import HTTPBasicAuth
import yaml


def consultar_mikrotik_resource(router, ca_cert_global):
    """Consulta la REST API de un MikroTik individual vía HTTPS."""
    nombre = router["nombre"]
    host = router["host"]
    user = router["user"]
    password = router["password"]
    port = router.get("port", 443)

    # Permite especificar una CA particular por router o usar la global
    ca_cert = router.get("ca_cert", ca_cert_global)

    # Endpoint HTTPS de la REST API RouterOS v7+ ## ACA SE MODIFICA LO QUE QUIERES OBTENER
    url = f"https://{host}:{port}/rest/interface/ethernet"

    try:
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(user, password),
            verify=ca_cert,  # Valida el certificado contra la CA especificada
            timeout=10,
        )
        resp.raise_for_status()

        data = resp.json()
        print(f"[{nombre}] ({host}) ✅ Datos obtenidos correctamente.")
        return {
            "nombre": nombre,
            "host": host,
            "estado": "exitoso",
            "datos": data,
        }

    except requests.exceptions.SSLError as e:
        print(
            f"[{nombre}] ({host}) ❌ Error SSL/TLS: Verifica la CA o el SAN."
        )
        return {
            "nombre": nombre,
            "host": host,
            "estado": "error_ssl",
            "error": str(e),
        }

    except requests.exceptions.HTTPError as e:
        print(f"[{nombre}] ({host}) ❌ Error HTTP: {resp.status_code}")
        return {
            "nombre": nombre,
            "host": host,
            "estado": "error_http",
            "codigo": resp.status_code,
            "error": resp.text,
        }

    except requests.exceptions.RequestException as e:
        print(f"[{nombre}] ({host}) ❌ Error de conexion: {e}")
        return {
            "nombre": nombre,
            "host": host,
            "estado": "error_conexion",
            "error": str(e),
        }


def cargar_inventario(archivo="inventario-mikrotik-m.yml"):
    """Carga la configuración y la lista de routers desde el YAML."""
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("routers", []), data.get("ca_cert_global", None)


if __name__ == "__main__":
    INVENTARIO_FILE = "inventario-mikrotik-m.yml"
    SALIDA_JSON = "resultado_mikrotik_resources.json"
    MAX_WORKERS = 5  # Número de consultas simultáneas

    routers, ca_global = cargar_inventario(INVENTARIO_FILE)

    print(
        f"🚀 Consultando {len(routers)} equipos MikroTik vía REST API (HTTPS) con {MAX_WORKERS} workers...\n"
    )

    resultados = []

    # Ejecución paralela usando ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(consultar_mikrotik_resource, router, ca_global)
            for router in routers
        ]

        for future in as_completed(futures):
            resultado = future.result()
            resultados.append(resultado)

    # Ordenar resultados por el campo 'nombre'
    resultados_ordenados = sorted(resultados, key=lambda x: x["nombre"])

    # Guardar la consolidación completa en un archivo JSON estructurado
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados_ordenados, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Proceso finalizado. Reporte consolidado guardado en: {SALIDA_JSON}")
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.auth import HTTPBasicAuth
import yaml


def consultar_mikrotik_sfp_monitor(router, ca_cert_global, interface_name="sfp-sfpplus1"):
    """Consulta la información DDM/DOM de un SFP en MikroTik vía POST en la REST API."""
    nombre = router["nombre"]
    host = router["host"]
    user = router["user"]
    password = router["password"]
    port = router.get("port", 443)

    ca_cert = router.get("ca_cert", ca_cert_global)

    # Endpoint de REST API para ejecutar el comando 'monitor' sobre la interfaz ethernet/sfp
    url = f"https://{host}:{port}/rest/interface/ethernet/monitor"

    # Payload equivalente a: /interface ethernet monitor <interface_name> once
    payload = {
        "numbers": interface_name,
        "once": True
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Se cambia requests.get por requests.post
        resp = requests.post(
            url,
            auth=HTTPBasicAuth(user, password),
            json=payload,         # Pasa los datos como JSON en el body
            headers=headers,
            verify=ca_cert,
            timeout=10,
        )
        resp.raise_for_status()

        data = resp.json()
        print(f"[{nombre}] ({host}) ✅ Datos SFP obtenidos correctamente para {interface_name}.")
        return {
            "nombre": nombre,
            "host": host,
            "interfaz": interface_name,
            "estado": "exitoso",
            "datos": data,
        }

    except requests.exceptions.SSLError as e:
        print(f"[{nombre}] ({host}) ❌ Error SSL/TLS: Verifica la CA o el SAN.")
        return {
            "nombre": nombre,
            "host": host,
            "estado": "error_ssl",
            "error": str(e),
        }

    except requests.exceptions.HTTPError as e:
        print(f"[{nombre}] ({host}) ❌ Error HTTP: {resp.status_code} - {resp.text}")
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
    SALIDA_JSON = "resultado_mikrotik_sfp.json"
    MAX_WORKERS = 5

    # Especifica el nombre de la interfaz SFP a monitorear (ej. 'sfp-sfpplus1', 'sfp1', etc.)
    PUERTO_SFP = "sfp-sfpplus1"

    routers, ca_global = cargar_inventario(INVENTARIO_FILE)

    print(
        f"🚀 Consultando métricas SFP ({PUERTO_SFP}) en {len(routers)} equipos MikroTik vía REST API...\n"
    )

    resultados = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(consultar_mikrotik_sfp_monitor, router, ca_global, PUERTO_SFP)
            for router in routers
        ]

        for future in as_completed(futures):
            resultado = future.result()
            resultados.append(resultado)

    resultados_ordenados = sorted(resultados, key=lambda x: x["nombre"])

    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados_ordenados, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Proceso finalizado. Reporte SFP guardado en: {SALIDA_JSON}")
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.auth import HTTPBasicAuth
import yaml


def obtener_puertos_sfp(host, port, user, password, ca_cert):
    """Fase 1 (GET): Obtiene todas las interfaces y filtra solo las que son SFP."""
    url = f"https://{host}:{port}/rest/interface/ethernet"
    try:
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(user, password),
            verify=ca_cert,
            timeout=10,
        )
        resp.raise_for_status()
        interfaces = resp.json()

        # Filtrar puertos cuyos nombres comiencen por 'sfp' (ej: sfp1, sfp-sfpplus1, etc.)
        puertos_sfp = [
            iface["name"]
            for iface in interfaces
            if iface.get("name", "").lower().startswith("sfp")
        ]
        return puertos_sfp

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error obteniendo la lista de puertos en {host}: {e}")
        return []


def consultar_metrica_sfp_individual(host, port, user, password, ca_cert, interface_name):
    """Consulta la métrica DDM de un único puerto SFP vía POST."""
    url = f"https://{host}:{port}/rest/interface/ethernet/monitor"
    payload = {"numbers": interface_name, "once": True}
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(
            url,
            auth=HTTPBasicAuth(user, password),
            json=payload,
            headers=headers,
            verify=ca_cert,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # La API devuelve una lista con un diccionario dentro
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data

    except requests.exceptions.RequestException as e:
        return {"name": interface_name, "error": str(e)}


def procesar_router_completo(router, ca_cert_global):
    """Procesa un router: Descubre sus SFPs (GET) y consulta sus métricas en paralelo (POST)."""
    nombre = router["nombre"]
    host = router["host"]
    user = router["user"]
    password = router["password"]
    port = router.get("port", 443)
    ca_cert = router.get("ca_cert", ca_cert_global)

    print(f"🔎 [{nombre}] ({host}): Detectando interfaces SFP...")

    # 1. Obtener la lista dinámica de SFPs de este equipo
    lista_sfps = obtener_puertos_sfp(host, port, user, password, ca_cert)

    if not lista_sfps:
        print(f"⚠️ [{nombre}] ({host}): No se encontraron puertos SFP o no se pudo consultar.")
        return {
            "nombre": nombre,
            "host": host,
            "estado": "sin_sfps_o_error",
            "sfps_detectados": 0,
            "datos_sfps": [],
        }

    print(f"⚡ [{nombre}] ({host}): Se detectaron {len(lista_sfps)} puerto(s) SFP: {lista_sfps}")

    # 2. Consultar las métricas DDM de todos los SFPs detectados en paralelo
    resultados_sfps = []
    # Usamos hilos locales para consultar todos los SFP del router al mismo tiempo
    with ThreadPoolExecutor(max_workers=len(lista_sfps)) as executor_sfp:
        futures_sfp = [
            executor_sfp.submit(
                consultar_metrica_sfp_individual,
                host,
                port,
                user,
                password,
                ca_cert,
                sfp_name,
            )
            for sfp_name in lista_sfps
        ]

        for future in as_completed(futures_sfp):
            resultados_sfps.append(future.result())

    # Ordenar los datos por nombre de interfaz (sfp1, sfp2, etc.)
    resultados_sfps = sorted(resultados_sfps, key=lambda x: x.get("name", ""))

    print(f"✅ [{nombre}] ({host}): Métricas DDM de {len(resultados_sfps)} SFP(s) recopiladas.")

    return {
        "nombre": nombre,
        "host": host,
        "estado": "exitoso",
        "sfps_detectados": len(lista_sfps),
        "datos_sfps": resultados_sfps,
    }


def cargar_inventario(archivo="inventario-mikrotik-m.yml"):
    """Carga los routers desde el archivo YAML."""
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("routers", []), data.get("ca_cert_global", None)


if __name__ == "__main__":
    INVENTARIO_FILE = "inventario-mikrotik-m.yml"
    SALIDA_JSON = "reporte_consolidado_sfps.json"
    MAX_WORKERS_ROUTERS = 5  # Consultar hasta 5 routers simultáneamente

    routers, ca_global = cargar_inventario(INVENTARIO_FILE)

    print(
        f"🚀 Iniciando escaneo de SFPs en {len(routers)} equipo(s) MikroTik...\n"
    )

    resultados_finales = []

    # Ejecutar el procesamiento multi-router en paralelo
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_ROUTERS) as executor_main:
        futures_routers = [
            executor_main.submit(procesar_router_completo, router, ca_global)
            for router in routers
        ]

        for future in as_completed(futures_routers):
            resultados_finales.append(future.result())

    # Ordenar el reporte por el nombre del router
    resultados_finales = sorted(resultados_finales, key=lambda x: x["nombre"])

    # Guardar archivo JSON estructurado
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados_finales, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 ¡Proceso completado! Reporte guardado en: {SALIDA_JSON}")
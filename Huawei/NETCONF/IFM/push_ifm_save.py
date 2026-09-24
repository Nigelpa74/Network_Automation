import yaml
import datetime
import re
import csv
import time
import argparse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from ncclient import manager
from ncclient.xml_ import to_ele

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <ifm xmlns="urn:huawei:yang:huawei-ifm">
      <interfaces>
        <interface>
          <name>Vlanif10</name>
            <ip-statistics-enable xmlns="urn:huawei:yang:huawei-ifm-ip-statistics">
              <unified-mode>
                <ip-enable>enable</ip-enable>
              </unified-mode>
            </ip-statistics-enable>
        </interface>
      </interfaces>
    </ifm>
</config>
"""

# Filtro NETCONF <get> para leer solo el archivo de startup actual del equipo
# (huawei-cfg: container cfg -> startup-infos -> startup-info -> current-cfg-file)
FILTER_STARTUP_INFO = """
<filter type="subtree">
  <cfg xmlns="urn:huawei:yang:huawei-cfg">
    <startup-infos>
      <startup-info>
        <current-cfg-file/>
      </startup-info>
    </startup-infos>
  </cfg>
</filter>
"""

NS_CFG = {"cfg": "urn:huawei:yang:huawei-cfg"}


def get_current_cfg_file(m):
    """
    Consulta el archivo de configuración de startup que el equipo REALMENTE
    tiene configurado (leaf current-cfg-file, dato de solo lectura).
    Usar SIEMPRE este nombre al hacer save, nunca uno fijo, porque varía
    de equipo a equipo (ej: flash:/colegio_001.cfg, flash:/colegio_002.cfg...).
    """
    reply = m.get(filter=FILTER_STARTUP_INFO)
    root = ET.fromstring(reply.data_xml)
    # Puede haber más de una entrada (p.ej. main/backup); nos quedamos con
    # la primera que traiga current-cfg-file con valor.
    for info in root.findall(".//cfg:startup-info", NS_CFG):
        cfg_file = info.find("cfg:current-cfg-file", NS_CFG)
        if cfg_file is not None and cfg_file.text:
            return cfg_file.text.strip()
    return None


def sin_prefijo_dispositivo(nombre_archivo):
    """
    El RPC <save> de huawei-cfg en este equipo (AR5710) NO acepta el prefijo
    de dispositivo (ej. 'flash:/'), solo el nombre del archivo — se confirmó
    en pruebas: 'flash:/colegio_001.cfg' -> "The file format is invalid",
    'colegio_001.cfg' (sin prefijo) -> guardado correcto.
    current-cfg-file siempre trae el prefijo (ej. 'flash:/colegio_001.cfg'),
    así que hay que quitarlo antes de pasarlo al save.
    """
    return re.sub(r"^[A-Za-z][A-Za-z0-9_]*:/*", "", nombre_archivo)


def huawei_connect(router):
    return manager.connect(
        host=router["host"],
        port=int(router["port"]),
        username=router["user"],
        password=router["password"],
        hostkey_verify=False,
        device_params={'name': "huaweiyang"},
        allow_agent=False,
        look_for_keys=False,
        timeout=20
    )

def push_ifm(router, dry_run=False):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            if dry_run:
                # Solo valida conectividad y lee el archivo de startup, no toca nada
                cfg_filename = get_current_cfg_file(m)
                if not cfg_filename:
                    print(f"[{nombre}] ⚠️  DRY-RUN: conecta pero no se pudo leer current-cfg-file")
                    return (nombre, "DRY_RUN_SIN_CFG")
                print(f"[{nombre}] 🔎 DRY-RUN OK, current-cfg-file={cfg_filename}")
                return (nombre, "DRY_RUN_OK")

            m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ IFM aplicado correctamente")

            # --- Detectar el archivo de startup real de ESTE equipo ---
            cfg_filename = get_current_cfg_file(m)
            if not cfg_filename:
                print(f"[{nombre}] ⚠️  No se pudo leer current-cfg-file, no se hizo save "
                      f"(la config quedó aplicada en running pero NO sobrevive a un reinicio)")
                return (nombre, "SIN_SAVE")

            # El save RPC no acepta el prefijo de dispositivo (flash:/), solo el nombre
            filename_para_save = sin_prefijo_dispositivo(cfg_filename)

            # --- Guardar en el MISMO archivo que usa el equipo, para que sobreviva a un reinicio ---
            rpc = to_ele(f"""
                <save xmlns="urn:huawei:yang:huawei-cfg">
                  <filename>{filename_para_save}</filename>
                </save>
            """)
            m.dispatch(rpc)
            print(f"[{nombre}] 💾 Configuración guardada en {cfg_filename}")
            return (nombre, "OK")

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")
        return (nombre, "FALLO")

def cargar_inventario(archivo="inventario-c.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]


def escribir_csv(resultados, archivo):
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["nombre", "estado", "timestamp"])
        ahora = datetime.datetime.now().isoformat(timespec="seconds")
        for nombre, estado in resultados:
            writer.writerow([nombre, estado, ahora])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Aplica IFM Vlanif10 por NETCONF en colegios MINEDU")
    parser.add_argument("--inventario", default="inventario-c.yml", help="Archivo YAML de inventario")
    parser.add_argument("--dry-run", action="store_true",
                         help="Solo conecta y lee current-cfg-file, no aplica ni guarda nada")
    parser.add_argument("--limit", type=int, default=None,
                         help="Procesa solo los primeros N routers del inventario (para pruebas piloto)")
    parser.add_argument("--batch-size", type=int, default=20,
                         help="Cantidad de routers por lote")
    parser.add_argument("--pausa-entre-lotes", type=float, default=10.0,
                         help="Segundos de pausa entre lotes, para poder frenar si algo sale mal")
    parser.add_argument("--workers", type=int, default=5,
                         help="Conexiones NETCONF concurrentes dentro de un lote")
    parser.add_argument("--salida-csv", default=None,
                         help="Archivo CSV de resultados (por defecto: resultados_<timestamp>.csv)")
    args = parser.parse_args()

    routers = cargar_inventario(args.inventario)
    if args.limit:
        routers = routers[:args.limit]

    modo = "DRY-RUN (sin cambios)" if args.dry_run else "APLICACIÓN REAL"
    print(f"Modo: {modo}")
    print(f"Total routers: {len(routers)} | lote={args.batch_size} | workers={args.workers}\n")

    resultados = []
    lotes = [routers[i:i + args.batch_size] for i in range(0, len(routers), args.batch_size)]

    for idx, lote in enumerate(lotes, start=1):
        print(f"\n--- Lote {idx}/{len(lotes)} ({len(lote)} routers) ---")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futuros = {pool.submit(push_ifm, router, args.dry_run): router for router in lote}
            for futuro in as_completed(futuros):
                resultados.append(futuro.result())

        if idx < len(lotes) and args.pausa_entre_lotes > 0:
            print(f"⏸️  Pausa de {args.pausa_entre_lotes}s antes del siguiente lote "
                  f"(Ctrl+C para frenar aquí y revisar)...")
            try:
                time.sleep(args.pausa_entre_lotes)
            except KeyboardInterrupt:
                print("⏹️  Detenido manualmente entre lotes.")
                break

    # --- Resumen final ---
    fallidos = [r for r in resultados if r[1] == "FALLO"]
    sin_save = [r for r in resultados if r[1] == "SIN_SAVE"]
    exitosos = [r for r in resultados if r[1] in ("OK", "DRY_RUN_OK")]
    print(f"\n=== RESUMEN ===")
    print(f"✅ Exitosos: {len(exitosos)}/{len(resultados)}")
    print(f"⚠️  Aplicado pero SIN guardar (revisar manualmente): {len(sin_save)}")
    for nombre, estado in sin_save:
        print(f"   - {nombre}")
    print(f"❌ Fallidos: {len(fallidos)}")
    for nombre, estado in fallidos:
        print(f"   - {nombre}")

    salida_csv = args.salida_csv or f"resultados_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    escribir_csv(resultados, salida_csv)
    print(f"\n📄 Resultados guardados en {salida_csv} (úsalo para armar un inventario solo con los fallidos y reintentar)")
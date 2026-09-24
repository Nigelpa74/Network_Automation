import datetime
import yaml
from ncclient import manager

# Ajusta estos 3 valores a tu caso real:
POOL_NOMBRE = "pool_vlan20"
DNS_VIEJOS = ["1.1.1.3", "8.8.8.8"]
DNS_NUEVOS = ["10.50.2.5"]

def generar_config():
    remove_dns = "".join(
        f'<dns-list xc:operation="remove"><dns-ip>{ip}</dns-ip></dns-list>'
        for ip in DNS_VIEJOS
    )
    add_dns = "".join(
        f'<dns-list><dns-ip>{ip}</dns-ip></dns-list>'
        for ip in DNS_NUEVOS
    )
    return f"""
    <config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
      <dhcp xmlns="urn:huawei:yang:huawei-dhcp">
        <server>
          <global-ip-pools>
            <global-ip-pool>
              <ip-pool-name>{POOL_NOMBRE}</ip-pool-name>
              <dns-lists>
                {remove_dns}
                {add_dns}
              </dns-lists>
            </global-ip-pool>
          </global-ip-pools>
        </server>
      </dhcp>
    </config>
    """

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
        timeout=15
    )

def push_dns(router, config_xml):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            m.edit_config(target="candidate", config=config_xml, error_option="rollback-on-error")
            m.commit()
            return (nombre, "OK", "")
    except Exception as e:
        return (nombre, "FALLO", str(e))

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]


if __name__ == '__main__':
    routers = cargar_inventario()
    config_xml = generar_config()
    resultados = []

    print(f"Aplicando cambio de DNS en {len(routers)} routers...\n")
    for router in routers:
        r = push_dns(router, config_xml)
        resultados.append(r)
        print(f"[{r[0]}] {r[1]}")

    exitosos = [r for r in resultados if r[1] == "OK"]
    fallidos = [r for r in resultados if r[1] == "FALLO"]

    resumen = []
    resumen.append(f"=== RESUMEN — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    resumen.append(f"Exitosos: {len(exitosos)}/{len(routers)}")
    resumen.append(f"Fallidos: {len(fallidos)}")
    for nombre, estado, error in fallidos:
        resumen.append(f"   - {nombre}: {error}")

    texto_resumen = "\n".join(resumen)
    print("\n" + texto_resumen)

    # Guardar en archivo con fecha en el nombre
    nombre_archivo = f"resultado_dns_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(nombre_archivo, "w") as f:
        f.write(texto_resumen)

    print(f"\nResumen guardado en: {nombre_archivo}")
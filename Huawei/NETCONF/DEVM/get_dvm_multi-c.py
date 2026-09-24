import xml.dom.minidom
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from ncclient import manager
import yaml

FILTER = """
<filter type="subtree">
  <devm xmlns="urn:huawei:yang:huawei-devm">
    <ports>
      <port>
        <position>GE0/0/8</position>
        <admin-state/>
        <optical-module xmlns="urn:huawei:yang:huawei-pic">
          <vendor-pn/>
          <wavelength/>
          <transmission-distance/>
          <manufacture-date/>
          <serial-number/>
        </optical-module>
      </port>
      <port>
        <position>GE0/0/9</position>
        <admin-state/>
        <optical-module xmlns="urn:huawei:yang:huawei-pic">
          <vendor-pn/>
          <wavelength/>
          <transmission-distance/>
          <manufacture-date/>
          <serial-number/>
        </optical-module>
      </port>
    </ports>
  </devm>
</filter>
"""


def huawei_connect(router):
    return manager.connect(
        host=router["host"],
        port=int(router["port"]),
        username=router["user"],
        password=router["password"],
        hostkey_verify=False,
        device_params={"name": "huaweiyang"},
        allow_agent=False,
        look_for_keys=False,
        timeout=20,
    )


def get_devm_tree(router):
    """Consulta NETCONF y devuelve la tupla (router, ElementTree_o_None)."""
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            print(f"[{nombre}] Sesion ID: {m._session.id}")
            reply = m.get(filter=FILTER)

            # Convertimos la respuesta NETCONF a un objeto ElementTree
            xml_tree = ET.fromstring(str(reply))

            # Extraemos únicamente el nodo <data> para ignorar la envoltura <rpc-reply>
            data_node = xml_tree.find(
                ".//{urn:ietf:params:xml:ns:netconf:base:1.0}data"
            )

            reply_tree = (
                data_node if data_node is not None else xml_tree
            )
            print(f"[{nombre}] ✅ Información obtenida correctamente.")
            return router, reply_tree

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")
        return router, None


def cargar_inventario(archivo="inventario-c.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["routers"]


if __name__ == "__main__":
    routers = cargar_inventario()
    MAX_WORKERS = 5

    print(f"🚀 Iniciando consultas NETCONF en paralelo con {MAX_WORKERS} workers...\n")

    # Guardaremos los resultados temporalmente
    resultados = []

    # Ejecución paralela con ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Enviamos todas las tareas al pool de hilos
        futures = [executor.submit(get_devm_tree, router) for router in routers]

        # Recogemos las respuestas a medida que van completándose
        for future in as_completed(futures):
            router, reply_tree = future.result()
            resultados.append((router, reply_tree))

    # Construcción secuencial del XML final ordenado
    root_consolidado = ET.Element("inventario-sfp-consolidado")

    for router, reply_tree in resultados:
        nombre = router["nombre"]
        router_node = ET.SubElement(
            root_consolidado,
            "router",
            nombre=str(nombre),
            host=str(router["host"]),
        )

        if reply_tree is not None:
            router_node.append(reply_tree)
        else:
            error_node = ET.SubElement(router_node, "error")
            error_node.text = "No se pudo conectar o ejecutar la consulta DEVM"

    # Formatear a XML indentado limpio
    raw_string = ET.tostring(root_consolidado, encoding="utf-8")
    xml_bonito = xml.dom.minidom.parseString(raw_string).toprettyxml(
        indent="  "
    )
    xml_bonito = "\n".join(
        line for line in xml_bonito.split("\n") if line.strip()
    )

    archivo_salida = "resultado_inventario_sfp_devm.xml"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(xml_bonito)

    print(
        f"\n🎉 Proceso completado. Todo el consolidado DEVM se guardó en: {archivo_salida}"
    )
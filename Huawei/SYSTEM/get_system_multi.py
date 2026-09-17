import xml.dom.minidom
import xml.etree.ElementTree as ET
from ncclient import manager
import yaml


FILTER = """
<filter type="subtree">
  <system xmlns="urn:huawei:yang:huawei-system">
    <system-info>
      <sys-name/>
      <sys-uptime/>
      <boot-time/>
    </system-info>
  </system>
</filter>
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
        timeout=60
    )

def get_system_tree(router):
    """Consulta NETCONF y devuelve la tupla (nombre, ElementTree) o (nombre, None)."""
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

            # Si existía <data>, devolvemos lo que hay dentro de data; si no, el tree completo
            reply_tree = (
                data_node if data_node is not None else xml_tree
            )
            return nombre, reply_tree

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")
        return nombre, None


def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["routers"]


if __name__ == "__main__":
    routers = cargar_inventario()

    root_consolidado = ET.Element("inventario-system-consolidado")

    for router in routers:
        nombre, reply_tree = get_system_tree(router)

        # Misma estructura de atributos explícitos str()
        router_node = ET.SubElement(
            root_consolidado,
            "router",
            nombre=str(nombre),
            host=str(router["host"]),
        )

        if reply_tree is not None:
            router_node.append(reply_tree)
            print(f"[{nombre}] ✅ Información agregada al reporte.")
        else:
            error_node = ET.SubElement(router_node, "error")
            error_node.text = "No se pudo conectar o ejecutar la consulta SYSTEM"

    # Formatear a XML indentado limpio
    raw_string = ET.tostring(root_consolidado, encoding="utf-8")
    xml_bonito = xml.dom.minidom.parseString(raw_string).toprettyxml(
        indent="  "
    )
    xml_bonito = "\n".join(
        line for line in xml_bonito.split("\n") if line.strip()
    )

    archivo_salida = "resultado_inventario_system.xml"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(xml_bonito)

    print(
        f"\n🚀 Proceso completado. Todo el consolidado SYSTEM se guardó en: {archivo_salida}"
    )
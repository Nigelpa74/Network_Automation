import yaml
import xml.dom.minidom
import xml.etree.ElementTree as ET
from ncclient import manager
from ncclient.xml_ import to_ele

DISPLAY_COMMANDS = """dis interface ge0/0/8 transceiver verbose | i Wavelength|Distance|Serial|Manufacturing|Part
dis interface ge0/0/9 transceiver verbose | i Wavelength|Distance|Serial|Manufacturing|Part
"""

def huawei_connect(router):
    return manager.connect(
        host=str(router["host"]),
        port=int(router["port"]),
        username=str(router["user"]),
        password=str(router["password"]),
        hostkey_verify=False,
        device_params={'name': "huaweiyang"},
        allow_agent=False,
        look_for_keys=False,
        timeout=20
    )

def get_cli_display(router):
    nombre = str(router["nombre"])
    try:
        with huawei_connect(router) as m:
            print(f"[{nombre}] Sesion ID: {m._session.id}")

            rpc_data = f"""
                <execute-batch-commands xmlns="urn:huawei:yang:huawei-cli">
                  <batch-commands>{DISPLAY_COMMANDS}</batch-commands>
                  <execute-policy>continue-on-error</execute-policy>
                </execute-batch-commands>
            """
            rpc = to_ele(rpc_data)
            reply = m.dispatch(rpc)
            
            tree = ET.fromstring(str(reply))
            return nombre, tree

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")
        return nombre, None

def cargar_inventario(archivo="inventario-c.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    
    root_consolidado = ET.Element("inventario-sfp-consolidado")

    for router in routers:
        nombre, reply_tree = get_cli_display(router)
        
        # ⚠️ FIX: Aseguramos que nombre y host sean convertidos explícitamente a str
        router_node = ET.SubElement(
            root_consolidado, 
            "router", 
            nombre=str(nombre), 
            host=str(router["host"])
        )
        
        if reply_tree is not None:
            router_node.append(reply_tree)
            print(f"[{nombre}] ✅ Información agregada al reporte.")
        else:
            error_node = ET.SubElement(router_node, "error")
            error_node.text = "No se pudo conectar o ejecutar el comando"

    raw_string = ET.tostring(root_consolidado, encoding="utf-8")
    xml_bonito = xml.dom.minidom.parseString(raw_string).toprettyxml(indent="  ")
    xml_bonito = "\n".join(line for line in xml_bonito.split("\n") if line.strip())

    archivo_salida = "resultado_inventario_sfp.xml"
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(xml_bonito)

    print(f"\n🚀 Proceso completado. Todo el consolidado se guardó en: {archivo_salida}")